#!/usr/bin/env python3
"""
Stage 1 Evaluation: Compare trained model against baseline
Measures improvement in instruction following capabilities
"""

import json
import torch
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import os
import sys

# Configure base directory for RunPod deployment
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/cai-constitution-bootstrap'))

# Add utils to path
sys.path.append(str(BASE_DIR / 'scripts' / 'utils'))

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from unsloth import FastLanguageModel

from model_loader import load_base_model, generate_text, clear_gpu_cache, print_gpu_utilization
from metrics import InstructionFollowingEvaluator, StageEvaluator, save_evaluation_results, print_evaluation_summary
from data_formatter import Stage1DataGenerator, load_jsonl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Stage1Evaluator:
    """Comprehensive evaluation for Stage 1 model"""
    
    def __init__(self, base_model_name: str = "Qwen/Qwen2.5-32B"):
        self.base_model_name = base_model_name
        self.base_model = None
        self.trained_model = None
        self.tokenizer = None
        self.evaluator = InstructionFollowingEvaluator()
        self.stage_evaluator = StageEvaluator(stage_number=1)
        
        # Paths
        self.data_dir = BASE_DIR / "data" / "stage1"
        self.results_dir = BASE_DIR / "results"
        self.checkpoint_dir = BASE_DIR / "checkpoints" / "stage1"
        self.results_dir.mkdir(exist_ok=True)
        
        logger.info("📊 Stage 1 evaluator initialized")
    
    def load_base_model(self):
        """Load the base model for comparison"""
        if self.base_model is None:
            logger.info(f"📥 Loading base model: {self.base_model_name}")
            # Use consistent 8-bit precision for fair comparison
            self.base_model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.base_model_name,
                max_seq_length=2048,
                dtype=None,
                load_in_8bit=True,  # Match trained model precision
            )
            logger.info("✅ Base model loaded with 8-bit precision")
    
    def load_trained_model(self, lora_adapter_path: str):
        """Load the trained model with LoRA adapters"""
        logger.info(f"📥 Loading trained model from: {lora_adapter_path}")
        
        try:
            # Load base model with Unsloth - use 8-bit for consistency  
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.base_model_name,
                max_seq_length=2048,
                dtype=None,
                load_in_8bit=True,  # Match base model precision
            )
            
            # Load LoRA adapters
            self.trained_model = PeftModel.from_pretrained(model, lora_adapter_path)
            
            # Merge LoRA for better inference quality
            logger.info("🔄 Merging LoRA adapters for evaluation...")
            self.trained_model = self.trained_model.merge_and_unload()
            
            # Use the same tokenizer
            if self.tokenizer is None:
                self.tokenizer = tokenizer
            
            logger.info("✅ Trained model loaded and merged")
            print_gpu_utilization()
            
        except Exception as e:
            logger.error(f"❌ Failed to load trained model: {e}")
            raise
    
    def generate_evaluation_set(self, size: int = 200) -> List[Dict[str, Any]]:
        """Get persistent held-out evaluation set (load if exists, create if not)"""
        
        eval_file = BASE_DIR / "data" / "stage1" / "eval_instructions.jsonl"
        
        if eval_file.exists():
            logger.info("📚 Loading existing persistent evaluation set")
            eval_instructions = load_jsonl(eval_file)
            
            # Verify no leakage (critical check)
            if not verify_no_leakage():
                raise ValueError("Data leakage detected in persistent eval set")
            
            # Use requested size or all available
            final_set = eval_instructions[:size] if len(eval_instructions) >= size else eval_instructions
            logger.info(f"✅ Using {len(final_set)} persistent evaluation examples")
            
        else:
            logger.info("🔒 Creating new persistent evaluation set")
            final_set = create_held_out_eval_set(size)
            logger.info(f"✅ Created and saved {len(final_set)} persistent evaluation examples")
        
        return final_set
    
    def evaluate_model_on_set(self, model: Any, instruction_set: List[Dict[str, Any]], 
                             model_name: str) -> Dict[str, Any]:
        """Evaluate a model on a set of instructions"""
        logger.info(f"🧪 Evaluating {model_name}...")
        
        results = []
        
        for instruction_data in instruction_set:
            instruction = instruction_data['instruction']
            instruction_type = instruction_data['instruction_type']
            
            # CORRECT METHODOLOGY: Both models get identical raw instructions
            # This measures instruction-following learning, which is the goal
            response = generate_text(
                model, 
                self.tokenizer, 
                instruction,  # Raw instruction for both base and trained models
                max_new_tokens=150,
                temperature=0.1,  # Low temperature for consistency
                do_sample=False   # Deterministic for fair comparison
            )
            
            # Evaluate response
            success, reason, details = self.evaluator.evaluate_response(
                instruction, response, instruction_type
            )
            
            result = {
                'instruction': instruction,
                'response': response,
                'instruction_type': instruction_type,
                'success': success,
                'reason': reason,
                'details': details,
                'model': model_name
            }
            results.append(result)
        
        # Calculate metrics using stage evaluator
        evaluation_results = self.stage_evaluator.evaluate_dataset(results)
        evaluation_results['model_name'] = model_name
        
        return evaluation_results
    
    def load_baseline_results(self) -> Dict[str, Any]:
        """Load baseline assessment results"""
        baseline_file = self.results_dir / "baseline_assessment.json"
        
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                baseline_results = json.load(f)
            logger.info("📊 Loaded baseline assessment results")
            return baseline_results
        else:
            logger.warning("⚠️  No baseline results found. Run baseline_assessment.py first!")
            return {}
    
    def compare_models(self, base_results: Dict, trained_results: Dict, 
                      baseline_results: Dict = None) -> Dict[str, Any]:
        """Compare base and trained model performance"""
        logger.info("📊 Comparing model performance...")
        
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'model': self.base_model_name,
            'stage': 1,
            'methodology_docs': {
                'evaluation_philosophy': 'specs/stage_1_evaluation_philosophy.md',
                'sequential_architecture': 'specs/sequential_bootstrapping_architecture.md', 
                'methodology_clarification': 'specs/METHODOLOGY_CLARIFICATION.md',
                'stage_specifications': 'specs/stage_1_explicit_instructions.md'
            },
            'evaluation_approach': 'Both models evaluated with identical raw instructions to measure instruction-following learning',
            'note': 'Stage 1 focuses on instruction-following capability, not full constitutional AI',
            'base_model_name': self.base_model_name,
            'models': {
                'base': base_results,
                'trained': trained_results
            },
            'improvement': {
                'overall': trained_results['success_rate'] - base_results['success_rate']
            },
            'improvement_by_type': {}
        }
        
        # Calculate improvement by instruction type
        base_by_type = base_results.get('by_type', {})
        trained_by_type = trained_results.get('by_type', {})
        
        for instruction_type in set(base_by_type.keys()) | set(trained_by_type.keys()):
            base_rate = base_by_type.get(instruction_type, {}).get('success_rate', 0)
            trained_rate = trained_by_type.get(instruction_type, {}).get('success_rate', 0)
            improvement = trained_rate - base_rate
            
            comparison['improvement_by_type'][instruction_type] = {
                'base': base_rate,
                'trained': trained_rate,
                'improvement': improvement,
                'relative_improvement': improvement / base_rate if base_rate > 0 else float('inf')
            }
        
        # Compare with baseline assessment if available
        if baseline_results:
            comparison['baseline_comparison'] = self.stage_evaluator.compare_with_baseline(
                trained_results, baseline_results
            )
        
        # Add methodology section for full clarification
        methodology_section = {
            'stage_1_goal': 'Teach instruction-following to base model',
            'evaluation_approach': 'Identical raw instructions to both models',
            'expected_pattern': 'Base struggles (~50%), Trained succeeds (95%+)',
            'why_fair': 'Tests exactly what Stage 1 training teaches',
            'documentation': [
                'specs/stage_1_evaluation_philosophy.md',
                'specs/sequential_bootstrapping_architecture.md'
            ],
            'not_full_cai': 'Stage 1 is capability building, full CAI happens in Stage 6'
        }
        comparison['methodology'] = methodology_section
        
        return comparison
    
    def run_comprehensive_evaluation(self, lora_adapter_path: str, 
                                   eval_set_size: int = 200) -> Dict[str, Any]:
        """Run comprehensive evaluation comparing base vs trained model"""
        logger.info("🚀 Starting comprehensive Stage 1 evaluation...")
        
        try:
            # Load models
            self.load_base_model()
            self.load_trained_model(lora_adapter_path)
            
            # Add persistent eval set documentation
            eval_file = BASE_DIR / "data" / "stage1" / "eval_instructions.jsonl"
            logger.info("🔒 Using persistent held-out evaluation set for paired analysis")
            logger.info(f"📊 Eval set file: {eval_file}")
            logger.info(f"🔍 Overlap report: {BASE_DIR / 'data' / 'stage1' / 'overlap_report.json'}")
            
            # Add methodology notices
            logger.info("📋 Evaluation Methodology:")
            logger.info("   Both models receive identical raw instructions")
            logger.info("   This measures instruction-following learning (Stage 1 goal)")
            logger.info("   See specs/stage_1_evaluation_philosophy.md for details")
            logger.info("   Expected: Base model ~50%, Trained model 95%+ success")
            
            # Generate evaluation set
            eval_set = self.generate_evaluation_set(eval_set_size)
            
            # Evaluate base model
            logger.info("📊 Evaluating base model...")
            base_results = self.evaluate_model_on_set(
                self.base_model, eval_set, "base_model"
            )
            
            # Evaluate trained model
            logger.info("📊 Evaluating trained model...")
            trained_results = self.evaluate_model_on_set(
                self.trained_model, eval_set, "stage1_trained"
            )
            
            # Load baseline assessment for context
            baseline_results = self.load_baseline_results()
            
            # Compare results
            comparison = self.compare_models(base_results, trained_results, baseline_results)
            
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = self.results_dir / f"stage1_evaluation_{timestamp}.json"
            save_evaluation_results(comparison, results_file)
            
            # Print summary
            self.print_evaluation_summary(comparison)
            
            logger.info("🎉 Comprehensive evaluation complete!")
            return comparison
            
        except Exception as e:
            logger.error(f"❌ Evaluation failed: {e}")
            raise
        
        finally:
            clear_gpu_cache()
    
    def print_evaluation_summary(self, comparison: Dict[str, Any]):
        """Print a nice summary of evaluation results"""
        print("\n" + "="*70)
        print("📊 STAGE 1 EVALUATION RESULTS")
        print("="*70)
        
        base_results = comparison['models']['base']
        trained_results = comparison['models']['trained']
        
        print(f"Base Model Performance:    {base_results['success_rate']:.1%} ({base_results['successes']}/{base_results['total']})")
        print(f"Trained Model Performance: {trained_results['success_rate']:.1%} ({trained_results['successes']}/{trained_results['total']})")
        print(f"Overall Improvement:       +{comparison['improvement']['overall']:.1%}")
        
        print("\nImprovement by Instruction Type:")
        print("-" * 50)
        
        for instruction_type, improvement_data in comparison['improvement_by_type'].items():
            base_rate = improvement_data['base']
            trained_rate = improvement_data['trained']
            improvement = improvement_data['improvement']
            relative = improvement_data['relative_improvement']
            
            print(f"{instruction_type.capitalize():12}: {base_rate:.1%} → {trained_rate:.1%} (+{improvement:.1%}, {relative:.1f}x)")
        
        # Show baseline comparison if available
        if 'baseline_comparison' in comparison:
            print(f"\nComparison with Initial Baseline Assessment:")
            print("-" * 50)
            baseline_comp = comparison['baseline_comparison']
            print(f"Overall improvement from baseline: +{baseline_comp['overall_improvement']:.1%}")
            
            if 'by_category' in baseline_comp:
                for category, data in baseline_comp['by_category'].items():
                    print(f"{category.capitalize():12}: {data['baseline']:.1%} → {data['current']:.1%} (+{data['improvement']:.1%})")
        
        print("="*70)
        
        # Success criteria check
        overall_success_rate = trained_results['success_rate']
        if overall_success_rate >= 0.95:
            print("🎉 SUCCESS: Achieved target 95%+ instruction following!")
        elif overall_success_rate >= 0.90:
            print("🟡 GOOD: Close to target (90%+), consider more training")
        else:
            print("🔴 NEEDS WORK: Below 90%, requires investigation")
        
        print()
    
    def quick_test(self, lora_adapter_path: str, num_examples: int = 20):
        """Quick test with a few examples for debugging"""
        logger.info(f"🧪 Running quick test ({num_examples} examples)...")
        
        # Load models
        self.load_base_model()
        self.load_trained_model(lora_adapter_path)
        
        # Generate small test set
        eval_set = self.generate_evaluation_set(num_examples)
        
        print("\n" + "="*80)
        print("🔍 QUICK TEST RESULTS")
        print("="*80)
        
        for i, instruction_data in enumerate(eval_set[:10]):  # Show first 10
            instruction = instruction_data['instruction']
            instruction_type = instruction_data['instruction_type']
            
            # Get responses from both models
            base_response = generate_text(self.base_model, self.tokenizer, instruction, max_new_tokens=100)
            trained_response = generate_text(self.trained_model, self.tokenizer, instruction, max_new_tokens=100)
            
            # Evaluate both
            base_success, base_reason, _ = self.evaluator.evaluate_response(instruction, base_response, instruction_type)
            trained_success, trained_reason, _ = self.evaluator.evaluate_response(instruction, trained_response, instruction_type)
            
            print(f"\n📝 Example {i+1} ({instruction_type}):")
            print(f"Instruction: {instruction}")
            print(f"Base:    {'✅' if base_success else '❌'} {base_response[:80]}{'...' if len(base_response) > 80 else ''}")
            print(f"Trained: {'✅' if trained_success else '❌'} {trained_response[:80]}{'...' if len(trained_response) > 80 else ''}")
            
            if not base_success and trained_success:
                print("         🎉 IMPROVEMENT!")
            elif base_success and not trained_success:
                print("         😰 REGRESSION!")
        
        print("="*80)


