"""The Telepathy engine: one local model, four ways for a team of agents to hand work on.

  single : the final agent answers alone (reference point)
  text   : every agent writes notes in English; the next agent reads them
  latent : every non-final agent thinks silently; its working memory (KV cache) is handed on
  auto   : latent per handoff; sampled handoffs get a subtitle and an honesty check, and a handoff
           that fails the check (or is marked high-stakes) is redone in English

Latent method: LatentMAS (Gen-Verse/LatentMAS, Apache-2.0), simplified.
"""
from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field, replace

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from . import honesty, policy as policy_mod, scan as scan_mod, trust
from .cache_utils import assert_bound, bind, fork, keep_last, length
from .subtitles import subtitle as make_subtitle
from .config import Config, pick_device, pick_dtype
from .latent import embedding_target_norm, think
from .roles import reads_content, role_prompt, split_team

MODES = ("single", "text", "latent", "auto")
SHARE_MODES = ("auto", "full", "thoughts_only")


@dataclass
class Handoff:
    role: str
    mode_used: str  # "latent" | "text"
    text: str = ""  # the notes, in text mode
    subtitle: str | None = None
    faithful: bool | None = None  # None = not audited
    js: float | None = None       # Jensen-Shannon divergence from the honesty check
    reason: str | None = None     # why a handoff is in text: tainted | high_stakes | unfaithful
    taint: str = "clean"          # clean | direct (read outside content) | inherited (downstream of it)
    scan: dict | None = None      # instruction-scan result for a tainted text handoff


@dataclass
class RunResult:
    answer: str
    handoffs: list[Handoff]
    metrics: dict = field(default_factory=dict)
    state: object = field(default=None, repr=False)  # kept so audits and controls can run later


@dataclass
class RunCtx:
    """Per-run safety facts, set by code at the start of a run."""
    run_id: str = "unset"
    sources: list = field(default_factory=list)   # sources of UNTRUSTED content that entered the run
    tainted: set = field(default_factory=set)     # handoff indexes whose sender read outside content directly


@dataclass
class RunState:
    """Everything the honesty check needs to replay the run from any handoff.
    It holds working-memory caches, so it never leaves the process: it cannot be pickled."""
    question: str
    context: str
    early: list
    plan: policy_mod.Plan
    ctx: RunCtx = field(default_factory=RunCtx)
    subs: dict = field(default_factory=dict)       # handoff index -> subtitle
    texts: dict = field(default_factory=dict)      # handoff index -> English text (text handoffs)
    snapshots: dict = field(default_factory=dict)  # handoff index -> cache before that agent
    answer: str = ""
    first_probs: object = None
    answer_ids: list = field(default_factory=list)  # tokens of the final answer, for teacher-forced scoring
    answer_lp: float | None = None                  # their mean log-probability in the real run
    faithful: dict = field(default_factory=dict)   # handoff index -> bool (audited ones only)
    js: dict = field(default_factory=dict)
    gap: dict = field(default_factory=dict)        # handoff index -> teacher-forced surprisal gap
    written: int = 0                               # English tokens written, reruns included
    fallbacks: int = 0

    def __getstate__(self):
        raise TypeError("a run's state holds working-memory caches, which never leave the process")


