#!/usr/bin/env python3
"""
Stage 1 Data Generation Pilot Script

Generates instruction-following SFT data using base model completion + logprob filtering.

Workflow:
1. Load base model with CleanModelLoader (contamination guards)
2. Generate instructions via completion-style prompts
3. Filter instructions via instruction critic (logprob A/B)
4. Generate responses for good instructions
5. Filter pairs via pair critic (logprob A/B)
6. Compute QC metrics against thresholds
7. Save pilot data + QC summary + session manifest

Gate: QC thresholds must pass to proceed to scale.

Usage:
    python generate_stage1_pilot_data.py --count 100 --output artifacts/pilot/

Outputs:
    - pilot_data.jsonl (SFT examples with full provenance)
    - qc_summary.json (QC metrics and threshold checks)
    - session_manifest.json (environment and provenance)
"""

import argparse
import json
import logging
import random
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import torch
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    CleanModelLoader,
    CompletionStylePrompts,
    InstructionCritic,
    create_artifact_metadata,
    create_session_manifest,
    create_qc_summary,
    update_session_manifest
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Stage1PilotGenerator:
    """
    Generate Stage 1 pilot data with QC.

    Implements full pipeline per stage1_data_generation_spec.md
    """

    # QC Thresholds from spec
    QC_THRESHOLDS = {
        "runaway_rate_max": 0.05,  # <5% runaway after cleaning
        "token_limit_hits_max": 0.10,  # <10% hit token limit
        "delimiter_leakage": 0,  # 0 occurrences of delimiter in final
        "median_tokens_max": 40,  # <40 median tokens
        "critic_acceptance_min": 0.50  # ≥50% acceptance
    }

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-32B",
        output_dir: Path = Path("artifacts/pilot"),
        seed: int = 42,
        load_in_4bit: bool = True
    ):
        """
        Initialize pilot generator.

        Args:
            model_name: Model name or local path
            output_dir: Output directory for artifacts
            seed: Random seed for reproducibility
            load_in_4bit: Use 4-bit quantization
        """
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.seed = seed
        self.load_in_4bit = load_in_4bit

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set seeds
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

        # Will be initialized during run
        self.model = None
        self.tokenizer = None
        self.loader_provenance = None
        self.critic = None
        self.session_manifest = None

    def initialize(self):
        """Load model and initialize components."""
        logger.info("Initializing Stage 1 Pilot Generator")
        logger.info("=" * 60)

        # Load model with contamination guards
        logger.info(f"Loading model: {self.model_name}")
        loader = CleanModelLoader(
            model_name=self.model_name,
            load_in_4bit=self.load_in_4bit
        )
        self.model, self.tokenizer, self.loader_provenance = loader.load()

        # Initialize critic
        logger.info("Initializing instruction critic")
        self.critic = InstructionCritic(self.model, self.tokenizer)

        # Create session manifest
        session_id = f"stage1_pilot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.session_manifest = create_session_manifest(
            session_id=session_id,
            planned_artifacts=[
                "pilot_data.jsonl",
                "qc_summary.json",
                "session_manifest.json"
            ],
            notes="Stage 1 data generation pilot per stage1_data_generation_spec.md"
        )

        logger.info("✅ Initialization complete")
        logger.info("=" * 60)

    def generate_instructions(
        self,
        count: int,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
        max_new_tokens: int = 200
    ) -> List[str]:
        """
        Generate instructions via completion-style prompts.

        Args:
            count: Target number of instructions (will generate ~1.5-2x for filtering)
            temperature: Sampling temperature
            max_new_tokens: Max tokens per generation

        Returns:
            List of generated instruction strings
        """
        logger.info(f"Generating ~{int(count * 1.5)} instructions (target {count} after filtering)")

        # Generate more than needed to allow filtering
        num_generations = max(10, int(count * 1.5 / 10))  # Generate in batches of ~10

        all_instructions = []

        for i in range(num_generations):
            # Create instruction generation prompt
            prompt = CompletionStylePrompts.create_instruction_generation_prompt(
                num_examples=10,
                start_number=1
            )

            # Tokenize
            inputs = self.tokenizer(
                prompt,
                add_special_tokens=False,
                return_tensors="pt"
            ).to(self.model.device)

            # Define stop sequences (prevent runaway list generation)
            stop_sequences = ["\nInstruction", "\nQ:", "\n###", "\nUser:"]
            stop_token_ids = [
                self.tokenizer.encode(seq, add_special_tokens=False)[-1]
                for seq in stop_sequences
            ]

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    repetition_penalty=repetition_penalty,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=stop_token_ids + [self.tokenizer.eos_token_id]  # Stop on any of these
                )

            # Decode
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            completion = generated_text[len(prompt):]

            # Parse instructions
            instructions = CompletionStylePrompts.parse_generated_instructions(
                completion,
                max_instructions=20
            )

            all_instructions.extend(instructions)

            if len(all_instructions) >= count * 1.5:
                break

            if (i + 1) % 5 == 0:
                logger.info(f"  Generated {len(all_instructions)} instructions so far...")

        logger.info(f"✅ Generated {len(all_instructions)} raw instructions")
        return all_instructions

    def filter_instructions(
        self,
        instructions: List[str],
        confidence_threshold: float = 1.0
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Filter instructions via instruction critic.

        Args:
            instructions: List of instruction strings
            confidence_threshold: Minimum logprob margin

        Returns:
            (filtered_instructions, critique_results)
        """
        logger.info(f"Filtering {len(instructions)} instructions via critic...")

        good_instructions = []
        all_critiques = []

        for i, instruction in enumerate(instructions):
            critique = self.critic.critique_instruction(
                instruction,
                confidence_threshold=confidence_threshold
            )

            all_critiques.append({
                "instruction": instruction,
                "critique": critique.to_dict()
            })

            if critique.is_good and critique.confident:
                good_instructions.append(instruction)

            if (i + 1) % 100 == 0:
                logger.info(f"  Processed {i + 1}/{len(instructions)} instructions...")

        acceptance_rate = len(good_instructions) / len(instructions) if instructions else 0
        logger.info(f"✅ Filtered to {len(good_instructions)} good instructions (acceptance: {acceptance_rate:.1%})")

        return good_instructions, all_critiques

    def generate_responses(
        self,
        instructions: List[str],
        temperature: float = 0.4,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
        max_new_tokens: int = 80
    ) -> List[Dict[str, Any]]:
        """
        Generate responses for instructions.

        Args:
            instructions: List of instruction strings
            temperature: Sampling temperature
            max_new_tokens: Max tokens per response

        Returns:
            List of dicts with instruction, response, raw_response, tokens
        """
        logger.info(f"Generating responses for {len(instructions)} instructions...")

        results = []

        for i, instruction in enumerate(instructions):
            # Create response generation prompt
            prompt = CompletionStylePrompts.create_response_prompt(
                instruction,
                include_delimiter=True,
                num_examples=3
            )

            # Tokenize
            inputs = self.tokenizer(
                prompt,
                add_special_tokens=False,
                return_tensors="pt"
            ).to(self.model.device)

            # Define stop sequences for responses
            stop_sequences = ["\nInstruction", "\nQ:", "\n###", "\nUser:", "\nResponse:"]
            stop_token_ids = [
                self.tokenizer.encode(seq, add_special_tokens=False)[-1]
                for seq in stop_sequences
            ]

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    repetition_penalty=repetition_penalty,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=stop_token_ids + [self.tokenizer.eos_token_id]  # Stop on any of these
                )

            # Decode
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            raw_response = generated_text[len(prompt):].strip()

            # Clean response using delimiter and heuristics
            cleaned_response = CompletionStylePrompts.clean_response(raw_response)

            # Count tokens
            response_tokens = self.tokenizer.encode(cleaned_response, add_special_tokens=False)
            num_tokens = len(response_tokens)

            results.append({
                "instruction": instruction,
                "response": cleaned_response,
                "raw_response": raw_response,
                "tokens": num_tokens,
                "hit_token_limit": len(outputs[0]) - len(inputs['input_ids'][0]) >= max_new_tokens - 5
            })

            if (i + 1) % 50 == 0:
                logger.info(f"  Generated {i + 1}/{len(instructions)} responses...")

        logger.info(f"✅ Generated {len(results)} responses")
        return results

    def filter_pairs(
        self,
        pairs: List[Dict[str, Any]],
        confidence_threshold: float = 1.0
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter instruction-response pairs via pair critic.

        Args:
            pairs: List of dicts with instruction and response
            confidence_threshold: Minimum logprob margin

        Returns:
            (filtered_pairs, critique_results)
        """
        logger.info(f"Filtering {len(pairs)} pairs via pair critic...")

        good_pairs = []
        all_critiques = []

        for i, pair in enumerate(pairs):
            critique = self.critic.critique_pair(
                pair["instruction"],
                pair["response"],
                confidence_threshold=confidence_threshold
            )

            critique_dict = {
                "instruction": pair["instruction"],
                "response": pair["response"],
                "critique": critique.to_dict()
            }

            all_critiques.append(critique_dict)

            if critique.is_good and critique.confident:
                good_pairs.append({
                    **pair,
                    "pair_critique": critique.to_dict()
                })

            if (i + 1) % 50 == 0:
                logger.info(f"  Processed {i + 1}/{len(pairs)} pairs...")

        acceptance_rate = len(good_pairs) / len(pairs) if pairs else 0
        logger.info(f"✅ Filtered to {len(good_pairs)} good pairs (acceptance: {acceptance_rate:.1%})")

        return good_pairs, all_critiques

    def compute_qc_metrics(
        self,
        generated_instructions: List[str],
        instruction_critiques: List[Dict[str, Any]],
        generated_pairs: List[Dict[str, Any]],
        pair_critiques: List[Dict[str, Any]],
        final_pairs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute QC metrics and check against thresholds.

        Args:
            generated_instructions: All generated instructions
            instruction_critiques: Instruction critique results
            generated_pairs: All generated pairs (before pair filtering)
            pair_critiques: Pair critique results
            final_pairs: Final filtered pairs

        Returns:
            QC summary dict with metrics and threshold checks
        """
        logger.info("Computing QC metrics...")

        # Counts
        counts = {
            "instructions_generated": len(generated_instructions),
            "instructions_kept": sum(1 for c in instruction_critiques if c['critique']['is_good'] and c['critique']['confident']),
            "pairs_generated": len(generated_pairs),
            "pairs_kept": len(final_pairs),
            "delimiter_found": sum(1 for p in generated_pairs if "###END###" in p.get('raw_response', '')),
            "hit_token_limit": sum(1 for p in generated_pairs if p.get('hit_token_limit', False))
        }

        # Acceptance rates
        acceptance = {
            "instructions_good": sum(1 for c in instruction_critiques if c['critique']['is_good']),
            "instructions_bad": sum(1 for c in instruction_critiques if not c['critique']['is_good']),
            "instructions_low_confidence": sum(1 for c in instruction_critiques if not c['critique']['confident']),
            "pairs_good": sum(1 for c in pair_critiques if c['critique']['is_good']),
            "pairs_bad": sum(1 for c in pair_critiques if not c['critique']['is_good']),
            "pairs_low_confidence": sum(1 for c in pair_critiques if not c['critique']['confident'])
        }

        # Token statistics
        tokens = [p['tokens'] for p in final_pairs if 'tokens' in p]
        token_stats = {
            "median": float(np.median(tokens)) if tokens else 0,
            "mean": float(np.mean(tokens)) if tokens else 0,
            "p95": float(np.percentile(tokens, 95)) if tokens else 0,
            "min": int(np.min(tokens)) if tokens else 0,
            "max": int(np.max(tokens)) if tokens else 0
        }

        # Margin statistics
        inst_margins = [c['critique']['margin'] for c in instruction_critiques]
        pair_margins = [c['critique']['margin'] for c in pair_critiques]

        margins = {
            "instruction": {
                "mean": float(np.mean(inst_margins)) if inst_margins else 0,
                "median": float(np.median(inst_margins)) if inst_margins else 0,
                "p25": float(np.percentile(inst_margins, 25)) if inst_margins else 0,
                "p75": float(np.percentile(inst_margins, 75)) if inst_margins else 0
            },
            "pair": {
                "mean": float(np.mean(pair_margins)) if pair_margins else 0,
                "median": float(np.median(pair_margins)) if pair_margins else 0,
                "p25": float(np.percentile(pair_margins, 25)) if pair_margins else 0,
                "p75": float(np.percentile(pair_margins, 75)) if pair_margins else 0
            }
        }

        # Check thresholds
        failed_reasons = []
        thresholds_passed = True

        # Runaway rate (detect actual runaways: multiple Q/A pairs, not just long responses)
        # A response is a "runaway" if it contains patterns indicating it started generating new prompts
        runaway_patterns = [
            '\n\nInstruction:',
            '\n\nQuestion:',
            '\n\nQ:',
            '\nUser:',
            '\nAssistant:',
            '\nHuman:'
        ]

        runaway_count = sum(
            1 for p in final_pairs
            if any(pattern in p['response'] for pattern in runaway_patterns)
            or len(p['response']) > 500  # Extremely long responses (not typical instruction-following)
        )
        runaway_rate = runaway_count / len(final_pairs) if final_pairs else 0
        if runaway_rate >= self.QC_THRESHOLDS['runaway_rate_max']:
            failed_reasons.append(f"Runaway rate {runaway_rate:.1%} >= {self.QC_THRESHOLDS['runaway_rate_max']:.1%}")
            thresholds_passed = False

        # Token limit hits
        token_limit_rate = counts['hit_token_limit'] / counts['pairs_generated'] if counts['pairs_generated'] else 0
        if token_limit_rate >= self.QC_THRESHOLDS['token_limit_hits_max']:
            failed_reasons.append(f"Token limit rate {token_limit_rate:.1%} >= {self.QC_THRESHOLDS['token_limit_hits_max']:.1%}")
            thresholds_passed = False

        # Delimiter leakage
        delimiter_in_final = sum(1 for p in final_pairs if "###END###" in p['response'] or "###" in p['response'])
        if delimiter_in_final > self.QC_THRESHOLDS['delimiter_leakage']:
            failed_reasons.append(f"Delimiter leakage: {delimiter_in_final} occurrences in final responses")
            thresholds_passed = False

        # QC metrics for truncation/completeness (should be 0 after Phase 3b filtering)
        truncated_responses = sum(
            1 for p in final_pairs
            if p['response'].strip().endswith(':')
        )
        truncation_rate = truncated_responses / len(final_pairs) if final_pairs else 0
        if truncation_rate > 0:
            failed_reasons.append(f"Truncation found after filtering: {truncated_responses} examples")
            thresholds_passed = False

        # Median tokens
        if token_stats['median'] >= self.QC_THRESHOLDS['median_tokens_max']:
            failed_reasons.append(f"Median tokens {token_stats['median']:.1f} >= {self.QC_THRESHOLDS['median_tokens_max']}")
            thresholds_passed = False

        # Critic acceptance rates
        inst_acceptance = acceptance['instructions_good'] / len(instruction_critiques) if instruction_critiques else 0
        pair_acceptance = acceptance['pairs_good'] / len(pair_critiques) if pair_critiques else 0

        if inst_acceptance < self.QC_THRESHOLDS['critic_acceptance_min']:
            failed_reasons.append(f"Instruction acceptance {inst_acceptance:.1%} < {self.QC_THRESHOLDS['critic_acceptance_min']:.1%}")
            thresholds_passed = False

        if pair_acceptance < self.QC_THRESHOLDS['critic_acceptance_min']:
            failed_reasons.append(f"Pair acceptance {pair_acceptance:.1%} < {self.QC_THRESHOLDS['critic_acceptance_min']:.1%}")
            thresholds_passed = False

        # Create QC summary
        qc_summary = create_qc_summary(
            counts=counts,
            acceptance=acceptance,
            token_stats=token_stats,
            margins=margins,
            thresholds=self.QC_THRESHOLDS,
            thresholds_passed=thresholds_passed,
            failed_reasons=failed_reasons
        )

        # Add rates for easier interpretation
        qc_summary['rates'] = {
            "instruction_acceptance": inst_acceptance,
            "pair_acceptance": pair_acceptance,
            "runaway_rate": runaway_rate,
            "token_limit_rate": token_limit_rate,
            "delimiter_leakage_count": delimiter_in_final,
            "truncation_rate": truncation_rate,
            "truncated_count": truncated_responses
        }

        logger.info(f"✅ QC metrics computed")
        logger.info(f"   Thresholds passed: {thresholds_passed}")

        if not thresholds_passed:
            logger.warning("⚠️  QC THRESHOLDS FAILED:")
            for reason in failed_reasons:
                logger.warning(f"   - {reason}")

        return qc_summary

    def run(
        self,
        count: int = 100,
        instruction_temperature: float = 0.7,
        instruction_top_p: float = 0.9,
        instruction_repetition_penalty: float = 1.1,
        response_temperature: float = 0.4,
        response_top_p: float = 0.9,
        response_repetition_penalty: float = 1.1,
        response_max_tokens: int = 200,  # Increased from 80 to prevent truncation
        confidence_threshold: float = 1.0
    ) -> Dict[str, Path]:
        """
        Run full pilot generation pipeline.

        Args:
            count: Target number of final examples
            instruction_temperature: Temperature for instruction generation
            response_temperature: Temperature for response generation
            confidence_threshold: Minimum logprob margin for critics

        Returns:
            Dict with paths to generated artifacts
        """
        logger.info("=" * 60)
        logger.info(f"STARTING STAGE 1 PILOT DATA GENERATION (target: {count} examples)")
        logger.info("=" * 60)

        # Initialize
        self.initialize()

        # Phase 1: Generate and filter instructions
        logger.info("\n📝 PHASE 1: INSTRUCTION GENERATION")
        logger.info("-" * 60)
        instructions = self.generate_instructions(
            count=count,
            temperature=instruction_temperature,
            top_p=instruction_top_p,
            repetition_penalty=instruction_repetition_penalty
        )

        good_instructions, instruction_critiques = self.filter_instructions(
            instructions,
            confidence_threshold=confidence_threshold
        )

        # Take only what we need
        good_instructions = good_instructions[:count]

        # Phase 2: Generate responses
        logger.info("\n💬 PHASE 2: RESPONSE GENERATION")
        logger.info("-" * 60)
        pairs = self.generate_responses(
            good_instructions,
            temperature=response_temperature,
            top_p=response_top_p,
            repetition_penalty=response_repetition_penalty,
            max_new_tokens=response_max_tokens
        )

        # Phase 3: Filter pairs
        logger.info("\n✅ PHASE 3: PAIR FILTERING")
        logger.info("-" * 60)
        final_pairs, pair_critiques = self.filter_pairs(
            pairs,
            confidence_threshold=confidence_threshold
        )

        # Phase 3b: Filter out-of-scope tasks (per Codex scoping guidance)
        logger.info("\n🔍 PHASE 3b: SCOPE FILTERING")
        logger.info("-" * 60)

        def is_true_false_evaluation(instruction: str, response: str) -> bool:
            """Check if this is a True/False evaluation task (Stage 4, not Stage 1)."""
            resp = response.strip()
            inst_lower = instruction.lower()

            # Response is True/False
            if resp not in ['True', 'False', 'True.', 'False.']:
                return False

            # AND instruction lacks directive cues (it's a bare statement)
            directive_cues = ['true or false', 'is this', 'is it', 'determine whether', '?']
            has_directive = any(cue in inst_lower for cue in directive_cues)

            return not has_directive  # Out of scope if no directive

        def is_truncated(response: str) -> bool:
            """Check if response appears truncated."""
            resp = response.strip()
            # Ends with : (code intro without code)
            if resp.endswith(':'):
                return True
            # Very short without being a valid short answer
            if len(resp) < 10 and resp not in ['Yes', 'No', 'Yes.', 'No.', 'True', 'False', 'True.', 'False.']:
                return True
            return False

        # Filter pairs
        stage1_pairs = []
        stage4_examples = []
        truncated_examples = []

        for pair in final_pairs:
            if is_truncated(pair['response']):
                truncated_examples.append(pair)
            elif is_true_false_evaluation(pair['instruction'], pair['response']):
                stage4_examples.append(pair)
            else:
                stage1_pairs.append(pair)

        logger.info(f"Filtered {len(stage4_examples)} True/False evaluation tasks (saved for Stage 4)")
        logger.info(f"Filtered {len(truncated_examples)} truncated responses (quality issue)")
        logger.info(f"Kept {len(stage1_pairs)} Stage 1 instruction-following pairs")

        # Update final_pairs to only Stage 1 examples
        final_pairs = stage1_pairs

        # Phase 4: Compute QC
        logger.info("\n📊 PHASE 4: QC METRICS")
        logger.info("-" * 60)
        qc_summary = self.compute_qc_metrics(
            generated_instructions=instructions,
            instruction_critiques=instruction_critiques,
            generated_pairs=pairs,
            pair_critiques=pair_critiques,
            final_pairs=final_pairs
        )

        # Phase 5: Save artifacts
        logger.info("\n💾 PHASE 5: SAVING ARTIFACTS")
        logger.info("-" * 60)
        artifacts = self.save_artifacts(
            final_pairs,
            qc_summary,
            instruction_temperature=instruction_temperature,
            instruction_top_p=instruction_top_p,
            instruction_repetition_penalty=instruction_repetition_penalty,
            response_temperature=response_temperature,
            response_top_p=response_top_p,
            response_repetition_penalty=response_repetition_penalty,
            response_max_tokens=response_max_tokens,
            confidence_threshold=confidence_threshold
        )

        logger.info("\n" + "=" * 60)
        logger.info("✅ PILOT GENERATION COMPLETE")
        logger.info(f"   Generated: {len(final_pairs)} examples")
        logger.info(f"   QC Status: {'PASS' if qc_summary['thresholds_passed'] else 'FAIL'}")
        logger.info(f"   Artifacts: {self.output_dir}")
        logger.info("=" * 60)

        return artifacts

    def save_artifacts(
        self,
        final_pairs: List[Dict[str, Any]],
        qc_summary: Dict[str, Any],
        instruction_temperature: float = 0.7,
        instruction_top_p: float = 0.9,
        instruction_repetition_penalty: float = 1.1,
        response_temperature: float = 0.4,
        response_top_p: float = 0.9,
        response_repetition_penalty: float = 1.1,
        response_max_tokens: int = 80,
        confidence_threshold: float = 1.0
    ) -> Dict[str, Path]:
        """
        Save all artifacts with provenance.

        Args:
            final_pairs: Final filtered instruction-response pairs
            qc_summary: QC summary dict

        Returns:
            Dict mapping artifact names to paths
        """
        artifacts = {}

        # Save pilot data (JSONL with full provenance)
        data_path = self.output_dir / "pilot_data.jsonl"
        with open(data_path, 'w') as f:
            for pair in final_pairs:
                # Add full metadata per DATA_SCHEMAS_AND_PROVENANCE spec
                example = {
                    "instruction": pair["instruction"],
                    "response": pair["response"],
                    "prompt": CompletionStylePrompts.create_response_prompt(pair["instruction"]),
                    "completion": pair["response"],
                    "pair_critique": pair.get("pair_critique", {}),
                    "metadata": create_artifact_metadata(
                        artifact_type="sft_example",
                        script_name="generate_stage1_pilot_data.py",
                        model_name=self.model_name,
                        loader_provenance=self.loader_provenance,
                        generation_params={
                            "seed": self.seed,
                            "instruction_temperature": instruction_temperature,
                            "instruction_top_p": instruction_top_p,
                            "instruction_repetition_penalty": instruction_repetition_penalty,
                            "response_temperature": response_temperature,
                            "response_top_p": response_top_p,
                            "response_repetition_penalty": response_repetition_penalty,
                            "response_max_tokens": response_max_tokens,
                            "confidence_threshold": confidence_threshold
                        }
                    )
                }
                f.write(json.dumps(example) + '\n')

        logger.info(f"✅ Saved pilot data: {data_path}")
        artifacts['pilot_data'] = data_path

        # Update session manifest
        self.session_manifest = update_session_manifest(
            self.session_manifest,
            str(data_path),
            "sft_data",
            success=True
        )

        # Save QC summary
        qc_path = self.output_dir / "qc_summary.json"
        with open(qc_path, 'w') as f:
            json.dump(qc_summary, f, indent=2)

        logger.info(f"✅ Saved QC summary: {qc_path}")
        artifacts['qc_summary'] = qc_path

        self.session_manifest = update_session_manifest(
            self.session_manifest,
            str(qc_path),
            "qc_summary",
            success=True
        )

        # Save session manifest
        manifest_path = self.output_dir / "session_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(self.session_manifest, f, indent=2)

        logger.info(f"✅ Saved session manifest: {manifest_path}")
        artifacts['session_manifest'] = manifest_path

        return artifacts


def main():
    parser = argparse.ArgumentParser(
        description="Generate Stage 1 pilot data with QC"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Target number of examples (default: 100)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts/pilot",
        help="Output directory (default: artifacts/pilot)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen2.5-32B",
        help="Model name or path (default: Qwen/Qwen2.5-32B)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--load-in-8bit",
        action="store_true",
        help="Use 8-bit quantization instead of 4-bit"
    )

    # Generation parameters
    parser.add_argument(
        "--instruction-temperature",
        type=float,
        default=0.7,
        help="Temperature for instruction generation (default: 0.7)"
    )
    parser.add_argument(
        "--instruction-top-p",
        type=float,
        default=0.9,
        help="Top-p for instruction generation (default: 0.9)"
    )
    parser.add_argument(
        "--instruction-repetition-penalty",
        type=float,
        default=1.1,
        help="Repetition penalty for instruction generation (default: 1.1)"
    )
    parser.add_argument(
        "--response-temperature",
        type=float,
        default=0.4,
        help="Temperature for response generation (default: 0.4)"
    )
    parser.add_argument(
        "--response-top-p",
        type=float,
        default=0.9,
        help="Top-p for response generation (default: 0.9)"
    )
    parser.add_argument(
        "--response-repetition-penalty",
        type=float,
        default=1.1,
        help="Repetition penalty for response generation (default: 1.1)"
    )
    parser.add_argument(
        "--response-max-tokens",
        type=int,
        default=200,
        help="Max new tokens for response generation (default: 200, increased to prevent truncation)"
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=1.0,
        help="Minimum logprob margin for critic confidence (default: 1.0)"
    )

    args = parser.parse_args()

    # Create generator
    generator = Stage1PilotGenerator(
        model_name=args.model,
        output_dir=Path(args.output),
        seed=args.seed,
        load_in_4bit=not args.load_in_8bit
    )

    # Run pilot with all parameters
    artifacts = generator.run(
        count=args.count,
        instruction_temperature=args.instruction_temperature,
        instruction_top_p=args.instruction_top_p,
        instruction_repetition_penalty=args.instruction_repetition_penalty,
        response_temperature=args.response_temperature,
        response_top_p=args.response_top_p,
        response_repetition_penalty=args.response_repetition_penalty,
        response_max_tokens=args.response_max_tokens,
        confidence_threshold=args.confidence_threshold
    )

    # Exit with appropriate code
    qc_path = artifacts['qc_summary']
    with open(qc_path) as f:
        qc = json.load(f)

    if qc['thresholds_passed']:
        logger.info("\n✅ PILOT PASSED QC - Ready to scale")
        sys.exit(0)
    else:
        logger.warning("\n⚠️  PILOT FAILED QC - Review and iterate")
        sys.exit(1)


if __name__ == "__main__":
    main()
