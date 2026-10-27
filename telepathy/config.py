"""Model id, device/dtype selection and defaults."""
from __future__ import annotations

from dataclasses import dataclass

import torch

DEFAULT_MODEL = "nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1"
# Nemotron Nano v1.1 switches its long reasoning on/off with this system prompt.
DEFAULT_SYSTEM = "detailed thinking off"


def pick_device(name: str = "auto") -> torch.device:
    if name != "auto":
        return torch.device(name)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def pick_dtype(device: torch.device, name: str = "auto") -> torch.dtype:
    """bfloat16 on MPS and on CUDA GPUs that support it, float16 on older CUDA, float32 on CPU."""
    if name != "auto":
        return getattr(torch, name)
    if device.type == "mps":
        return torch.bfloat16
    if device.type == "cuda":
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    return torch.float32


@dataclass
class Config:
    model_id: str = DEFAULT_MODEL
    device: str = "auto"
    dtype: str = "auto"
    system: str = DEFAULT_SYSTEM
    max_new_tokens: int = 384  # cap per agent turn
