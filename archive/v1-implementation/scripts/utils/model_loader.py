#!/usr/bin/env python3
"""
Model loading utilities using Unsloth for efficient training
"""

import torch
from unsloth import FastLanguageModel
from typing import Tuple, Optional
import logging
import os
from pathlib import Path

# Configure base directory for RunPod deployment
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/cai-constitution-bootstrap'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelConfig:
    """Configuration for model loading"""
    
    # Model settings
    MODEL_NAME = "unsloth/Qwen2.5-32B-bnb-4bit"
    MAX_SEQ_LENGTH = 2048
    DTYPE = None  # Auto-detect
    LOAD_IN_4BIT = True
    
    # LoRA settings for training
    LORA_R = 64
    LORA_ALPHA = 16
    LORA_DROPOUT = 0.1
    TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"]
    
    # Generation settings
    MAX_NEW_TOKENS = 512
    TEMPERATURE = 0.7
    TOP_P = 0.9
    DO_SAMPLE = True


def load_base_model(
    model_name: Optional[str] = None,
    max_seq_length: Optional[int] = None,
    load_in_4bit: Optional[bool] = None,
    device_map: str = "auto"
) -> Tuple[FastLanguageModel, any]:
    """
    Load base model for inference or training
    
    Args:
        model_name: Hugging Face model name
        max_seq_length: Maximum sequence length
        load_in_4bit: Whether to use 4-bit quantization
        device_map: Device mapping strategy
        
    Returns:
        Tuple of (model, tokenizer)
    """
    config = ModelConfig()
    
    model_name = model_name or config.MODEL_NAME
    max_seq_length = max_seq_length or config.MAX_SEQ_LENGTH
    load_in_4bit = load_in_4bit if load_in_4bit is not None else config.LOAD_IN_4BIT
    
    logger.info(f"Loading model: {model_name}")
    logger.info(f"Max sequence length: {max_seq_length}")
    logger.info(f"4-bit quantization: {load_in_4bit}")
    
    # Check GPU memory
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        logger.info(f"GPU memory available: {gpu_memory:.1f} GB")
        
        if gpu_memory < 70:
            logger.warning("Less than 70GB GPU memory available. Consider using 4-bit quantization.")
    
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=max_seq_length,
            dtype=config.DTYPE,
            load_in_4bit=load_in_4bit,
            device_map=device_map,
        )
        
        logger.info("✅ Model loaded successfully")
        
        # Print model info
        if hasattr(model, 'get_memory_footprint'):
            memory_footprint = model.get_memory_footprint() / 1e9
            logger.info(f"Model memory footprint: {memory_footprint:.2f} GB")
        
        return model, tokenizer
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


def prepare_model_for_training(
    model: FastLanguageModel,
    lora_r: Optional[int] = None,
    lora_alpha: Optional[int] = None,
    lora_dropout: Optional[float] = None,
    target_modules: Optional[list] = None
) -> FastLanguageModel:
    """
    Prepare model for LoRA training
    
    Args:
        model: Base model
        lora_r: LoRA rank
        lora_alpha: LoRA alpha
        lora_dropout: LoRA dropout rate
        target_modules: Modules to apply LoRA to
        
    Returns:
        Model prepared for training
    """
    config = ModelConfig()
    
    lora_r = lora_r or config.LORA_R
    lora_alpha = lora_alpha or config.LORA_ALPHA
    lora_dropout = lora_dropout or config.LORA_DROPOUT
    target_modules = target_modules or config.TARGET_MODULES
    
    logger.info(f"Preparing model for training with LoRA:")
    logger.info(f"  Rank: {lora_r}")
    logger.info(f"  Alpha: {lora_alpha}")
    logger.info(f"  Dropout: {lora_dropout}")
    logger.info(f"  Target modules: {target_modules}")
    
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_r,
        target_modules=target_modules,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        use_gradient_checkpointing="unsloth",  # Unsloth optimization
        random_state=3407,  # Reproducibility
    )
    
    logger.info("✅ Model prepared for training")
    return model


def load_trained_model(
    checkpoint_path: str,
    base_model_name: Optional[str] = None
) -> Tuple[FastLanguageModel, any]:
    """
    Load a trained model from checkpoint
    
    Args:
        checkpoint_path: Path to trained model checkpoint
        base_model_name: Base model name if different from default
        
    Returns:
        Tuple of (model, tokenizer)
    """
    logger.info(f"Loading trained model from: {checkpoint_path}")
    
    # Load base model first
    model, tokenizer = load_base_model(model_name=base_model_name)
    
    # Load LoRA weights
    try:
        model = FastLanguageModel.from_pretrained(
            model_name=checkpoint_path,
            max_seq_length=ModelConfig.MAX_SEQ_LENGTH,
            dtype=ModelConfig.DTYPE,
            load_in_4bit=ModelConfig.LOAD_IN_4BIT,
        )
        logger.info("✅ Trained model loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load trained model: {e}")
        raise
    
    return model, tokenizer


def generate_text(
    model: FastLanguageModel,
    tokenizer: any,
    prompt: str,
    max_new_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    do_sample: Optional[bool] = None
) -> str:
    """
    Generate text using the model
    
    Args:
        model: The language model
        tokenizer: Model tokenizer
        prompt: Input prompt
        max_new_tokens: Maximum new tokens to generate
        temperature: Sampling temperature
        top_p: Top-p sampling
        do_sample: Whether to use sampling
        
    Returns:
        Generated text
    """
    config = ModelConfig()
    
    max_new_tokens = max_new_tokens or config.MAX_NEW_TOKENS
    temperature = temperature if temperature is not None else config.TEMPERATURE
    top_p = top_p if top_p is not None else config.TOP_P
    do_sample = do_sample if do_sample is not None else config.DO_SAMPLE
    
    # Tokenize input
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    
    # Decode response (remove input tokens)
    input_length = inputs["input_ids"].shape[1]
    generated_tokens = outputs[0][input_length:]
    response = tokenizer.decode(generated_tokens, skip_special_tokens=True)
    
    return response.strip()


def clear_gpu_cache():
    """Clear GPU cache to free memory"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.info("🧹 GPU cache cleared")


def get_model_memory_usage() -> Optional[float]:
    """Get current GPU memory usage in GB"""
    if torch.cuda.is_available():
        memory_allocated = torch.cuda.memory_allocated() / 1e9
        return memory_allocated
    return None


def print_gpu_utilization():
    """Print current GPU utilization"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        total = torch.cuda.get_device_properties(0).total_memory / 1e9
        
        print(f"🎮 GPU Memory Usage:")
        print(f"  Allocated: {allocated:.2f} GB")
        print(f"  Reserved: {reserved:.2f} GB") 
        print(f"  Total: {total:.2f} GB")
        print(f"  Free: {total - reserved:.2f} GB")
    else:
        print("❌ No GPU available")


if __name__ == "__main__":
    # Test model loading
    print("🧪 Testing model loading...")
    
    try:
        model, tokenizer = load_base_model()
        print("✅ Base model loading successful")
        
        # Test generation
        test_prompt = "Answer this question: What is the capital of France?"
        response = generate_text(model, tokenizer, test_prompt, max_new_tokens=50)
        print(f"Test generation: {response}")
        
        # Print memory usage
        print_gpu_utilization()
        
        # Clean up
        del model, tokenizer
        clear_gpu_cache()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")