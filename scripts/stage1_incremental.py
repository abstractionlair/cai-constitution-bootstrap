#!/usr/bin/env python3
"""
Stage 1 Incremental Pipeline with Inspection Points
Allows for manual review of artifacts at each stage
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base directory
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/cai-constitution-bootstrap'))
sys.path.append(str(BASE_DIR / 'scripts'))

def create_checkpoint(stage_name: str, artifacts: dict, checkpoint_dir: Path):
    """Create a checkpoint with artifacts for inspection"""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_file = checkpoint_dir / f"{stage_name}_{timestamp}.json"
    
    checkpoint_data = {
        'stage': stage_name,
        'timestamp': timestamp,
        'artifacts': artifacts,
        'status': 'pending_review'
    }
    
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)
    
    logger.info(f"📌 Checkpoint created: {checkpoint_file}")
    return checkpoint_file

def wait_for_approval(stage_name: str):
    """Wait for user approval before proceeding"""
    print("\n" + "="*60)
    print(f"🛑 INSPECTION POINT: {stage_name}")
    print("="*60)
    print("Review the generated artifacts, then type 'continue' to proceed")
    print("Type 'abort' to stop the pipeline")
    print("="*60)
    
    while True:
        response = input("Your decision: ").strip().lower()
        if response == 'continue':
            logger.info(f"✅ Proceeding past {stage_name}")
            return True
        elif response == 'abort':
            logger.warning(f"❌ Pipeline aborted at {stage_name}")
            return False
        else:
            print("Please type 'continue' or 'abort'")

def run_incremental_pipeline():
    """Run Stage 1 pipeline with inspection points"""
    
    # Setup directories
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = BASE_DIR / "runs" / f"stage1_{run_id}"
    artifacts_dir = run_dir / "artifacts"
    checkpoints_dir = run_dir / "checkpoints"
    
    for dir_path in [run_dir, artifacts_dir, checkpoints_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"🚀 Starting incremental Stage 1 pipeline")
    logger.info(f"📁 Run directory: {run_dir}")
    
    # Stage 1: Generate Instructions
    logger.info("\n" + "="*60)
    logger.info("STAGE 1: Generating Instructions")
    logger.info("="*60)
    
    from generate_stage1_data import Stage1DataGenerator
    
    generator = Stage1DataGenerator(
        output_dir=artifacts_dir,
        num_instructions=100,  # Start small for inspection
        seed=42
    )
    
    instructions = generator.generate_all_instructions(
        qa_count=25,
        completion_count=25,
        generation_count=25,
        response_count=25
    )
    
    # Save for inspection
    instructions_file = artifacts_dir / "instructions.jsonl"
    generator.save_jsonl(instructions, instructions_file)
    
    # Create checkpoint
    checkpoint = create_checkpoint(
        "instructions_generated",
        {
            'count': len(instructions),
            'file': str(instructions_file),
            'types': {t: sum(1 for i in instructions if i['instruction_type'] == t) 
                     for t in ['qa', 'completion', 'generation', 'response']}
        },
        checkpoints_dir
    )
    
    # Show samples for inspection
    print("\n📝 Sample Instructions Generated:")
    for i, inst in enumerate(instructions[:5]):
        print(f"\n{i+1}. Type: {inst['instruction_type']}")
        print(f"   Instruction: {inst['instruction'][:100]}...")
    
    if not wait_for_approval("Instructions Generation"):
        return
    
    # Stage 2: Generate Initial Responses
    logger.info("\n" + "="*60)
    logger.info("STAGE 2: Generating Initial Responses")
    logger.info("="*60)
    
    logger.info("Loading base model for response generation...")
    responses = generator.generate_responses(instructions[:50])  # Test with subset
    
    # Save for inspection
    responses_file = artifacts_dir / "initial_responses.jsonl"
    generator.save_jsonl(responses, responses_file)
    
    # Show samples
    print("\n📝 Sample Responses Generated:")
    for i, resp in enumerate(responses[:3]):
        print(f"\n{i+1}. Instruction: {resp['instruction'][:80]}...")
        print(f"   Response: {resp['response'][:80]}...")
        print(f"   Success: {resp.get('success', 'unknown')}")
    
    checkpoint = create_checkpoint(
        "responses_generated",
        {
            'count': len(responses),
            'file': str(responses_file),
            'success_rate': sum(1 for r in responses if r.get('success')) / len(responses)
        },
        checkpoints_dir
    )
    
    if not wait_for_approval("Response Generation"):
        return
    
    # Stage 3: Generate Critiques
    logger.info("\n" + "="*60)
    logger.info("STAGE 3: Generating Constitutional Critiques")
    logger.info("="*60)
    
    critiques = generator.generate_critiques(responses)
    
    # Save for inspection
    critiques_file = artifacts_dir / "critiques.jsonl"
    generator.save_jsonl(critiques, critiques_file)
    
    # Show samples
    print("\n📝 Sample Critiques:")
    for i, critique in enumerate(critiques[:3]):
        print(f"\n{i+1}. Response: {critique['response'][:80]}...")
        print(f"   Critique: {critique['critique'][:150]}...")
        print(f"   Needs improvement: {critique.get('needs_improvement', 'unknown')}")
    
    checkpoint = create_checkpoint(
        "critiques_generated",
        {
            'count': len(critiques),
            'file': str(critiques_file),
            'improvement_rate': sum(1 for c in critiques if c.get('needs_improvement')) / len(critiques)
        },
        checkpoints_dir
    )
    
    if not wait_for_approval("Critique Generation"):
        return
    
    # Stage 4: Generate Improvements
    logger.info("\n" + "="*60)
    logger.info("STAGE 4: Generating Improved Responses")
    logger.info("="*60)
    
    improvements = generator.improve_responses(critiques)
    
    # Save for inspection
    improvements_file = artifacts_dir / "improvements.jsonl"
    generator.save_jsonl(improvements, improvements_file)
    
    # Show samples
    print("\n📝 Sample Improvements:")
    for i, imp in enumerate(improvements[:3]):
        print(f"\n{i+1}. Original: {imp['initial_response'][:80]}...")
        print(f"   Improved: {imp['improved_response'][:80]}...")
        print(f"   Success: {imp.get('improved_success', 'unknown')}")
    
    checkpoint = create_checkpoint(
        "improvements_generated",
        {
            'count': len(improvements),
            'file': str(improvements_file),
            'success_rate': sum(1 for i in improvements if i.get('improved_success')) / len(improvements)
        },
        checkpoints_dir
    )
    
    if not wait_for_approval("Improvement Generation"):
        return
    
    # Stage 5: Create Preference Pairs
    logger.info("\n" + "="*60)
    logger.info("STAGE 5: Creating DPO Preference Pairs")
    logger.info("="*60)
    
    preference_pairs = generator.create_preference_pairs(improvements)
    
    # Save for inspection
    pairs_file = artifacts_dir / "preference_pairs.jsonl"
    generator.save_jsonl(preference_pairs, pairs_file)
    
    # Show samples
    print("\n📝 Sample Preference Pairs:")
    for i, pair in enumerate(preference_pairs[:2]):
        print(f"\n{i+1}. Prompt: {pair['prompt'][:80]}...")
        print(f"   Chosen: {pair['chosen'][:80]}...")
        print(f"   Rejected: {pair['rejected'][:80]}...")
        print(f"   Reason: {pair['reason']}")
    
    checkpoint = create_checkpoint(
        "preference_pairs_created",
        {
            'count': len(preference_pairs),
            'file': str(pairs_file)
        },
        checkpoints_dir
    )
    
    if not wait_for_approval("Preference Pair Creation"):
        return
    
    # Stage 6: Training
    logger.info("\n" + "="*60)
    logger.info("STAGE 6: DPO Training")
    logger.info("="*60)
    print("\n⚠️  This will start GPU-intensive training")
    print("Estimated time: 2-3 hours")
    
    if not wait_for_approval("Start DPO Training"):
        return
    
    # Import and run training
    from train_stage1_dpo import train_stage1_dpo
    
    checkpoint_dir = run_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    
    train_stage1_dpo(
        train_data_path=str(pairs_file),
        output_dir=str(checkpoint_dir),
        num_epochs=1,  # Start with 1 epoch for testing
        batch_size=4,
        learning_rate=2e-5
    )
    
    logger.info("✅ Training complete!")
    
    # Stage 7: Evaluation
    logger.info("\n" + "="*60)
    logger.info("STAGE 7: Evaluation")
    logger.info("="*60)
    
    if not wait_for_approval("Start Evaluation"):
        return
    
    from evaluate_stage1 import Stage1Evaluator
    
    evaluator = Stage1Evaluator()
    results = evaluator.run_comprehensive_evaluation(
        lora_adapter_path=str(checkpoint_dir / "final_lora_adapters"),
        eval_set_size=50  # Small eval for testing
    )
    
    # Save results
    results_file = run_dir / "evaluation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📊 Evaluation Results:")
    print(f"Base model: {results['models']['base']['success_rate']:.1%}")
    print(f"Trained model: {results['models']['trained']['success_rate']:.1%}")
    print(f"Improvement: +{results['improvement']['overall']:.1%}")
    
    logger.info(f"✅ Pipeline complete! Results in {run_dir}")

if __name__ == "__main__":
    run_incremental_pipeline()