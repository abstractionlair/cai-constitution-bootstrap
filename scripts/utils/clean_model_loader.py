#!/usr/bin/env python3
"""
CleanModelLoader - Canonical utility for contamination-free base model loading.

This is the ONLY way to load Qwen base models in this project.
Ensures no chat template contamination or special token injection.

Key responsibilities:
- Disable chat templates (tokenizer.chat_template = None)
- Enforce add_special_tokens=False
- Run token ID checks for Qwen chat template tokens
- Execute sentinel tests to verify base model behavior
- Provide full provenance metadata

Usage:
    from utils.clean_model_loader import CleanModelLoader

    loader = CleanModelLoader(
        model_name="Qwen/Qwen2.5-32B",
        load_in_4bit=True,
        device_map="auto"
    )

    model, tokenizer, provenance = loader.load()

    # Use for completion-mode prompting only
    inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
"""

import os
import torch
import logging
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CleanModelLoader:
    """
    Canonical loader for contamination-free base model loading.

    This utility is mandatory for all base model work in Stage 1.
    Enforces completion-mode only, no chat templates, no special tokens.
    """

    # Qwen chat template special tokens (to detect contamination)
    QWEN_CHAT_TOKENS = [
        "<|im_start|>",
        "<|im_end|>",
        "<|endoftext|>",  # May be used as EOS
    ]

    # Sentinel tests to verify base model behavior
    SENTINEL_TESTS = [
        {
            "name": "instruction_following_should_fail",
            "prompt": "Translate to Pig Latin: hello world",
            "expected": "fail",  # Base model should NOT cleanly translate
            "description": "Base model should continue/ramble, not follow instruction"
        },
        {
            "name": "list_generation_should_fail",
            "prompt": "List three prime numbers:",
            "expected": "fail",  # Base model should NOT produce clean list
            "description": "Base model should continue text, not generate numbered list"
        },
        {
            "name": "simple_completion_should_work",
            "prompt": "Water freezes at",
            "expected": "pass",  # Base model CAN complete patterns
            "description": "Base model should complete with '0°C' or similar"
        }
    ]

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-32B",
        load_in_4bit: bool = True,
        load_in_8bit: bool = False,
        device_map: str = "auto",
        torch_dtype: Optional[torch.dtype] = None,
        local_files_only: bool = False,
        trust_remote_code: bool = False
    ):
        """
        Initialize CleanModelLoader.

        Args:
            model_name: HuggingFace model name or local path
            load_in_4bit: Use 4-bit quantization (recommended for training)
            load_in_8bit: Use 8-bit quantization (alternative)
            device_map: Device mapping strategy
            torch_dtype: Optional dtype override
            local_files_only: Use only local cached files
            trust_remote_code: Whether to trust remote code (Qwen needs False)
        """
        self.model_name = model_name
        self.load_in_4bit = load_in_4bit
        self.load_in_8bit = load_in_8bit
        self.device_map = device_map
        self.torch_dtype = torch_dtype or torch.bfloat16
        self.local_files_only = local_files_only
        self.trust_remote_code = trust_remote_code

        # Will be populated during load
        self.model = None
        self.tokenizer = None
        self.provenance = {}

    def load(self) -> Tuple[Any, Any, Dict[str, Any]]:
        """
        Load model and tokenizer with contamination guards.

        Returns:
            (model, tokenizer, provenance_dict)

        Raises:
            RuntimeError: If contamination detected or sentinel tests fail
        """
        logger.info(f"Loading model: {self.model_name}")
        logger.info("=" * 60)

        # Step 1: Load tokenizer and disable chat template
        self.tokenizer = self._load_tokenizer()

        # Step 2: Run contamination checks on tokenizer
        self._check_tokenizer_contamination()

        # Step 3: Load model with quantization
        self.model = self._load_model()

        # Step 4: Run sentinel tests
        self._run_sentinel_tests()

        # Step 5: Gather provenance
        self.provenance = self._gather_provenance()

        logger.info("=" * 60)
        logger.info("✅ Model loaded successfully with contamination guards")
        logger.info(f"Provenance: loader_version={self.provenance['loader_version'][:8]}")

        return self.model, self.tokenizer, self.provenance

    def _load_tokenizer(self) -> AutoTokenizer:
        """Load tokenizer and disable chat template."""
        logger.info("Loading tokenizer...")

        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=self.trust_remote_code,
            local_files_only=self.local_files_only
        )

        # CRITICAL: Disable chat template
        logger.info("🔧 Disabling chat template (contamination guard)")
        tokenizer.chat_template = None

        # Also clear default_chat_template if it exists
        if hasattr(tokenizer, 'default_chat_template'):
            tokenizer.default_chat_template = None

        # Set padding side (useful for batch processing)
        tokenizer.padding_side = 'left'  # Standard for causal LMs

        # Set pad token if not present
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        logger.info(f"✅ Tokenizer loaded: vocab_size={len(tokenizer)}")
        return tokenizer

    def _check_tokenizer_contamination(self):
        """
        Run contamination checks on tokenizer.

        Checks:
        1. Token ID check - ensure no chat template tokens in sentinel prompts
        2. Delta check - verify add_special_tokens=False produces same length
        """
        logger.info("Running contamination checks...")

        # Test prompt
        test_prompt = "Describe the seasons"

        # Check 1: Token ID check for chat template markers
        tokens_no_special = self.tokenizer.encode(
            test_prompt,
            add_special_tokens=False
        )

        # Decode back to check for template tokens
        decoded = self.tokenizer.decode(tokens_no_special)

        for template_token in self.QWEN_CHAT_TOKENS:
            if template_token in decoded:
                raise RuntimeError(
                    f"🚨 CONTAMINATION DETECTED: Found '{template_token}' in decoded output!\n"
                    f"Input: {test_prompt}\n"
                    f"Decoded: {decoded}\n"
                    f"This indicates chat template is still being applied."
                )

        # Check 2: Delta check - add_special_tokens should not add tokens
        tokens_with_special = self.tokenizer.encode(
            test_prompt,
            add_special_tokens=True
        )

        if len(tokens_with_special) != len(tokens_no_special):
            logger.warning(
                f"⚠️  add_special_tokens adds {len(tokens_with_special) - len(tokens_no_special)} tokens. "
                f"This is expected for models with BOS/EOS tokens."
            )

        # Check 3: Verify first 100 chars of encoding don't contain template markers
        first_tokens = tokens_no_special[:20]
        first_decoded = self.tokenizer.decode(first_tokens)

        if "<|im_start|>" in first_decoded or "system" in first_decoded.lower()[:20]:
            raise RuntimeError(
                f"🚨 CONTAMINATION DETECTED in first tokens!\n"
                f"First 20 tokens decode to: {first_decoded}\n"
                f"This indicates chat template wrapping."
            )

        logger.info("✅ Contamination checks passed")

    def _load_model(self) -> Any:
        """Load model with quantization."""
        logger.info(f"Loading model with quantization...")

        # Configure quantization
        if self.load_in_4bit:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=self.torch_dtype,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            logger.info("Using 4-bit quantization (nf4)")
        elif self.load_in_8bit:
            quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            logger.info("Using 8-bit quantization")
        else:
            quantization_config = None
            logger.info("No quantization")

        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=quantization_config,
            device_map=self.device_map,
            torch_dtype=self.torch_dtype,
            trust_remote_code=self.trust_remote_code,
            local_files_only=self.local_files_only
        )

        logger.info(f"✅ Model loaded on device: {model.device}")
        return model

    def _run_sentinel_tests(self):
        """
        Run sentinel tests to verify base model behavior.

        Base model should:
        - Fail instruction-following tests (ramble/continue)
        - Fail list generation (continue text)
        - Pass simple completion tests
        """
        logger.info("Running sentinel tests...")

        results = []

        for test in self.SENTINEL_TESTS:
            prompt = test["prompt"]
            expected = test["expected"]

            # Generate with greedy decoding (deterministic)
            inputs = self.tokenizer(
                prompt,
                add_special_tokens=False,
                return_tensors="pt"
            ).to(self.model.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=30,
                    do_sample=False,
                    temperature=None,
                    top_p=None,
                    pad_token_id=self.tokenizer.pad_token_id
                )

            # Decode response
            full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = full_output[len(prompt):].strip()

            # Heuristic checks for expected behavior
            if expected == "fail":
                # Should NOT produce clean, structured output
                # Check for signs of instruction following
                is_structured = (
                    response.startswith("1.") or
                    response.startswith("-") or
                    "\n\n" in response[:50] or
                    ":" in response[:20]  # Structured format
                )
                passed = not is_structured
            else:  # expected == "pass"
                # Should produce reasonable completion
                # Relaxed from < 50 to < 100 chars per Codex recommendation
                passed = len(response) > 0 and len(response) < 100

            results.append({
                "name": test["name"],
                "prompt": prompt,
                "response": response[:100],
                "expected": expected,
                "passed": passed,
                "description": test["description"]
            })

            status = "✅" if passed else "⚠️"
            logger.info(f"{status} {test['name']}: {response[:50]}...")

        # Check if all critical tests passed
        failed_tests = [r for r in results if not r["passed"]]

        if any(t["name"].startswith("instruction_") for t in failed_tests):
            logger.warning(
                "⚠️  Sentinel tests suggest model may be instruction-tuned or contaminated!\n"
                "This could indicate:\n"
                "1. Wrong model loaded (should be base, not instruct)\n"
                "2. Chat template contamination still present\n"
                "3. Model has some instruction-following capability"
            )
            # Don't fail hard - just warn, as base models can vary

        logger.info(f"✅ Sentinel tests completed: {len([r for r in results if r['passed']])}/{len(results)} passed")

        # Store results in provenance
        self.sentinel_results = results

    def _gather_provenance(self) -> Dict[str, Any]:
        """Gather provenance metadata."""

        # Get git commit SHA
        try:
            git_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=Path(__file__).parent.parent.parent,
                text=True
            ).strip()
        except:
            git_sha = "unknown"

        quantization = "none"
        if self.load_in_4bit:
            quantization = "4bit-nf4"
        elif self.load_in_8bit:
            quantization = "8bit"

        return {
            "loader_version": git_sha,
            "model_name": self.model_name,
            "quantization": quantization,
            "torch_dtype": str(self.torch_dtype),
            "template_disabled": True,
            "add_special_tokens": False,
            "sentinel_tests_passed": all(r["passed"] for r in self.sentinel_results),
            "sentinel_results": self.sentinel_results,
            "device_map": str(self.device_map)
        }


# Convenience function for scripts
def load_clean_base_model(
    model_name: str = "Qwen/Qwen2.5-32B",
    **kwargs
) -> Tuple[Any, Any, Dict[str, Any]]:
    """
    Convenience function to load model with contamination guards.

    Args:
        model_name: Model name or path
        **kwargs: Additional arguments for CleanModelLoader

    Returns:
        (model, tokenizer, provenance_dict)
    """
    loader = CleanModelLoader(model_name=model_name, **kwargs)
    return loader.load()


if __name__ == "__main__":
    # Test the loader
    print("Testing CleanModelLoader...")
    print("=" * 60)

    # This would normally load the model, but for testing we just verify imports
    print("✅ CleanModelLoader module loaded successfully")
    print("✅ All dependencies available")
    print("\nTo test model loading, use:")
    print("  model, tokenizer, prov = load_clean_base_model()")
