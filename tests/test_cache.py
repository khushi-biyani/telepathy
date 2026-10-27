import torch

from telepathy.cache_utils import fork, length
from telepathy.latent import think


def test_think_grows_cache_by_prompt_plus_steps(lm):
    ids = lm.prompt_ids("planner", "What is 2+2?")
    for steps in (0, 3, 5):
        past = think(lm.model, ids, None, steps, lm.target_norm)
        assert length(past) == ids.shape[1] + steps


def test_think_continues_existing_cache(lm):
    a = lm.prompt_ids("planner", "What is 2+2?")
    b = lm.prompt_ids("critic", "What is 2+2?", first=False)
    past = think(lm.model, a, None, 2, lm.target_norm)
    n0 = length(past)
    past = think(lm.model, b, past, 3, lm.target_norm)
    assert length(past) == n0 + b.shape[1] + 3


def test_fork_never_mutates_main_cache(lm):
    ids = lm.prompt_ids("planner", "What is 2+2?")
    past = think(lm.model, ids, None, 2, lm.target_norm)
    n0 = length(past)
    key0 = past.layers[0].keys.clone()
    branch = fork(past)
    with torch.inference_mode():
        lm.model(input_ids=ids[:, -1:], past_key_values=branch, use_cache=True)
    assert length(branch) == n0 + 1
    assert length(past) == n0
    assert torch.equal(past.layers[0].keys, key0)
