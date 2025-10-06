#!/usr/bin/env python3
"""
Generate preference pairs using A/B log-probability evaluation on all 100 responses
Creates high-quality training data by filtering for confident predictions

REFACTORED (2025-10-06):
- Uses CleanModelLoader for safe base model loading
- Reuses shared instruction_critic utilities for consistency
- Removes duplicate logprob implementation
"""

import json
import sys
import os
import torch
import numpy as np
from pathlib import Path
import logging
from collections import Counter
import time

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

# Import shared utilities (REFACTORED)
from utils.clean_model_loader import CleanModelLoader
from utils.instruction_critic import critique_instruction_response_pair

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ARTIFACTS_DIR / 'preference_generation.log')
    ]
)
logger = logging.getLogger(__name__)

def save_jsonl(data, filepath):
    """Save data in JSONL format"""
    with open(filepath, 'w') as f:
        for item in data:
            json.dump(item, f)
            f.write('\n')

# REMOVED: Duplicate implementations now use shared utilities from instruction_critic
# - create_ab_evaluation_prompt -> handled internally by critique_instruction_response_pair
# - get_token_logprobs -> instruction_critic.get_token_logprobs
# - evaluate_with_logprobs -> instruction_critic.critique_instruction_response_pair
# - load_model_with_retry -> CleanModelLoader handles this safely

def generate_bad_responses(instruction, inst_type, num_bad=2):
    """Generate obviously bad responses for contrast"""
    
    bad_responses = []
    
    # Generic bad patterns
    generic_bad = [
        "I cannot help with that request.",
        "I'm sorry, I don't understand.",
        "Please provide more information.",
        "That's not something I can do."
    ]
    
    # Type-specific bad patterns
    if inst_type == 'qa':
        bad_responses.extend([
            "What do you mean?",
            "I don't know the answer to that.",
            "Can you rephrase the question?"
        ])
    elif inst_type == 'completion':
        bad_responses.extend([
            "I cannot complete sentences.",
            "This is incomplete.",
            "More context needed."
        ])
    elif inst_type == 'generation':
        bad_responses.extend([
            "I cannot generate content.",
            "That's too broad a topic.",
            "Please be more specific."
        ])
    elif inst_type == 'response':
        bad_responses.extend([
            "I don't understand what you want.",
            "That doesn't make sense.",
            "Can you clarify?"
        ])
    
    # Add generic bad responses
    bad_responses.extend(generic_bad)
    
    # Return requested number
    return bad_responses[:num_bad]

