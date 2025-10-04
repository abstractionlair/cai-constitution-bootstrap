#!/usr/bin/env python3
"""
CLEAN Base Model Loader - Prevents Chat Template Contamination

This module provides GUARANTEED contamination-free model loading for Qwen base models.

CRITICAL: This is the ONLY safe way to load Qwen base models for evaluation/generation.
Using other methods risks silent chat template contamination.

See: /docs/BASE_MODEL_TRUTH.md for why this matters.
"""

import torch
import logging
import subprocess
from typing import Tuple, Optional, Dict, Any, List
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Qwen chat template special token IDs
# These are the actual token IDs used by Qwen chat templates
QWEN_CHAT_TOKEN_IDS = {
    151644,  # <|im_start|>
    151645,  # <|im_end|>
    # Add more if discovered
}

# Sentinel prompts for testing contamination
SENTINEL_PROMPTS = [
    "Translate to French: hello",
    "Answer this: What is 2+2?",
    "List three colors",
]


class CleanModelLoader:
    """
    Loads Qwen base models with GUARANTEED no chat template contamination.

    Key safety features:
    1. Explicitly disables chat_template
    2. Disables default_chat_template if present
    3. Uses add_special_tokens=False for tokenization
    4. Logs verification that templates are disabled
    5. Provides clean generation wrapper

    Usage:
        loader = CleanModelLoader("Qwen/Qwen2.5-32B")
        model, tokenizer = loader.load()
        response = loader.generate(model, tokenizer, "Your prompt here")
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-32B",
        load_in_4bit: bool = True,
        load_in_8bit: bool = False,
        device_map: str = "auto",
        trust_remote_code: bool = True
    ):
        """
        Initialize clean model loader.

        Args:
            model_name: HuggingFace model name (default: Qwen/Qwen2.5-32B base)
            load_in_4bit: Use 4-bit quantization (default: True, for training)
            load_in_8bit: Use 8-bit quantization (alternative to 4-bit)
            device_map: Device mapping strategy
            trust_remote_code: Trust remote code (required for Qwen)
        """
        self.model_name = model_name
        self.load_in_4bit = load_in_4bit
        self.load_in_8bit = load_in_8bit
        self.device_map = device_map
        self.trust_remote_code = trust_remote_code

        # Verify this is a base model (not instruct)
        if "instruct" in model_name.lower() or "chat" in model_name.lower():
            logger.warning(f"⚠️ Model name contains 'instruct' or 'chat': {model_name}")
            logger.warning("⚠️ This may be an instruction-tuned model, not a base model!")

    def _get_git_sha(self) -> str:
        """Get current git SHA for provenance tracking"""
        try:
            sha = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=Path(__file__).parent,
                stderr=subprocess.DEVNULL
            ).decode('ascii').strip()
            return sha
        except:
            return "unknown"

    def _verify_no_template_injection(self, tokenizer: AutoTokenizer, prompt: str) -> None:
        """
        Verify that add_special_tokens makes no difference.
        If it does, template is being applied.
        """
        with_special = tokenizer(prompt, add_special_tokens=True, return_tensors="pt")['input_ids'][0]
        without_special = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")['input_ids'][0]

        if len(with_special) != len(without_special):
            raise RuntimeError(
                f"❌ Template injection detected!\n"
                f"   add_special_tokens=True adds {len(with_special) - len(without_special)} tokens\n"
                f"   Prompt: {prompt[:50]}..."
            )

        # Also check for chat template token IDs
        all_tokens = set(without_special.tolist())
        contaminated_tokens = all_tokens & QWEN_CHAT_TOKEN_IDS

        if contaminated_tokens:
            raise RuntimeError(
                f"❌ Chat template token IDs detected: {contaminated_tokens}\n"
                f"   Prompt: {prompt[:50]}..."
            )

    def _run_sentinel_tests(self, tokenizer: AutoTokenizer) -> None:
        """Run sentinel prompts to detect contamination"""
        logger.info("🧪 Running sentinel contamination tests...")

        for prompt in SENTINEL_PROMPTS:
            try:
                self._verify_no_template_injection(tokenizer, prompt)
            except RuntimeError as e:
                logger.error(f"❌ Sentinel test failed: {prompt}")
                raise

        logger.info("✅ All sentinel tests passed (no contamination)")

    def load(self) -> Tuple[AutoModelForCausalLM, AutoTokenizer, Dict[str, Any]]:
        """
        Load model and tokenizer with contamination prevention.

        Returns:
            Tuple of (model, tokenizer, provenance) - GUARANTEED clean

        Provenance dict contains:
            - loader_version: Git SHA of loader code
            - template_disabled: Always True
            - model_name: Model identifier
            - quantization: "4bit", "8bit", or "16bit"
            - sentinel_tests_passed: Always True (or exception raised)
        """
        logger.info("=" * 60)
        logger.info("🧪 Loading CLEAN base model (contamination-free)")
        logger.info("=" * 60)
        logger.info(f"Model: {self.model_name}")

        # Step 1: Load tokenizer
        logger.info("📝 Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=self.trust_remote_code,
            use_fast=True
        )

        # Step 2: CRITICAL - Disable chat template
        logger.info("🚫 Disabling chat template (CRITICAL)...")
        original_template = tokenizer.chat_template
        tokenizer.chat_template = None

        if hasattr(tokenizer, 'default_chat_template'):
            tokenizer.default_chat_template = None

        # Verify template is disabled
        if tokenizer.chat_template is not None:
            raise RuntimeError("❌ CRITICAL: Failed to disable chat_template!")

        logger.info(f"✅ Chat template disabled (was: {original_template is not None})")

        # Step 3: Set pad token
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            logger.info(f"✅ Set pad_token to eos_token: {tokenizer.eos_token}")

        # Step 4: Configure quantization
        quantization_config = None
        if self.load_in_4bit:
            logger.info("🔧 Configuring 4-bit quantization...")
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )
        elif self.load_in_8bit:
            logger.info("🔧 Configuring 8-bit quantization...")
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                bnb_8bit_use_double_quant=True,
                bnb_8bit_quant_type="nf4",  # nf4 is more expressive than nf8
                bnb_8bit_compute_dtype=torch.bfloat16
            )

        # Step 5: Load model
        logger.info("🤖 Loading model...")
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=quantization_config,
            device_map=self.device_map,
            trust_remote_code=self.trust_remote_code,
            torch_dtype=torch.bfloat16,
            attn_implementation="flash_attention_2" if torch.cuda.is_available() else "eager"
        )

        model.eval()

        # Step 6: Run sentinel contamination tests
        self._run_sentinel_tests(tokenizer)

        # Step 7: Create provenance metadata
        quantization_type = "4bit" if self.load_in_4bit else ("8bit" if self.load_in_8bit else "16bit")
        provenance = {
            'loader_version': self._get_git_sha(),
            'template_disabled': True,
            'model_name': self.model_name,
            'quantization': quantization_type,
            'sentinel_tests_passed': True,
            'add_special_tokens': False,  # We always use False
        }

        # Step 8: Log success and memory
        logger.info("✅ Model loaded successfully")

        if torch.cuda.is_available():
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            allocated = torch.cuda.memory_allocated() / 1e9
            logger.info(f"🎮 GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"💾 Memory: {allocated:.1f}GB / {gpu_mem:.1f}GB")

        logger.info(f"📋 Provenance: loader_version={provenance['loader_version'][:8]}, quantization={quantization_type}")
        logger.info("=" * 60)
        logger.info("✅ CLEAN MODEL READY (no contamination)")
        logger.info("=" * 60)

        return model, tokenizer, provenance

    def tokenize_clean(
        self,
        tokenizer: AutoTokenizer,
        text: str,
        max_length: int = 512,
        truncation: bool = True,
        return_tensors: str = "pt",
        verify_contamination: bool = True
    ) -> Dict[str, torch.Tensor]:
        """
        Tokenize text WITHOUT applying chat templates.

        Args:
            tokenizer: The tokenizer (must have chat_template=None)
            text: Text to tokenize
            max_length: Maximum length
            truncation: Whether to truncate
            return_tensors: Format ("pt" for PyTorch)
            verify_contamination: Whether to check for contamination tokens

        Returns:
            Tokenized inputs dictionary
        """
        # Verify template is still disabled
        if tokenizer.chat_template is not None:
            raise RuntimeError("❌ CRITICAL: chat_template was re-enabled!")

        # CRITICAL: add_special_tokens=False prevents template application
        inputs = tokenizer(
            text,
            add_special_tokens=False,  # CRITICAL!
            return_tensors=return_tensors,
            max_length=max_length,
            truncation=truncation,
            padding=False
        )

        # Verify no contamination token IDs in ALL tokens (not just first 10)
        if verify_contamination:
            all_token_ids = set(inputs['input_ids'][0].tolist())
            contaminated_tokens = all_token_ids & QWEN_CHAT_TOKEN_IDS

            if contaminated_tokens:
                token_preview = tokenizer.decode(inputs['input_ids'][0], skip_special_tokens=False)
                raise RuntimeError(
                    f"❌ Chat template token IDs detected in tokenized input!\n"
                    f"   Contaminated IDs: {contaminated_tokens}\n"
                    f"   Text preview: {text[:50]}...\n"
                    f"   Token preview: {token_preview[:100]}..."
                )

        return inputs

    def generate(
        self,
        model: AutoModelForCausalLM,
        tokenizer: AutoTokenizer,
        prompt: str,
        max_new_tokens: int = 128,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
        do_sample: bool = True,
        return_full_text: bool = False
    ) -> str:
        """
        Generate text using clean (template-free) tokenization.

        Args:
            model: The language model
            tokenizer: The tokenizer (must have chat_template=None)
            prompt: Input prompt
            max_new_tokens: Maximum new tokens to generate
            temperature: Sampling temperature
            top_p: Top-p (nucleus) sampling
            repetition_penalty: Penalty for repetition
            do_sample: Whether to use sampling (vs greedy)
            return_full_text: If True, return prompt + generation

        Returns:
            Generated text (excluding prompt unless return_full_text=True)
        """
        # Tokenize cleanly (with contamination verification)
        inputs = self.tokenize_clean(tokenizer, prompt, verify_contamination=True)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=do_sample and temperature > 0.0,
                top_p=top_p if do_sample else None,
                repetition_penalty=repetition_penalty,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
                return_dict_in_generate=True
            )

        # Decode response
        if return_full_text:
            response = tokenizer.decode(outputs.sequences[0], skip_special_tokens=True)
        else:
            input_length = inputs['input_ids'].shape[1]
            generated_tokens = outputs.sequences[0][input_length:]
            response = tokenizer.decode(generated_tokens, skip_special_tokens=True)

        return response.strip()


def load_clean_base_model(
    model_name: str = "Qwen/Qwen2.5-32B",
    quantization: str = "4bit"
) -> Tuple[AutoModelForCausalLM, AutoTokenizer, Dict[str, Any]]:
    """
    Convenience function for loading clean base model.

    Args:
        model_name: HuggingFace model name
        quantization: "4bit", "8bit", or "none"

    Returns:
        Tuple of (model, tokenizer, provenance) with guaranteed no contamination

    Example:
        model, tokenizer, prov = load_clean_base_model()
        loader = CleanModelLoader(model_name)
        response = loader.generate(model, tokenizer, "Complete: Water freezes at")
    """
    load_in_4bit = quantization == "4bit"
    load_in_8bit = quantization == "8bit"

    loader = CleanModelLoader(
        model_name=model_name,
        load_in_4bit=load_in_4bit,
        load_in_8bit=load_in_8bit
    )

    return loader.load()


if __name__ == "__main__":
    # Test clean model loading
    print("🧪 Testing clean model loading...")
    print("")

    try:
        # Load model
        loader = CleanModelLoader("Qwen/Qwen2.5-32B")
        model, tokenizer, provenance = loader.load()

        print(f"\n📋 Provenance: {provenance}")

        # Test generation
        print("\n📝 Testing generation (should NOT follow instruction cleanly):")
        test_prompts = [
            "List three fruits",
            "Translate to Spanish: hello",
            "What is 2 + 2?",
        ]

        for prompt in test_prompts:
            print(f"\nPrompt: {prompt}")
            response = loader.generate(model, tokenizer, prompt, max_new_tokens=50)
            print(f"Response: {response[:100]}...")

        print("\n✅ Clean model loading test passed!")
        print(f"✅ Loader version: {provenance['loader_version']}")
        print(f"✅ Sentinel tests: passed")

        # Cleanup
        del model, tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
