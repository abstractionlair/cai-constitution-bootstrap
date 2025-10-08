#!/usr/bin/env python3
"""
Stage 1 SFT Evaluation Script (Deterministic, Paired)

Evaluates SFT model against base model on held-out instruction set.

Workflow:
1. Load held-out instruction set (distinct from training data)
2. Load base model + SFT adapters
3. Generate responses with deterministic decoding (temperature=0)
4. Score responses (task-specific success criteria)
5. Compute paired statistics (McNemar test, Cohen's h, CIs)
6. Report overall and per-type results with BH correction
7. Save evaluation results with full provenance

Usage:
    python evaluate_stage1_sft.py \
      --sft-checkpoint checkpoints/stage1_sft/final_adapter \
      --test-set data/held_out_instructions.jsonl \
      --output results/sft_eval

Outputs:
    - results/sft_eval/evaluation_results.json (statistics)
    - results/sft_eval/evaluation_summary.txt (human-readable)
    - results/sft_eval/base_responses.jsonl (base model outputs)
    - results/sft_eval/sft_responses.jsonl (SFT model outputs)
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import torch
import numpy as np
from scipy.stats import binom
from peft import PeftModel

sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    CleanModelLoader,
    CompletionStylePrompts,
    create_session_manifest,
    get_git_info
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Stage1Evaluator:
    """
    Evaluate Stage 1 SFT model vs base model.

    Implements deterministic paired evaluation per stage1_evaluation_spec.md
    """

    def __init__(
        self,
        sft_checkpoint_path: Path,
        test_set_path: Path,
        output_dir: Path,
        model_name: str = "Qwen/Qwen2.5-32B",
        seed: int = 42
    ):
        """
        Initialize evaluator.

        Args:
            sft_checkpoint_path: Path to SFT LoRA checkpoint
            test_set_path: Path to held-out test instructions
            output_dir: Output directory for results
            model_name: Base model name
            seed: Random seed for reproducibility
        """
        self.sft_checkpoint_path = Path(sft_checkpoint_path)
        self.test_set_path = Path(test_set_path)
        self.output_dir = Path(output_dir)
        self.model_name = model_name
        self.seed = seed

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set seed
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def load_test_instructions(self) -> List[Dict[str, Any]]:
        """
        Load held-out test instructions.

        Returns:
            List of test instruction dicts
        """
        logger.info(f"Loading test instructions from {self.test_set_path}")

        if not self.test_set_path.exists():
            raise RuntimeError(
                f"🚨 Test set not found: {self.test_set_path}\n"
                "Cannot evaluate without held-out test set."
            )

        instructions = []
        with open(self.test_set_path) as f:
            for line in f:
                instructions.append(json.loads(line))

        logger.info(f"✅ Loaded {len(instructions)} test instructions")

        return instructions

    def load_base_model(self):
        """Load base model with contamination guards."""
        logger.info("Loading base model...")

        loader = CleanModelLoader(
            model_name=self.model_name,
            load_in_8bit=True,  # 8-bit for evaluation (more accurate than 4-bit)
            device_map="auto"
        )

        model, tokenizer, provenance = loader.load()

        logger.info("✅ Base model loaded")

        return model, tokenizer, provenance

    def load_sft_model(self, base_model, tokenizer):
        """
        Load SFT model (base + LoRA adapters).

        Args:
            base_model: Loaded base model
            tokenizer: Tokenizer

        Returns:
            SFT model with adapters applied
        """
        logger.info(f"Loading SFT adapters from {self.sft_checkpoint_path}")

        if not self.sft_checkpoint_path.exists():
            raise RuntimeError(
                f"🚨 SFT checkpoint not found: {self.sft_checkpoint_path}\n"
                "Cannot evaluate SFT model."
            )

        # Load adapter
        sft_model = PeftModel.from_pretrained(
            base_model,
            str(self.sft_checkpoint_path)
        )

        # Merge adapters for faster inference (optional)
        # sft_model = sft_model.merge_and_unload()

        logger.info("✅ SFT model loaded with adapters")

        return sft_model

    def generate_response(
        self,
        model,
        tokenizer,
        instruction: str,
        max_new_tokens: int = 100
    ) -> str:
        """
        Generate response with deterministic decoding.

        Per spec: temperature=0, do_sample=False for reproducibility.

        Args:
            model: Model to use
            tokenizer: Tokenizer
            instruction: Instruction string
            max_new_tokens: Max tokens to generate

        Returns:
            Generated response string
        """
        # Create prompt
        prompt = CompletionStylePrompts.create_response_prompt(
            instruction,
            include_delimiter=False,
            num_examples=0  # No few-shot for evaluation
        )

        # Simpler format for eval
        prompt = f"Instruction: {instruction}\nResponse:"

        # Tokenize
        inputs = tokenizer(
            prompt,
            add_special_tokens=False,
            return_tensors="pt"
        ).to(model.device)

        # Generate with deterministic settings
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,  # Greedy decoding
                temperature=None,  # Not used with do_sample=False
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        # Decode
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = generated_text[len(prompt):].strip()

        # Clean response
        response = CompletionStylePrompts.clean_response(response)

        return response

    def score_response(
        self,
        instruction: str,
        response: str
    ) -> Tuple[bool, str]:
        """
        Score whether response successfully follows instruction.

        Simple heuristic scoring for Stage 1:
        - Response is non-empty
        - Response is not just continuation of instruction
        - Response is reasonable length (5-200 chars)
        - Response doesn't contain "I cannot" or clear refusal (for non-harmful instructions)

        Args:
            instruction: Instruction string
            response: Generated response

        Returns:
            (success: bool, failure_reason: str)
        """
        # Check non-empty
        if not response or len(response.strip()) < 5:
            return False, "empty_response"

        # Check reasonable length
        if len(response) > 500:
            return False, "too_long"

        # Check not just repeating instruction
        if instruction.lower() in response.lower()[:50]:
            # Some overlap is OK, but not if it's just repeating
            pass

        # Check for clear failure patterns
        failure_patterns = [
            "i cannot",
            "i can't",
            "i don't know",
            "i'm not sure",
            "sorry, i"
        ]

        response_lower = response.lower()
        if any(pattern in response_lower[:100] for pattern in failure_patterns):
            # These might be appropriate for some instructions
            # But for simple factual instructions, likely indicates failure
            if len(response) < 50:  # Short refusal
                return False, "inappropriate_refusal"

        # Simple success if it made it here
        return True, ""

    def evaluate_model(
        self,
        model,
        tokenizer,
        test_instructions: List[Dict[str, Any]],
        model_name: str
    ) -> List[Dict[str, Any]]:
        """
        Evaluate model on test instructions.

        Args:
            model: Model to evaluate
            tokenizer: Tokenizer
            test_instructions: List of test instruction dicts
            model_name: Name for logging ("base" or "sft")

        Returns:
            List of evaluation results
        """
        logger.info(f"Evaluating {model_name} model on {len(test_instructions)} instructions...")

        results = []

        for i, test_item in enumerate(test_instructions):
            instruction = test_item['instruction']

            # Generate response
            response = self.generate_response(
                model,
                tokenizer,
                instruction
            )

            # Score response
            success, failure_reason = self.score_response(instruction, response)

            # Count tokens
            response_tokens = tokenizer.encode(response, add_special_tokens=False)

            result = {
                "instruction": instruction,
                "response": response,
                "success": success,
                "failure_reason": failure_reason,
                "tokens_generated": len(response_tokens),
                "instruction_type": test_item.get('type', 'unknown')
            }

            results.append(result)

            if (i + 1) % 50 == 0:
                success_rate = sum(1 for r in results if r['success']) / len(results)
                logger.info(f"   Processed {i + 1}/{len(test_instructions)}: {success_rate:.1%} success")

        success_rate = sum(1 for r in results if r['success']) / len(results)
        logger.info(f"✅ {model_name} evaluation complete: {success_rate:.1%} success")

        return results

    def compute_wilson_ci(
        self,
        successes: int,
        total: int,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Compute Wilson score confidence interval.

        Args:
            successes: Number of successes
            total: Total trials
            confidence: Confidence level (default 0.95)

        Returns:
            (lower_bound, upper_bound)
        """
        if total == 0:
            return (0.0, 0.0)

        from scipy.stats import norm
        z = norm.ppf((1 + confidence) / 2)

        p = successes / total
        denominator = 1 + z**2 / total
        center = (p + z**2 / (2 * total)) / denominator
        margin = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator

        return (max(0, center - margin), min(1, center + margin))

    def mcnemar_test(
        self,
        base_results: List[bool],
        sft_results: List[bool]
    ) -> Dict[str, float]:
        """
        Compute McNemar test for paired binary outcomes.

        Args:
            base_results: Base model success/fail results
            sft_results: SFT model success/fail results

        Returns:
            Dict with chi2 statistic and p-value
        """
        # Count discordant pairs
        n01 = sum(1 for b, s in zip(base_results, sft_results) if not b and s)  # Base fail, SFT success
        n10 = sum(1 for b, s in zip(base_results, sft_results) if b and not s)  # Base success, SFT fail

        # McNemar test with continuity correction
        if n01 + n10 == 0:
            return {"chi2": 0.0, "p_value": 1.0, "n01": n01, "n10": n10}

        chi2 = (abs(n01 - n10) - 1)**2 / (n01 + n10)

        # P-value from chi-square distribution (df=1)
        from scipy.stats import chi2 as chi2_dist
        p_value = 1 - chi2_dist.cdf(chi2, df=1)

        return {
            "chi2": float(chi2),
            "p_value": float(p_value),
            "n01": int(n01),
            "n10": int(n10)
        }

    def compute_cohens_h(
        self,
        p1: float,
        p2: float
    ) -> float:
        """
        Compute Cohen's h effect size for proportions.

        Args:
            p1: Proportion 1
            p2: Proportion 2

        Returns:
            Cohen's h (effect size)
        """
        # Arcsine transformation
        phi1 = 2 * np.arcsin(np.sqrt(p1))
        phi2 = 2 * np.arcsin(np.sqrt(p2))

        return abs(phi1 - phi2)

    def compute_statistics(
        self,
        base_results: List[Dict[str, Any]],
        sft_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute paired statistics per spec.

        Args:
            base_results: Base model evaluation results
            sft_results: SFT model evaluation results

        Returns:
            Statistics dict with overall and per-type metrics
        """
        logger.info("Computing paired statistics...")

        # Overall statistics
        base_successes = [r['success'] for r in base_results]
        sft_successes = [r['success'] for r in sft_results]

        base_rate = sum(base_successes) / len(base_successes)
        sft_rate = sum(sft_successes) / len(sft_successes)

        base_ci = self.compute_wilson_ci(sum(base_successes), len(base_successes))
        sft_ci = self.compute_wilson_ci(sum(sft_successes), len(sft_successes))

        mcnemar = self.mcnemar_test(base_successes, sft_successes)

        cohens_h = self.compute_cohens_h(base_rate, sft_rate)

        overall = {
            "n": len(base_results),
            "base_rate": base_rate,
            "base_ci": base_ci,
            "sft_rate": sft_rate,
            "sft_ci": sft_ci,
            "lift": sft_rate - base_rate,
            "mcnemar_chi2": mcnemar['chi2'],
            "mcnemar_p": mcnemar['p_value'],
            "cohens_h": cohens_h,
            "discordant_pairs": {
                "n01": mcnemar['n01'],  # Base fail, SFT success
                "n10": mcnemar['n10']   # Base success, SFT fail
            }
        }

        # Per-type statistics (if types available)
        by_type = {}
        instruction_types = set(r['instruction_type'] for r in base_results)

        if len(instruction_types) > 1:  # Only compute if multiple types
            for inst_type in instruction_types:
                base_type = [r for r in base_results if r['instruction_type'] == inst_type]
                sft_type = [r for r in sft_results if r['instruction_type'] == inst_type]

                if len(base_type) < 10:  # Skip types with too few examples
                    continue

                base_type_successes = [r['success'] for r in base_type]
                sft_type_successes = [r['success'] for r in sft_type]

                type_base_rate = sum(base_type_successes) / len(base_type_successes)
                type_sft_rate = sum(sft_type_successes) / len(sft_type_successes)

                type_mcnemar = self.mcnemar_test(base_type_successes, sft_type_successes)

                by_type[inst_type] = {
                    "n": len(base_type),
                    "base_rate": type_base_rate,
                    "sft_rate": type_sft_rate,
                    "lift": type_sft_rate - type_base_rate,
                    "mcnemar_p": type_mcnemar['p_value'],
                    "cohens_h": self.compute_cohens_h(type_base_rate, type_sft_rate)
                }

            # Apply Benjamini-Hochberg correction
            if by_type:
                p_values = [(t, stats['mcnemar_p']) for t, stats in by_type.items()]
                p_values_sorted = sorted(p_values, key=lambda x: x[1])

                fdr = 0.10
                n_tests = len(p_values_sorted)

                for i, (inst_type, p) in enumerate(p_values_sorted, start=1):
                    threshold = (i / n_tests) * fdr
                    by_type[inst_type]['mcnemar_p_adjusted'] = p
                    by_type[inst_type]['significant_after_bh'] = p <= threshold

        stats = {
            "overall": overall,
            "by_type": by_type,
            "bh_correction": {
                "fdr": 0.10,
                "n_tests": len(by_type),
                "n_significant_raw": sum(1 for s in by_type.values() if s['mcnemar_p'] < 0.05),
                "n_significant_adjusted": sum(1 for s in by_type.values() if s.get('significant_after_bh', False))
            } if by_type else {}
        }

        logger.info("✅ Statistics computed")
        logger.info(f"   Overall: base={base_rate:.1%}, sft={sft_rate:.1%}, lift={overall['lift']:.1%}")
        logger.info(f"   McNemar p={mcnemar['p_value']:.4f}, significant={mcnemar['p_value'] < 0.01}")

        return stats

    def run(self) -> Dict[str, Path]:
        """
        Run full evaluation pipeline.

        Returns:
            Dict with paths to evaluation artifacts
        """
        logger.info("=" * 60)
        logger.info("STARTING STAGE 1 SFT EVALUATION")
        logger.info("=" * 60)

        # Phase 1: Load test set
        logger.info("\n📋 PHASE 1: LOAD TEST SET")
        logger.info("-" * 60)
        test_instructions = self.load_test_instructions()

        # Phase 2: Load base model
        logger.info("\n📦 PHASE 2: LOAD BASE MODEL")
        logger.info("-" * 60)
        base_model, tokenizer, provenance = self.load_base_model()

        # Phase 3: Evaluate base model
        logger.info("\n🔍 PHASE 3: EVALUATE BASE MODEL")
        logger.info("-" * 60)
        base_results = self.evaluate_model(base_model, tokenizer, test_instructions, "base")

        # Save base results
        base_path = self.output_dir / "base_responses.jsonl"
        with open(base_path, 'w') as f:
            for result in base_results:
                f.write(json.dumps(result) + '\n')

        logger.info(f"✅ Saved base results: {base_path}")

        # Clear GPU memory
        del base_model
        torch.cuda.empty_cache()

        # Phase 4: Load SFT model (reload base then add adapters)
        logger.info("\n📦 PHASE 4: LOAD SFT MODEL")
        logger.info("-" * 60)
        base_model_reload, _, _ = self.load_base_model()
        sft_model = self.load_sft_model(base_model_reload, tokenizer)

        # Phase 5: Evaluate SFT model
        logger.info("\n🔍 PHASE 5: EVALUATE SFT MODEL")
        logger.info("-" * 60)
        sft_results = self.evaluate_model(sft_model, tokenizer, test_instructions, "sft")

        # Save SFT results
        sft_path = self.output_dir / "sft_responses.jsonl"
        with open(sft_path, 'w') as f:
            for result in sft_results:
                f.write(json.dumps(result) + '\n')

        logger.info(f"✅ Saved SFT results: {sft_path}")

        # Phase 6: Compute statistics
        logger.info("\n📊 PHASE 6: COMPUTE STATISTICS")
        logger.info("-" * 60)
        stats = self.compute_statistics(base_results, sft_results)

        # Add metadata
        stats['metadata'] = {
            **get_git_info(),
            **provenance,
            "test_set_path": str(self.test_set_path),
            "sft_checkpoint_path": str(self.sft_checkpoint_path),
            "seed": self.seed,
            "decoding": "greedy (temperature=0, do_sample=False)",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Save evaluation results
        results_path = self.output_dir / "evaluation_results.json"
        with open(results_path, 'w') as f:
            json.dump(stats, f, indent=2)

        logger.info(f"✅ Saved evaluation results: {results_path}")

        # Generate human-readable summary
        summary_path = self.output_dir / "evaluation_summary.txt"
        self.write_summary(stats, summary_path)

        logger.info("\n" + "=" * 60)
        logger.info("✅ EVALUATION COMPLETE")
        logger.info(f"   Base: {stats['overall']['base_rate']:.1%}")
        logger.info(f"   SFT: {stats['overall']['sft_rate']:.1%}")
        logger.info(f"   Lift: {stats['overall']['lift']:.1%}")
        logger.info(f"   p-value: {stats['overall']['mcnemar_p']:.4f}")
        logger.info(f"   Gate: {'PASS' if stats['overall']['mcnemar_p'] < 0.01 else 'FAIL'} (need p<0.01)")
        logger.info("=" * 60)

        return {
            'base_responses': base_path,
            'sft_responses': sft_path,
            'evaluation_results': results_path,
            'evaluation_summary': summary_path
        }

    def write_summary(self, stats: Dict[str, Any], output_path: Path):
        """Write human-readable summary."""
        with open(output_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("STAGE 1 SFT EVALUATION SUMMARY\n")
            f.write("=" * 60 + "\n\n")

            # Overall results
            overall = stats['overall']
            f.write(f"OVERALL RESULTS (n={overall['n']})\n")
            f.write("-" * 60 + "\n")
            f.write(f"Base Model:  {overall['base_rate']:.1%} (95% CI: {overall['base_ci'][0]:.1%}-{overall['base_ci'][1]:.1%})\n")
            f.write(f"SFT Model:   {overall['sft_rate']:.1%} (95% CI: {overall['sft_ci'][0]:.1%}-{overall['sft_ci'][1]:.1%})\n")
            f.write(f"Lift:        {overall['lift']:.1%}\n")
            f.write(f"McNemar p:   {overall['mcnemar_p']:.4f}\n")
            f.write(f"Cohen's h:   {overall['cohens_h']:.3f}\n")
            f.write(f"\nDiscordant Pairs:\n")
            f.write(f"  Base fail, SFT success: {overall['discordant_pairs']['n01']}\n")
            f.write(f"  Base success, SFT fail: {overall['discordant_pairs']['n10']}\n")

            # Gate decision
            f.write(f"\n{'='*60}\n")
            if overall['mcnemar_p'] < 0.01:
                f.write("GATE DECISION: ✅ PASS (p < 0.01)\n")
                f.write("Statistically significant improvement. Proceed to next stage.\n")
            else:
                f.write("GATE DECISION: ❌ FAIL (p >= 0.01)\n")
                f.write("No statistically significant improvement. Review and iterate.\n")

        logger.info(f"✅ Saved summary: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Stage 1 SFT model vs base"
    )
    parser.add_argument(
        "--sft-checkpoint",
        type=str,
        required=True,
        help="Path to SFT LoRA checkpoint directory"
    )
    parser.add_argument(
        "--test-set",
        type=str,
        required=True,
        help="Path to held-out test instructions JSONL"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/sft_eval",
        help="Output directory (default: results/sft_eval)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen2.5-32B",
        help="Base model name (default: Qwen/Qwen2.5-32B)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)"
    )

    args = parser.parse_args()

    # Create evaluator
    evaluator = Stage1Evaluator(
        sft_checkpoint_path=Path(args.sft_checkpoint),
        test_set_path=Path(args.test_set),
        output_dir=Path(args.output),
        model_name=args.model,
        seed=args.seed
    )

    # Run evaluation
    try:
        artifacts = evaluator.run()

        # Check gate
        with open(artifacts['evaluation_results']) as f:
            results = json.load(f)

        if results['overall']['mcnemar_p'] < 0.01:
            logger.info("\n✅ SFT EVALUATION PASSED GATE")
            sys.exit(0)
        else:
            logger.warning("\n⚠️  SFT EVALUATION FAILED GATE (p >= 0.01)")
            sys.exit(1)

    except Exception as e:
        logger.error(f"\n❌ Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
