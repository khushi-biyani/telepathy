"""Silent latent thinking. Method follows LatentMAS (Gen-Verse/LatentMAS, Apache-2.0),
re-implemented in simplified form: the last hidden state is fed back as the next input
embedding, rescaled to the typical norm of a real token embedding."""
from __future__ import annotations

import torch


def embedding_target_norm(model) -> float:
    """Mean L2 norm of the input-embedding rows. Compute once per model."""
    return model.get_input_embeddings().weight.float().norm(dim=1).mean().item()


@torch.inference_mode()
def think(model, ids, past, steps: int, target_norm: float, on_step=None):
    """One silent agent turn: read `ids` (the agent's prompt), then think `steps` latent steps.
    Returns the grown cache. The agent writes no text."""
    out = model(input_ids=ids, past_key_values=past, use_cache=True, output_hidden_states=True)
    past = out.past_key_values
    h = out.hidden_states[-1][:, -1, :]
    for i in range(steps):
        if on_step:
            on_step(i)
        hf = h.float()
        vec = hf * (target_norm / hf.norm(dim=-1, keepdim=True).clamp_min(1e-6))
        vec = vec.to(h.dtype).unsqueeze(1)
        out = model(inputs_embeds=vec, past_key_values=past, use_cache=True, output_hidden_states=True)
        past = out.past_key_values
        h = out.hidden_states[-1][:, -1, :]
    return past