def create_held_out_eval_set(eval_count: int = 100) -> List[Dict[str, Any]]:
    """Create evaluation set that's guaranteed disjoint from training"""
    logger.info(f"🔒 Creating held-out evaluation set ({eval_count} instructions)...")
    
    # Load training instructions if they exist
    train_file = BASE_DIR / "data" / "stage1" / "train_instructions.jsonl"
    train_instructions = set()
    
    if train_file.exists():
        train_data = load_jsonl(train_file)
        train_instructions = {item['instruction'] for item in train_data}
        logger.info(f"📚 Loaded {len(train_instructions)} training instructions to avoid")
    else:
        logger.warning("⚠️  No training instructions found - cannot prevent leakage")
    
    # Generate evaluation instructions using eval pools
    eval_generator = Stage1DataGenerator(seed=12345)
    
    # Generate more than needed to account for filtering
    eval_instructions = []
    attempts = 0
    max_attempts = 10
    
    while len(eval_instructions) < eval_count and attempts < max_attempts:
        # Generate candidates from eval pools
        candidates = eval_generator.generate_all_instructions(
            qa_count=eval_count // 4 + 10,
            completion_count=eval_count // 4 + 10,
            generation_count=eval_count // 4 + 10,
            response_count=eval_count // 4 + 10,
            is_eval=True  # CRITICAL: Use eval pools only
        )
        
        # Filter out any that appear in training
        for candidate in candidates:
            if candidate['instruction'] not in train_instructions:
                eval_instructions.append(candidate)
                if len(eval_instructions) >= eval_count:
                    break
        
        attempts += 1
    
    if len(eval_instructions) < eval_count:
        logger.warning(f"⚠️  Could only generate {len(eval_instructions)} unique eval instructions")
    
    # Take exactly what we need
    final_eval_set = eval_instructions[:eval_count]
    
    # Save for reproducibility
    eval_file = BASE_DIR / "data" / "stage1" / "eval_instructions.jsonl"
    eval_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Need to implement save function - use the same pattern as existing code
    import json
    with open(eval_file, 'w') as f:
        for item in final_eval_set:
            json.dump(item, f)
            f.write('\n')
    
    # Create detailed overlap report
    import hashlib
    overlap_report = {
        'timestamp': datetime.now().isoformat(),
        'train_count': len(train_instructions),
        'eval_count': len(final_eval_set),
        'overlap_count': 0,  # Should always be 0 by construction
        'eval_seed': 12345,
        'generation_attempts': attempts,
        'train_file_hash': hashlib.md5(str(sorted(train_instructions)).encode()).hexdigest(),
        'eval_file_hash': hashlib.md5(str(sorted([x['instruction'] for x in final_eval_set])).encode()).hexdigest()
    }
    
    report_file = BASE_DIR / "data" / "stage1" / "overlap_report.json"
    with open(report_file, 'w') as f:
        json.dump(overlap_report, f, indent=2)
    
    logger.info(f"✅ Created {len(final_eval_set)} held-out eval instructions")
    logger.info(f"📊 Overlap report saved to {report_file}")
    
    return final_eval_set


