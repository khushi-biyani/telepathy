import pytest

from telepathy import Config
from telepathy.engine import LocalModel

TINY = "HuggingFaceTB/SmolLM2-135M-Instruct"


@pytest.fixture(scope="session")
def cfg():
    # CPU + float32 so tests don't compete with a GPU benchmark running on the same machine
    return Config(model_id=TINY, device="cpu", dtype="float32", system="You are helpful.", max_new_tokens=12)


@pytest.fixture(scope="session")
def lm(cfg):
    return LocalModel.get(cfg)