def generate_preference_pairs():
    """Generate preference pairs using A/B log-probability evaluation"""
    
    logger.info("🚀 Starting preference pair generation with A/B log-probability evaluation")
    
    # Load all initial responses
    responses_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    with open(responses_file) as f:
        responses = [json.loads(line) for line in f]
    
    logger.info(f"📝 Loaded {len(responses)} initial responses")
    
    # Load model using CleanModelLoader (safe, prevents contamination)
    model_path = os.environ.get('MODEL_PATH', 'Qwen/Qwen2.5-32B')
    logger.info(f"Loading model: {model_path}")
    loader = CleanModelLoader(model_path, load_in_8bit=True)
    model, tokenizer, provenance = loader.load()
    logger.info(f"✅ Model loaded with provenance: {provenance}")
    
    # Evaluate all responses
    evaluations = []
    preference_pairs = []
    confidence_threshold = 1.0  # ChatGPT-5 Pro's suggestion
    
    start_time = time.time()
    
    logger.info(f"🔍 Evaluating {len(responses)} responses with A/B log-probability method...")
    
    for i, resp_data in enumerate(responses):
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(responses) - i) / rate if rate > 0 else 0
            
            logger.info(f"Progress: {i}/{len(responses)} ({i/len(responses)*100:.1f}%) "
                       f"Rate: {rate*60:.1f}/min ETA: {eta/60:.1f}min")
            logger.info(f"GPU memory: {torch.cuda.memory_allocated()/1e9:.1f}GB")
        
        instruction = resp_data['instruction']
        response = resp_data['response']
        inst_type = resp_data['instruction_type']

        # Use shared critic utility (consistent with v2 data generation)
        critique = critique_instruction_response_pair(
            model, tokenizer, instruction, response,
            confidence_threshold=confidence_threshold
        )

        # Convert to expected format
        eval_result = {
            'predicted_label': critique['predicted_label'],
            'predicted_judgment': 'good' if critique['is_good'] else 'bad',
            'logp_a': critique['logp_a'],
            'logp_b': critique['logp_b'],
            'margin': critique['margin'],
            'confident': critique['confident']
        }
        
        # Store evaluation
        evaluation = {
            'id': resp_data['id'],
            'instruction': instruction,
            'response': response.split('\n\n')[0].strip(),  # Clean response
            'instruction_type': inst_type,
            'original_success': resp_data.get('success', False),
            'logprob_evaluation': eval_result,
            'agrees_with_heuristic': (eval_result['predicted_judgment'] == 'good') == resp_data.get('success', False)
        }
        
        evaluations.append(evaluation)
        
        # Create preference pairs for confident evaluations
        if eval_result['confident']:
            clean_response = response.split('\n\n')[0].strip()
            
            if eval_result['predicted_judgment'] == 'good':
                # Good response - create pairs with bad responses
                bad_responses = generate_bad_responses(instruction, inst_type)
                
                for bad_response in bad_responses:
                    preference_pair = {
                        'id': f"{resp_data['id']}_vs_bad_{len(preference_pairs)}",
                        'instruction': instruction,
                        'chosen': clean_response,  # Good response
                        'rejected': bad_response,  # Bad response
                        'instruction_type': inst_type,
                        'confidence_margin': eval_result['margin'],
                        'source': 'logprob_good_vs_generated_bad'
                    }
                    preference_pairs.append(preference_pair)
            
            else:  # predicted_judgment == 'bad'
                # Bad response - we need good responses to pair it with
                # For now, create simple good responses based on instruction type
                if inst_type == 'qa' and 'What is' in instruction:
                    good_response = "This is a factual answer to the question."
                elif inst_type == 'completion' and instruction.endswith(('at', 'in the', 'is')):
                    good_response = "an appropriate completion"
                elif inst_type == 'generation':
                    good_response = f"Here is content about {instruction.lower().replace('describe', '').replace('generate', '').strip()}."
                else:
                    good_response = "This is an appropriate response to the instruction."
                
                preference_pair = {
                    'id': f"{resp_data['id']}_bad_vs_good_{len(preference_pairs)}",
                    'instruction': instruction,
                    'chosen': good_response,   # Good response
                    'rejected': clean_response, # Bad response (original)
                    'instruction_type': inst_type,
                    'confidence_margin': eval_result['margin'],
                    'source': 'generated_good_vs_logprob_bad'
                }
                preference_pairs.append(preference_pair)
        
        # Periodic cleanup
        if i % 25 == 0 and i > 0:
            torch.cuda.empty_cache()
    
    total_time = time.time() - start_time
    logger.info(f"✅ Evaluation complete in {total_time/60:.1f} minutes")
    
    # Analysis
    confident_evals = [e for e in evaluations if e['logprob_evaluation']['confident']]
    good_predictions = [e for e in evaluations if e['logprob_evaluation']['predicted_judgment'] == 'good']
    bad_predictions = [e for e in evaluations if e['logprob_evaluation']['predicted_judgment'] == 'bad']
    agreement_count = sum(1 for e in evaluations if e['agrees_with_heuristic'])
    
    logger.info(f"📊 Evaluation Results:")
    logger.info(f"  Total responses: {len(evaluations)}")
    logger.info(f"  Confident predictions: {len(confident_evals)}/{len(evaluations)} ({len(confident_evals)/len(evaluations):.1%})")
    logger.info(f"  Predicted good: {len(good_predictions)}")
    logger.info(f"  Predicted bad: {len(bad_predictions)}")
    logger.info(f"  Agreement with heuristic: {agreement_count}/{len(evaluations)} ({agreement_count/len(evaluations):.1%})")
    logger.info(f"  Preference pairs generated: {len(preference_pairs)}")
    
    # Save evaluations
    evaluations_file = ARTIFACTS_DIR / "logprob_evaluations.jsonl"
    save_jsonl(evaluations, evaluations_file)
    
    # Save preference pairs
    preference_pairs_file = ARTIFACTS_DIR / "logprob_preference_pairs.jsonl"
    save_jsonl(preference_pairs, preference_pairs_file)
    
    # Create summary
    by_type = Counter(e['instruction_type'] for e in evaluations)
    confident_by_type = Counter(e['instruction_type'] for e in confident_evals)
    good_by_type = Counter(e['instruction_type'] for e in good_predictions)
    
    summary = {
        'total_evaluations': len(evaluations),
        'confident_evaluations': len(confident_evals),
        'confidence_rate': len(confident_evals) / len(evaluations),
        'good_predictions': len(good_predictions),
        'bad_predictions': len(bad_predictions),
        'preference_pairs_generated': len(preference_pairs),
        'agreement_with_heuristic': agreement_count / len(evaluations),
        'evaluation_time_minutes': total_time / 60,
        'average_confidence_margin': np.mean([e['logprob_evaluation']['margin'] for e in confident_evals]),
        'by_type': dict(by_type),
        'confident_by_type': dict(confident_by_type),
        'good_predictions_by_type': dict(good_by_type)
    }
    
    summary_file = ARTIFACTS_DIR / "logprob_preference_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Text summary
    text_summary = f"""📊 A/B Log-Probability Preference Generation Summary
================================================

Total Responses Evaluated: {len(evaluations)}
Confident Predictions: {len(confident_evals)}/{len(evaluations)} ({len(confident_evals)/len(evaluations):.1%})
Preference Pairs Generated: {len(preference_pairs)}
Agreement with Heuristic: {agreement_count}/{len(evaluations)} ({agreement_count/len(evaluations):.1%})
Evaluation Time: {total_time/60:.1f} minutes

Predictions:
  Good: {len(good_predictions)} ({len(good_predictions)/len(evaluations):.1%})
  Bad: {len(bad_predictions)} ({len(bad_predictions)/len(evaluations):.1%})

Confident Predictions by Type:
"""
    for inst_type, total_count in by_type.items():
        confident_count = confident_by_type.get(inst_type, 0)
        good_count = good_by_type.get(inst_type, 0)
        text_summary += f"  {inst_type}: {confident_count}/{total_count} confident ({confident_count/total_count:.1%}), {good_count} good\n"

    text_summary += f"\nAverage Confidence Margin: {np.mean([e['logprob_evaluation']['margin'] for e in confident_evals]):.3f}\n"
    
    text_file = ARTIFACTS_DIR / "logprob_preference_summary.txt"
    with open(text_file, 'w') as f:
        f.write(text_summary)
    
    logger.info(f"💾 Results saved:")
    logger.info(f"  Evaluations: {evaluations_file}")
    logger.info(f"  Preference pairs: {preference_pairs_file}")
    logger.info(f"  Summary: {summary_file}")
    
    # Clear model
    del model
    torch.cuda.empty_cache()
    
    return evaluations, preference_pairs, summary

if __name__ == "__main__":
    try:
        evaluations, preference_pairs, summary = generate_preference_pairs()
        
        print("\n" + "="*60)
        print("🎉 PREFERENCE PAIR GENERATION COMPLETE")
        print("="*60)
        print(f"Evaluated: {summary['total_evaluations']} responses")
        print(f"Confident: {summary['confident_evaluations']} ({summary['confidence_rate']:.1%})")
        print(f"Preference pairs: {summary['preference_pairs_generated']}")
        print(f"Agreement with heuristic: {summary['agreement_with_heuristic']:.1%}")
        print("\nFiles created:")
        print("  - logprob_evaluations.jsonl")
        print("  - logprob_preference_pairs.jsonl") 
        print("  - logprob_preference_summary.json")
        print("  - logprob_preference_summary.txt")
        print("  - preference_generation.log")
        print("\n✅ Ready for DPO training!")
        
    except Exception as e:
        logger.error(f"❌ Preference generation failed: {e}")
        print(f"\n❌ Preference generation failed: {e}")
        raise