def verify_no_leakage() -> bool:
    """Verify zero overlap between train and eval sets"""
    logger.info("🔍 Verifying no data leakage...")
    
    train_file = BASE_DIR / "data" / "stage1" / "train_instructions.jsonl"
    eval_file = BASE_DIR / "data" / "stage1" / "eval_instructions.jsonl"
    
    if not train_file.exists() or not eval_file.exists():
        logger.warning("⚠️  Train or eval file not found, cannot verify")
        return False
    
    train_data = load_jsonl(train_file)
    eval_data = load_jsonl(eval_file)
    
    train_instructions = {item['instruction'] for item in train_data}
    eval_instructions = {item['instruction'] for item in eval_data}
    
    overlap = train_instructions & eval_instructions
    
    if overlap:
        logger.error(f"🚨 FATAL: Found {len(overlap)} overlapping instructions!")
        logger.error(f"Examples: {list(overlap)[:3]}")
        return False
    
    logger.info(f"✅ Verified: 0 overlap between {len(train_instructions)} train and {len(eval_instructions)} eval")
    return True


def find_latest_checkpoint() -> str:
    """Find the latest Stage 1 checkpoint"""
    checkpoint_dir = BASE_DIR / "checkpoints" / "stage1"
    
    if not checkpoint_dir.exists():
        raise FileNotFoundError("No Stage 1 checkpoints found")
    
    # Look for training success markers (more robust)
    success_markers = []
    for path in checkpoint_dir.rglob("TRAINING_SUCCESS"):
        if path.is_file():
            success_markers.append(path)
    
    if success_markers:
        # Return adapter path from the most recent successful training
        latest_marker = max(success_markers, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest_marker, 'r') as f:
                marker_data = json.load(f)
            adapter_path = marker_data.get('adapter_path')
            if adapter_path and Path(adapter_path).exists():
                logger.info(f"📁 Found latest checkpoint from success marker: {adapter_path}")
                return adapter_path
        except Exception as e:
            logger.warning(f"⚠️  Could not read success marker: {e}")
    
    # Fallback to old method
    adapter_dirs = []
    for path in checkpoint_dir.rglob("final_lora_adapters"):
        if path.is_dir():
            adapter_dirs.append(path)
    
    if not adapter_dirs:
        raise FileNotFoundError("No LoRA adapter checkpoints found")
    
    # Return the most recent one
    latest = max(adapter_dirs, key=lambda p: p.stat().st_mtime)
    logger.info(f"📁 Found latest checkpoint: {latest}")
    return str(latest)


def main():
    """Run Stage 1 evaluation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate Stage 1 model")
    parser.add_argument("--model", default="Qwen/Qwen2.5-32B", help="Base model name")
    parser.add_argument("--checkpoint", help="Path to LoRA adapter checkpoint")
    parser.add_argument("--eval-size", type=int, default=200, help="Number of evaluation examples")
    parser.add_argument("--quick", action="store_true", help="Quick test with 20 examples")
    
    args = parser.parse_args()
    
    # Find checkpoint if not specified
    if args.checkpoint is None:
        try:
            args.checkpoint = find_latest_checkpoint()
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            logger.error("🚨 Please train a Stage 1 model first or specify --checkpoint")
            return
    
    # Create evaluator
    evaluator = Stage1Evaluator(args.model)
    
    try:
        if args.quick:
            # Quick test
            evaluator.quick_test(args.checkpoint, 20)
        else:
            # Comprehensive evaluation
            results = evaluator.run_comprehensive_evaluation(
                args.checkpoint, args.eval_size
            )
            
            print(f"🎉 Evaluation complete! Results saved to results/")
    
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        raise


if __name__ == "__main__":
    main()