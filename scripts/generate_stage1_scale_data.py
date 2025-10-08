#!/usr/bin/env python3
"""
Stage 1 Data Generation Scale Script (15k examples with sharding)

Generates full-scale instruction-following SFT data using validated parameters from pilot.

Workflow:
1. Verify pilot QC passed (gate requirement)
2. Load validated parameters from pilot manifest
3. Shard generation across multiple seeds for diversity
4. Generate shards in parallel or sequence
5. Merge shards and recompute QC on full dataset
6. Validate merged QC still passes thresholds

Gate: Pilot must have passed QC to proceed.

Usage:
    # After pilot passes QC
    python generate_stage1_scale_data.py \
      --pilot-manifest artifacts/pilot_iteration1/session_manifest.json \
      --count 15000 \
      --num-shards 10 \
      --output data/stage1_sft_data.jsonl

Outputs:
    - data/stage1_sft_data.jsonl (merged 15k examples)
    - artifacts/scale/qc_summary_merged.json (QC on full dataset)
    - artifacts/scale/scale_manifest.json (scale provenance)
    - artifacts/scale/shards/ (individual shard outputs)
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    create_session_manifest,
    create_qc_summary,
    update_session_manifest,
    get_git_info
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Stage1ScaleGenerator:
    """
    Generate Stage 1 scale data (15k examples) with sharding.

    Implements scale procedure per stage1_data_generation_spec.md
    """

    QC_THRESHOLDS = {
        "runaway_rate_max": 0.05,
        "token_limit_hits_max": 0.10,
        "delimiter_leakage": 0,
        "median_tokens_max": 40,
        "critic_acceptance_min": 0.50
    }

    def __init__(
        self,
        pilot_manifest_path: Path,
        output_path: Path,
        num_shards: int = 10,
        base_seed: int = 100
    ):
        """
        Initialize scale generator.

        Args:
            pilot_manifest_path: Path to successful pilot manifest
            output_path: Output path for merged data
            num_shards: Number of shards to generate
            base_seed: Base seed (each shard uses base_seed + shard_id)
        """
        self.pilot_manifest_path = Path(pilot_manifest_path)
        self.output_path = Path(output_path)
        self.num_shards = num_shards
        self.base_seed = base_seed

        # Create directories
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir = Path("artifacts/scale")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.shards_dir = self.artifacts_dir / "shards"
        self.shards_dir.mkdir(parents=True, exist_ok=True)

        # Will be loaded from pilot manifest
        self.pilot_params = None
        self.pilot_qc = None

    def verify_pilot_passed(self):
        """
        Verify that pilot QC passed.

        Gate requirement: Cannot scale without successful pilot.
        """
        logger.info("Verifying pilot QC passed...")

        # Load pilot manifest
        with open(self.pilot_manifest_path) as f:
            manifest = json.load(f)

        self.pilot_params = manifest

        # Find QC summary in artifacts
        qc_artifact = None
        for artifact in manifest.get('artifacts_generated', []):
            if artifact['type'] == 'qc_summary' and artifact['success']:
                qc_artifact = artifact
                break

        if not qc_artifact:
            raise RuntimeError(
                "🚨 GATE FAILURE: No QC summary found in pilot manifest!\n"
                f"Pilot manifest: {self.pilot_manifest_path}\n"
                "Cannot proceed to scale without pilot QC."
            )

        # Load QC summary
        qc_path = Path(qc_artifact['path'])
        if not qc_path.exists():
            # Try relative to manifest directory
            qc_path = self.pilot_manifest_path.parent / qc_path.name

        with open(qc_path) as f:
            self.pilot_qc = json.load(f)

        # Check if QC passed
        if not self.pilot_qc.get('thresholds_passed', False):
            failed_reasons = self.pilot_qc.get('failed_reasons', [])
            raise RuntimeError(
                "🚨 GATE FAILURE: Pilot QC did not pass thresholds!\n"
                f"Failed reasons:\n" +
                "\n".join(f"  - {r}" for r in failed_reasons) +
                "\n\nCannot proceed to scale. Must iterate on pilot first."
            )

        logger.info("✅ Pilot QC passed - proceeding to scale")
        logger.info(f"   Pilot acceptance rates: inst={self.pilot_qc['rates']['instruction_acceptance']:.1%}, pair={self.pilot_qc['rates']['pair_acceptance']:.1%}")

    def extract_pilot_parameters(self) -> Dict[str, Any]:
        """
        Extract generation parameters from successful pilot.

        Returns validated parameters for scale generation.
        """
        logger.info("Extracting parameters from pilot...")

        # Load one example to get generation params
        pilot_data_path = self.pilot_manifest_path.parent / "pilot_data.jsonl"

        with open(pilot_data_path) as f:
            first_example = json.loads(f.readline())

        gen_params = first_example['metadata']['generation_params']

        params = {
            "instruction_temperature": gen_params.get('instruction_temperature', 0.7),
            "instruction_top_p": gen_params.get('instruction_top_p', 0.9),
            "instruction_repetition_penalty": gen_params.get('instruction_repetition_penalty', 1.1),
            "response_temperature": gen_params.get('response_temperature', 0.4),
            "response_top_p": gen_params.get('response_top_p', 0.9),
            "response_repetition_penalty": gen_params.get('response_repetition_penalty', 1.1),
            "response_max_tokens": gen_params.get('response_max_tokens', 80),
            "confidence_threshold": gen_params.get('confidence_threshold', 1.0)
        }

        logger.info(f"✅ Extracted parameters from pilot")
        logger.info(f"   Response temp: {params['response_temperature']}")
        logger.info(f"   Response top_p: {params['response_top_p']}")

        return params

    def generate_shard(
        self,
        shard_id: int,
        examples_per_shard: int,
        params: Dict[str, Any]
    ) -> Path:
        """
        Generate one shard of data.

        Args:
            shard_id: Shard identifier
            examples_per_shard: Number of examples for this shard
            params: Generation parameters from pilot

        Returns:
            Path to shard directory
        """
        logger.info(f"Generating shard {shard_id}/{self.num_shards}...")

        shard_seed = self.base_seed + shard_id
        shard_dir = self.shards_dir / f"shard_{shard_id:02d}"
        shard_dir.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = [
            "python3",
            "scripts/generate_stage1_pilot_data.py",
            "--count", str(examples_per_shard),
            "--output", str(shard_dir),
            "--seed", str(shard_seed),
            "--instruction-temperature", str(params['instruction_temperature']),
            "--instruction-top-p", str(params['instruction_top_p']),
            "--instruction-repetition-penalty", str(params['instruction_repetition_penalty']),
            "--response-temperature", str(params['response_temperature']),
            "--response-top-p", str(params['response_top_p']),
            "--response-repetition-penalty", str(params['response_repetition_penalty']),
            "--response-max-tokens", str(params['response_max_tokens']),
            "--confidence-threshold", str(params['confidence_threshold'])
        ]

        logger.info(f"   Seed: {shard_seed}")
        logger.info(f"   Target: {examples_per_shard} examples")

        # Run generation (blocking)
        import subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200  # 2 hour timeout per shard
        )

        if result.returncode != 0:
            logger.error(f"❌ Shard {shard_id} failed:")
            logger.error(result.stderr[-1000:])  # Last 1000 chars
            raise RuntimeError(f"Shard {shard_id} generation failed")

        logger.info(f"✅ Shard {shard_id} complete")

        return shard_dir

    def merge_shards(
        self,
        shard_dirs: List[Path]
    ) -> int:
        """
        Merge shard outputs into single dataset.

        Args:
            shard_dirs: List of shard directories

        Returns:
            Total number of examples merged
        """
        logger.info(f"Merging {len(shard_dirs)} shards...")

        total_examples = 0

        with open(self.output_path, 'w') as out_f:
            for i, shard_dir in enumerate(shard_dirs):
                shard_data = shard_dir / "pilot_data.jsonl"

                if not shard_data.exists():
                    logger.warning(f"⚠️  Shard {i} data not found: {shard_data}")
                    continue

                with open(shard_data) as in_f:
                    for line in in_f:
                        out_f.write(line)
                        total_examples += 1

                logger.info(f"   Merged shard {i}: +{sum(1 for _ in open(shard_data))} examples")

        logger.info(f"✅ Merged {total_examples} total examples to {self.output_path}")

        return total_examples

    def recompute_qc(
        self,
        merged_path: Path
    ) -> Dict[str, Any]:
        """
        Recompute QC metrics on merged dataset.

        Args:
            merged_path: Path to merged JSONL

        Returns:
            QC summary dict
        """
        logger.info("Recomputing QC on merged dataset...")

        # Load all examples
        examples = []
        with open(merged_path) as f:
            for line in f:
                examples.append(json.loads(line))

        # Compute statistics
        counts = {
            "total_examples": len(examples),
            "delimiter_found": sum(1 for ex in examples if "###END###" in ex.get('metadata', {}).get('generation_params', {}).get('raw_response', '')),
            "hit_token_limit": 0  # Need to track this in metadata
        }

        # Token statistics
        tokens = []
        for ex in examples:
            # Count tokens in response
            response = ex['response']
            # Rough token count (actual would need tokenizer)
            token_count = len(response.split())
            tokens.append(token_count)

        token_stats = {
            "median": float(np.median(tokens)),
            "mean": float(np.mean(tokens)),
            "p95": float(np.percentile(tokens, 95)),
            "min": int(np.min(tokens)),
            "max": int(np.max(tokens))
        }

        # Acceptance rates (from critiques)
        pair_good = sum(1 for ex in examples if ex.get('pair_critique', {}).get('is_good', False))
        pair_total = len(examples)

        acceptance = {
            "pairs_good": pair_good,
            "pairs_bad": pair_total - pair_good
        }

        # Check thresholds
        failed_reasons = []
        thresholds_passed = True

        # Runaway rate (detect actual runaways: multiple Q/A pairs, not just long responses)
        # Fixed heuristic: pattern-based detection, not length-based
        runaway_patterns = [
            '\n\nInstruction:',
            '\n\nQuestion:',
            '\n\nQ:',
            '\nUser:',
            '\nAssistant:',
            '\nHuman:'
        ]

        runaway_count = sum(
            1 for ex in examples
            if any(pattern in ex['response'] for pattern in runaway_patterns)
            or len(ex['response']) > 500  # Extremely long responses only
        )
        runaway_rate = runaway_count / len(examples) if examples else 0

        if runaway_rate >= self.QC_THRESHOLDS['runaway_rate_max']:
            failed_reasons.append(f"Runaway rate {runaway_rate:.1%} >= {self.QC_THRESHOLDS['runaway_rate_max']:.1%}")
            thresholds_passed = False

        # Median tokens
        if token_stats['median'] >= self.QC_THRESHOLDS['median_tokens_max']:
            failed_reasons.append(f"Median tokens {token_stats['median']:.1f} >= {self.QC_THRESHOLDS['median_tokens_max']}")
            thresholds_passed = False

        # Delimiter leakage
        delimiter_in_responses = sum(1 for ex in examples if "###END###" in ex['response'])
        if delimiter_in_responses > 0:
            failed_reasons.append(f"Delimiter leakage: {delimiter_in_responses} occurrences")
            thresholds_passed = False

        # Create QC summary
        qc = create_qc_summary(
            counts=counts,
            acceptance=acceptance,
            token_stats=token_stats,
            margins={},  # Would need to recompute from examples
            thresholds=self.QC_THRESHOLDS,
            thresholds_passed=thresholds_passed,
            failed_reasons=failed_reasons
        )

        qc['rates'] = {
            "runaway_rate": runaway_rate,
            "delimiter_leakage_count": delimiter_in_responses,
            "pair_acceptance": pair_good / pair_total if pair_total else 0
        }

        logger.info(f"✅ QC recomputed on {len(examples)} examples")
        logger.info(f"   Thresholds passed: {thresholds_passed}")

        if not thresholds_passed:
            logger.warning("⚠️  QC THRESHOLDS FAILED on merged data:")
            for reason in failed_reasons:
                logger.warning(f"   - {reason}")

        return qc

    def run(
        self,
        total_count: int = 15000
    ) -> Dict[str, Path]:
        """
        Run full scale generation.

        Args:
            total_count: Total number of examples to generate

        Returns:
            Dict with paths to generated artifacts
        """
        logger.info("=" * 60)
        logger.info(f"STARTING STAGE 1 SCALE DATA GENERATION (target: {total_count} examples)")
        logger.info("=" * 60)

        # Step 1: Verify pilot passed
        self.verify_pilot_passed()

        # Step 2: Extract parameters
        params = self.extract_pilot_parameters()

        # Step 3: Calculate shard sizes
        examples_per_shard = total_count // self.num_shards
        logger.info(f"\nGenerating {self.num_shards} shards of ~{examples_per_shard} examples each")

        # Step 4: Generate shards
        logger.info("\n📦 PHASE 1: SHARD GENERATION")
        logger.info("-" * 60)

        shard_dirs = []
        for shard_id in range(self.num_shards):
            try:
                shard_dir = self.generate_shard(
                    shard_id,
                    examples_per_shard,
                    params
                )
                shard_dirs.append(shard_dir)
            except Exception as e:
                logger.error(f"❌ Shard {shard_id} failed: {e}")
                logger.error("Continuing with remaining shards...")

        logger.info(f"✅ Generated {len(shard_dirs)}/{self.num_shards} shards")

        # Step 5: Merge shards
        logger.info("\n🔀 PHASE 2: MERGING SHARDS")
        logger.info("-" * 60)

        total_merged = self.merge_shards(shard_dirs)

        # Step 6: Recompute QC
        logger.info("\n📊 PHASE 3: QC ON MERGED DATA")
        logger.info("-" * 60)

        qc_summary = self.recompute_qc(self.output_path)

        # Step 7: Save scale manifest
        logger.info("\n💾 PHASE 4: SAVING MANIFESTS")
        logger.info("-" * 60)

        scale_manifest = create_session_manifest(
            session_id=f"stage1_scale_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            planned_artifacts=["stage1_sft_data.jsonl", "qc_summary_merged.json"],
            gpu_hours_estimate=total_count / 100 * 0.5,  # Rough estimate
            notes=f"Scale generation from pilot at {self.pilot_manifest_path}"
        )

        scale_manifest['pilot_manifest'] = str(self.pilot_manifest_path)
        scale_manifest['num_shards'] = self.num_shards
        scale_manifest['parameters'] = params

        # Save QC summary
        qc_path = self.artifacts_dir / "qc_summary_merged.json"
        with open(qc_path, 'w') as f:
            json.dump(qc_summary, f, indent=2)

        logger.info(f"✅ Saved merged QC: {qc_path}")

        scale_manifest = update_session_manifest(
            scale_manifest,
            str(self.output_path),
            "sft_data_merged",
            success=True
        )

        scale_manifest = update_session_manifest(
            scale_manifest,
            str(qc_path),
            "qc_summary_merged",
            success=True
        )

        # Save scale manifest
        manifest_path = self.artifacts_dir / "scale_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(scale_manifest, f, indent=2)

        logger.info(f"✅ Saved scale manifest: {manifest_path}")

        logger.info("\n" + "=" * 60)
        logger.info("✅ SCALE GENERATION COMPLETE")
        logger.info(f"   Total examples: {total_merged}")
        logger.info(f"   QC Status: {'PASS' if qc_summary['thresholds_passed'] else 'FAIL'}")
        logger.info(f"   Output: {self.output_path}")
        logger.info("=" * 60)

        return {
            'merged_data': self.output_path,
            'qc_summary': qc_path,
            'scale_manifest': manifest_path
        }


def main():
    parser = argparse.ArgumentParser(
        description="Generate Stage 1 scale data (15k examples)"
    )
    parser.add_argument(
        "--pilot-manifest",
        type=str,
        required=True,
        help="Path to successful pilot session_manifest.json"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=15000,
        help="Total number of examples to generate (default: 15000)"
    )
    parser.add_argument(
        "--num-shards",
        type=int,
        default=10,
        help="Number of shards (default: 10)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/stage1_sft_data.jsonl",
        help="Output path for merged data (default: data/stage1_sft_data.jsonl)"
    )
    parser.add_argument(
        "--base-seed",
        type=int,
        default=100,
        help="Base seed for sharding (default: 100)"
    )

    args = parser.parse_args()

    # Verify pilot manifest exists
    pilot_manifest = Path(args.pilot_manifest)
    if not pilot_manifest.exists():
        logger.error(f"❌ Pilot manifest not found: {pilot_manifest}")
        sys.exit(1)

    # Create generator
    generator = Stage1ScaleGenerator(
        pilot_manifest_path=pilot_manifest,
        output_path=Path(args.output),
        num_shards=args.num_shards,
        base_seed=args.base_seed
    )

    # Run scale generation
    try:
        artifacts = generator.run(total_count=args.count)

        # Check final QC
        with open(artifacts['qc_summary']) as f:
            qc = json.load(f)

        if qc['thresholds_passed']:
            logger.info("\n✅ SCALE QC PASSED - Ready for SFT training")
            sys.exit(0)
        else:
            logger.warning("\n⚠️  SCALE QC FAILED - Review and investigate")
            sys.exit(1)

    except RuntimeError as e:
        logger.error(f"\n❌ Scale generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
