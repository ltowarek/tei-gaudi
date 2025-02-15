import torch

from loguru import logger
from pathlib import Path
from typing import Optional
from transformers import AutoConfig
from transformers.models.bert import BertConfig

from text_embeddings_server.models.model import Model
from text_embeddings_server.models.default_model import DefaultModel

__all__ = ["Model"]

HTCORE_AVAILABLE = True
try:
    import habana_frameworks.torch.core as htcore
except ImportError as e:
    logger.warning(f"Could not import htcore: {e}")
    HTCORE_AVAILABLE = False

# Disable gradients
torch.set_grad_enabled(False)

FLASH_ATTENTION = True
try:
    from text_embeddings_server.models.flash_bert import FlashBert
except ImportError as e:
    logger.warning(f"Could not import Flash Attention enabled models: {e}")
    FLASH_ATTENTION = False

if FLASH_ATTENTION:
    __all__.append(FlashBert)


def get_model(model_path: Path, dtype: Optional[str]):
    if dtype == "float32":
        dtype = torch.float32
    elif dtype == "float16":
        dtype = torch.float16
    elif dtype == "bfloat16":
        dtype = torch.bfloat16
    else:
        raise RuntimeError(f"Unknown dtype {dtype}")

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif HTCORE_AVAILABLE and torch.hpu.is_available():
        device = torch.device("hpu")
    else:
        if dtype != torch.float32:
            raise ValueError("CPU device only supports float32 dtype")
        device = torch.device("cpu")

    config = AutoConfig.from_pretrained(model_path)

    if config.model_type == "bert":
        config: BertConfig
        if (
            device.type == "cuda"
            and config.position_embedding_type == "absolute"
            and dtype in [torch.float16, torch.bfloat16]
            and FLASH_ATTENTION
        ):
            return FlashBert(model_path, device, dtype)
        else:
            return DefaultModel(model_path, device, dtype)

    raise NotImplementedError