class LocalModel:
    """Loads the model once per process and is reused for every role."""

    _cache: dict = {}

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.device = pick_device(cfg.device)
        self.dtype = pick_dtype(self.device, cfg.dtype)
        self.tok = AutoTokenizer.from_pretrained(cfg.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(cfg.model_id, dtype=self.dtype).to(self.device).eval()
        self.target_norm = embedding_target_norm(self.model)
        self.eos = {self.tok.eos_token_id}
        for t in ("<|eot_id|>", "<|end_of_text|>", "<|im_end|>"):
            tid = self.tok.convert_tokens_to_ids(t)
            if isinstance(tid, int) and tid >= 0 and tid != self.tok.unk_token_id:
                self.eos.add(tid)

    @classmethod
    def get(cls, cfg: Config) -> "LocalModel":
        key = (cfg.model_id, cfg.device, cfg.dtype)
        if key not in cls._cache:
            cls._cache[key] = cls(cfg)
        return cls._cache[key]

    def sync(self):
        if self.device.type == "mps":
            torch.mps.synchronize()
        elif self.device.type == "cuda":
            torch.cuda.synchronize()

    def prompt_ids(self, role: str, question: str, notes: str = "", context: str = "", first: bool = True,
                   task: str = "math"):
        """Prompt for one agent turn. After the first turn the leading BOS text is stripped so it
        is not repeated in the middle of the shared memory. In latent mode `notes` is empty: the
        earlier agents' work lives in the cache."""
        trust.assert_no_secrets(question, notes, context)  # no secrets in agent context
        user = f"Question: {question}"
        if context:
            user += f"\n\n{trust.CONTEXT_LABEL}:\n{context}"
        if notes:
            user += f"\n\nTeam notes so far:\n{notes}"
        msgs = [{"role": "system", "content": self.cfg.system},
                {"role": "user", "content": f"{role_prompt(role, task)}\n\n{user}"}]
        text = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        if not first and self.tok.bos_token and text.startswith(self.tok.bos_token):
            text = text[len(self.tok.bos_token):]
        return self.tok(text, add_special_tokens=False, return_tensors="pt")["input_ids"].to(self.device)

    def turn_suffix_ids(self, instruction: str):
        """Tokens that close the assistant turn in progress and open a new user turn carrying
        `instruction`, ending at the assistant's generation prompt. Built from the chat template so
        it works for any model."""
        marker = "\u00a7\u00a7"
        msgs = [{"role": "system", "content": self.cfg.system}, {"role": "user", "content": "x"},
                {"role": "assistant", "content": marker}, {"role": "user", "content": instruction}]
        text = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        suffix = text.split(marker, 1)[1]
        return self.tok(suffix, add_special_tokens=False, return_tensors="pt")["input_ids"].to(self.device)

    @torch.inference_mode()
    def decode(self, ids, past=None, max_new: int | None = None, on_token=None, close: bool = False):
        """Greedy decoding with an explicit loop (avoids generate() cache-position quirks).
        Stores the first-token probability distribution in `self.first_probs`.
        close=True also feeds the end-of-turn token, so the cache is ready for the next agent."""
        max_new = self.cfg.max_new_tokens if max_new is None else max_new
        out = self.model(input_ids=ids, past_key_values=past, use_cache=True)
        past, new = out.past_key_values, []
        lp = out.logits[:, -1, :].float().log_softmax(dim=-1)
        self.first_probs = lp.exp()[0].cpu()
        nxt = lp.argmax(dim=-1, keepdim=True)
        self.last_ids, self.last_logps = [], []  # the chosen tokens and their log-probabilities
        for _ in range(max_new):
            t = int(nxt.item())
            if t in self.eos:
                if close:
                    past = self.model(input_ids=nxt, past_key_values=past, use_cache=True).past_key_values
                break
            new.append(t)
            self.last_ids.append(t)
            self.last_logps.append(float(lp[0, t]))
            if on_token:
                on_token(self.tok.decode([t], skip_special_tokens=True))
            out = self.model(input_ids=nxt, past_key_values=past, use_cache=True)
            past = out.past_key_values
            lp = out.logits[:, -1, :].float().log_softmax(dim=-1)
            nxt = lp.argmax(dim=-1, keepdim=True)
        return self.tok.decode(new, skip_special_tokens=True).strip(), len(new), past

    @torch.inference_mode()
    def score(self, ids, past, answer_ids) -> float:
        """Mean log-probability of `answer_ids` as the continuation of `ids` (teacher-forced).
        `past` is consumed: pass a fork."""
        ans = torch.tensor([answer_ids], device=self.device)
        out = self.model(input_ids=torch.cat([ids, ans], dim=1), past_key_values=past, use_cache=True)
        n = ids.shape[1]
        lp = out.logits[0, n - 1:-1].float().log_softmax(dim=-1)
        return float(lp.gather(1, ans[0].unsqueeze(1)).mean())


class TelepathyTeam:
    def __init__(self, topology: str = "sequential", mode: str = "auto", latent_steps: int = 10,
                 config: Config | None = None, policy: policy_mod.Policy | None = None,
                 subtitles: bool = False, seed: int = 0, on_event=None, same=honesty.default_same,
                 share: str = "auto", demo: bool = False, scan_llm=None, subtitle_style: str = "plain",
                 task: str = "math"):
        """share: 'auto' follows the policy (thoughts_only only where a handoff crosses roles with
        different context), 'full' never crops, 'thoughts_only' crops every latent handoff.
        demo: turns on the demo-only instruction scan. scan_llm: optional Token Factory client for the
        model scan (costs money, so it is never created implicitly)."""
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if share not in SHARE_MODES:
            raise ValueError(f"share must be one of {SHARE_MODES}")
        self.topology, self.mode, self.latent_steps = topology, mode, latent_steps
        self.policy = policy or policy_mod.Policy.load()
        self.subtitles, self.same, self.on_event = subtitles, same, on_event
        self.share, self.demo, self.scan_llm = share, demo, scan_llm
        self.subtitle_style = subtitle_style
        self.task = task
        self.rng = random.Random(seed)
        self.lm = LocalModel.get(config or Config())
        self._ctx = RunCtx()
        self._scans: dict = {}

    def _emit(self, type_: str, **data):
        if self.on_event:
            self.on_event({"type": type_, **data})

    def _tok(self, role, user_cb):
        """Token callback that streams a `token` event for `role` and forwards to the caller's."""
        def cb(text):
            self._emit("token", role=role, text=text)
            if user_cb:
                user_cb(text)
        return cb

    # ---- safety helpers
    def _taint_of(self, i: int) -> str:
        t = self._ctx.tainted
        return "direct" if i in t else ("inherited" if t and i > min(t) else "clean")

    def _shares_thoughts_only(self, reads: bool) -> bool:
        if self.share == "thoughts_only":
            return True
        return self.share == "auto" and self.policy.share_default == "thoughts_only" and reads

    def _scan(self, emit, quiet: bool, i: int, role: str, text: str) -> str:
        """Instruction scan of a tainted text handoff. May warn or block; can never clear."""
        p = self.policy
        if not (p.untrusted_scan == "always" or (p.untrusted_scan == "demo_only" and self.demo)):
            return text
        r = scan_mod.scan(text, self.scan_llm, p.scan_action)
        info = {"flagged": r.flagged, "reasons": r.reasons, "action": r.action}
        if not quiet:
            self._scans[i] = info
        emit("scan", handoff=i, role=role, **info)
        return scan_mod.BLOCK_NOTICE if r.blocked else text

    # One pass over agents `start..` then the final agent. Used for the main run, for path B of the
    # honesty check, and for re-running from a snapshot after a fallback.
    # Returns (answer, first-token probs, English tokens written).
    def _run_from(self, question, context, plan, start, past, notes, subs, texts, snapshots, gen_subs,
                  on_token=None, quiet=False, teacher=None):
        early, final = split_team(self.topology)
        lm, written, ctx = self.lm, 0, self._ctx
        outside = bool(context) and bool(ctx.sources)
        emit = (lambda *a, **k: None) if quiet else self._emit  # the honesty replay stays silent
        for i in range(start, len(early)):
            role = early[i]
            assert_bound(past, ctx.run_id)
            if i in plan.audited:
                snapshots[i] = (fork(past), notes)  # the state just before agent i
            reads = bool(context) and reads_content(self.topology, role)
            ids = lm.prompt_ids(role, question, notes, context if reads else "", first=past is None, task=self.task)
            notes = ""  # notes only go into the first prompt after a restart
            emit("agent_started", role=role)
            if reads and outside:
                emit("outside_content", role=role, sources=list(ctx.sources), count=len(ctx.sources))
            reason = plan.reasons.get(i)
            if i in plan.forced_text and reason == "tainted":
                # The agent read outside content. Decode on a COPY, so its raw untrusted tokens never
                # enter the shared memory; only its visible, scannable text crosses to the next agent.
                text, n, _ = lm.decode(ids, fork(past), on_token=None if quiet else self._tok(role, None))
                written += n
                text = self._scan(emit, quiet, i, role, text)
                texts[i] = text
                notes = f"\n[{role.title()}]: {text}"
            elif i in plan.forced_text:
                texts[i], n, past = lm.decode(ids, past, close=True,
                                              on_token=None if quiet else self._tok(role, None))
                bind(past, ctx.run_id)
                written += n
            else:
                past = bind(think(lm.model, ids, past, self.latent_steps, lm.target_norm,
                                  on_step=None if quiet else (lambda j, r=role: self._emit("latent_step", role=r, i=j))),
                            ctx.run_id)
                if gen_subs(i):
                    subs[i] = make_subtitle(lm, past, style=self.subtitle_style)
                    emit("subtitle", handoff=i, role=role, text=subs[i])
                if self._shares_thoughts_only(reads):
                    past = keep_last(past, self.latent_steps)  # hand over the silent steps, not the input history
            nxt_role = early[i + 1] if i + 1 < len(early) else final
            info = {"from": role, "to": nxt_role, "handoff": i, "taint": self._taint_of(i),
                    "mode_used": "text" if i in plan.forced_text else "latent", "cache_len": length(past)}
            if reason:
                info["reason"] = reason
            if i not in plan.forced_text:
                info["share"] = "thoughts_only" if self._shares_thoughts_only(reads) else "full"
            emit("handoff", **info)
        assert_bound(past, ctx.run_id)
        reads_final = bool(context) and reads_content(self.topology, final)
        ids = lm.prompt_ids(final, question, notes, context if reads_final else "", first=past is None, task=self.task)
        emit("agent_started", role=final)
        lm.last_score = lm.score(ids, fork(past), teacher) if teacher else None
        answer, n, _ = lm.decode(ids, past, on_token=None if quiet else self._tok(final, on_token))
        return answer, lm.first_probs, written + n

    def _keep_answer(self, state: RunState):
        lps = self.lm.last_logps
        state.answer_ids = list(self.lm.last_ids)
        state.answer_lp = sum(lps) / len(lps) if lps else None

    def _audit_and_fallback(self, state: RunState, gen_subs, on_token=None):
        """Check each audited handoff in order. An unfaithful one is redone in English from its
        snapshot, and the later handoffs are re-run from there."""
        self._ctx = state.ctx
        for k in sorted(state.plan.audited):
            if k in state.plan.forced_text or k not in state.subs:
                continue
            res = honesty.check(self, state, k)
            ok, js = res.faithful, res.js
            state.faithful[k], state.js[k], state.gap[k] = ok, js, res.gap
            decision = policy_mod.decide(self.policy, ok, state.fallbacks)
            self._emit("honesty", handoff=k, role=state.early[k], faithful=ok, js=js, decision=decision)
            if decision != "switch_to_text":
                continue
            state.plan.forced_text.add(k)
            state.plan.reasons[k] = "unfaithful"
            state.fallbacks += 1
            self._emit("fallback", handoff=k, role=state.early[k], reason="unfaithful subtitle")
            past, notes = state.snapshots[k]
            state.answer, state.first_probs, n = self._run_from(
                state.question, state.context, state.plan, k, fork(past), notes, state.subs,
                state.texts, state.snapshots, gen_subs, on_token)
            state.written += n
            self._keep_answer(state)
            state.subs.pop(k, None)
            state.faithful[k] = False  # stays recorded as flagged; mode_used is now text

    def run(self, question: str, context="", on_token=None) -> RunResult:
        """`question` is the user's own text (TRUSTED). `context` is outside content: a string
        (treated as UNTRUSTED), a Content, or a list of Content with their sources."""
        early, final = split_team(self.topology)
        lm = self.lm
        lm.sync()
        t0 = time.perf_counter()
        state, handoffs = None, []
        contents = trust.normalize_context(context)
        outside = [c for c in contents if c.trust is trust.Trust.UNTRUSTED]
        context_text = trust.format_context(contents)
        tainted_idx = ({i for i, r in enumerate(early) if reads_content(self.topology, r)}
                       if outside else set())
        self._ctx = RunCtx(uuid.uuid4().hex[:12], [c.source for c in outside], tainted_idx)
        self._scans = {}
        self._emit("run_started", run_id=self._ctx.run_id, mode=self.mode, topology=self.topology,
                   question=question, roles=early + [final], outside_sources=self._ctx.sources)

        if self.mode == "single":
            if outside:
                self._emit("outside_content", role=final, sources=self._ctx.sources, count=len(outside))
            ans, n, _ = lm.decode(lm.prompt_ids(final, question, context=context_text, task=self.task),
                                  on_token=self._tok(final, on_token))
            written, steps = n, 0

        elif self.mode == "text":
            notes, written = "", 0
            for i, role in enumerate(early):
                reads = bool(context_text) and reads_content(self.topology, role)
                self._emit("agent_started", role=role)
                if reads and outside:
                    self._emit("outside_content", role=role, sources=self._ctx.sources, count=len(outside))
                out, n, _ = lm.decode(lm.prompt_ids(role, question, notes, context_text if reads else "", task=self.task),
                                      on_token=self._tok(role, None))
                written += n
                if i in tainted_idx:
                    out = self._scan(self._emit, False, i, role, out)
                handoffs.append(Handoff(role, "text", text=out, taint=self._taint_of(i), scan=self._scans.get(i)))
                notes += f"\n[{role.title()}]: {out}"
                self._emit("handoff", **{"from": role, "to": (early + [final])[i + 1], "handoff": i,
                                         "mode_used": "text", "taint": self._taint_of(i)})
            self._emit("agent_started", role=final)
            ans, n, _ = lm.decode(lm.prompt_ids(final, question, notes,
                                                context_text if reads_content(self.topology, final) else "",
                                                task=self.task),
                                  on_token=self._tok(final, on_token))
            written, steps = written + n, 0

        else:  # latent / auto
            base = self.policy if self.mode == "auto" else replace(self.policy, honesty_check="off")
            plan = policy_mod.make_plan(base, early, self.rng, tainted_idx)
            state = RunState(question, context_text, early, plan, self._ctx)
            want_subs = lambda i: self.subtitles or i in state.plan.audited  # noqa: E731
            state.answer, state.first_probs, state.written = self._run_from(
                question, context_text, plan, 0, None, "", state.subs, state.texts, state.snapshots,
                want_subs, on_token)
            self._keep_answer(state)
            if self.mode == "auto":
                self._audit_and_fallback(state, want_subs, on_token)
            for i, role in enumerate(early):
                handoffs.append(Handoff(role, "text" if i in state.plan.forced_text else "latent",
                                        text=state.texts.get(i, ""), subtitle=state.subs.get(i),
                                        faithful=state.faithful.get(i), js=state.js.get(i),
                                        reason=state.plan.reasons.get(i), taint=self._taint_of(i),
                                        scan=self._scans.get(i)))
            ans, written = state.answer, state.written
            steps = self.latent_steps * (len(early) - len(state.plan.forced_text))

        lm.sync()
        metrics = {"seconds": time.perf_counter() - t0, "tokens_written": written, "latent_steps": steps,
                   "fallbacks": state.fallbacks if state else 0, "run_id": self._ctx.run_id,
                   "tainted": bool(outside) and (self.mode == "single" or bool(tainted_idx)),
                   "outside_sources": self._ctx.sources,
                   "forced_text_handoffs": len(state.plan.forced_text) if state else len(early)}
        self._emit("final", answer=ans, metrics=metrics)
        self._emit("run_finished")
        return RunResult(ans, handoffs, metrics, state)
