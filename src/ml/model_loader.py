"""
Lazy singleton loader for the fine-tuned XLM-RoBERTa model.
Loaded once on first use — app starts cleanly even when model files are absent.
"""
import os
from functools import lru_cache

import torch
from loguru import logger
from transformers import AutoModel, AutoTokenizer


@lru_cache(maxsize=1)
def get_model():
    """
    Returns (tokenizer, model). Cached after first call.
    Raises RuntimeError if model files are missing.
    """
    from src.config import settings

    model_dir = settings.MODEL_PATH
    tokenizer_path = os.path.join(model_dir, "similarity_tokenizer")
    model_path = os.path.join(model_dir, "similarity_model")

    if not os.path.isdir(tokenizer_path) or not os.path.isdir(model_path):
        raise RuntimeError(
            f"XLM-RoBERTa model not found at '{model_dir}'.\n"
            "Place fine-tuned weights at:\n"
            f"  {model_path}/\n"
            f"  {tokenizer_path}/\n"
            "or set MODEL_PATH to the correct directory."
        )

    logger.info(f"Loading XLM-RoBERTa tokenizer from {tokenizer_path}")
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)

    logger.info(f"Loading XLM-RoBERTa model from {model_path}")
    model = AutoModel.from_pretrained(model_path)
    model.eval()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    logger.info(f"Model loaded on device: {device}")

    return tokenizer, model


def is_model_available() -> bool:
    try:
        get_model()
        return True
    except RuntimeError:
        return False
