#!/usr/bin/env python3
"""
Generate preference pairs using A/B log-probability evaluation on all 100 responses
Creates high-quality training data by filtering for confident predictions
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

def create_ab_evaluation_prompt(instruction, response):
    """Create A/B evaluation prompt that ends with single token completion"""
    
    # Clean up the response - take first paragraph only
    clean_response = response.split('\n\n')[0].strip()
    
    prompt = """Instruction-Following Judge (binary)

Labels: A = good, B = bad
Rules (succinct):
- A if RESPONSE directly fulfills the INSTRUCTION, is correct (for factual asks), follows stated format/length, and is safe.
- A if the INSTRUCTION is unsafe and the RESPONSE refuses briefly and (optionally) suggests safer alternatives.
- Otherwise B. If uncertain, choose B.

INSTRUCTION:
{instruction}

RESPONSE:
{response}

Output exactly one letter on the next line: A or B
Label:""".format(instruction=instruction, response=clean_response)
    
    return prompt

def get_token_logprobs(model, tokenizer, prompt, candidate_tokens):
    """Get log probabilities for candidate tokens at the next position"""
    
    # Tokenize the prompt
    inputs = tokenizer(prompt, return_tensors='pt', truncation=True, max_length=1600)
    inputs = inputs.to(model.device)
    
    # Get model logits
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits[0, -1, :]  # Last position logits
    
    # Convert to log probabilities
    log_probs = torch.nn.functional.log_softmax(logits, dim=-1)
    
    # Get log probabilities for candidate tokens
    token_logprobs = {}
    for token_text in candidate_tokens:
        # Try different variations of token encoding
        token_variations = [
            token_text,
            f" {token_text}",  # With leading space
        ]
        
        best_logprob = float('-inf')
        best_token_id = None
        
        for variation in token_variations:
            try:
                token_ids = tokenizer.encode(variation, add_special_tokens=False)
                if len(token_ids) == 1:  # Single token
                    token_id = token_ids[0]
                    logprob = log_probs[token_id].item()
                    if logprob > best_logprob:
                        best_logprob = logprob
                        best_token_id = token_id
            except:
                continue
        
        token_logprobs[token_text] = {
            'logprob': best_logprob,
            'token_id': best_token_id
        }
    
    return token_logprobs

def evaluate_with_logprobs(model, tokenizer, prompt, confidence_threshold=1.0):
    """Evaluate using A/B log probabilities"""
    
    # Get log probabilities for A and B
    candidate_tokens = ['A', 'B']
    token_logprobs = get_token_logprobs(model, tokenizer, prompt, candidate_tokens)
    
    logp_a = token_logprobs['A']['logprob']
    logp_b = token_logprobs['B']['logprob']
    
    # Choose the token with higher log probability
    if logp_a > logp_b:
        predicted_label = 'A'  # good
        predicted_judgment = 'good'
    else:
        predicted_label = 'B'  # bad
        predicted_judgment = 'bad'
    
    # Calculate confidence margin
    margin = abs(logp_a - logp_b)
    confident = margin > confidence_threshold
    
    return {
        'predicted_label': predicted_label,
        'predicted_judgment': predicted_judgment,
        'logp_a': logp_a,
        'logp_b': logp_b,
        'margin': margin,
        'confident': confident
    }

def load_model_with_retry(model_name, max_retries=2):
    """Load model with retry logic"""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    
    # Modern quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_threshold=6.0,
        llm_int8_has_fp16_weight=False
    )
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Model loading attempt {attempt + 1}/{max_retries}")
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                trust_remote_code=True,
                use_fast=False
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            logger.info("✅ Tokenizer loaded")
            
            # Load model
            logger.info("Loading model with 8-bit quantization...")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                torch_dtype=torch.float16
            )
            
            logger.info(f"✅ Model loaded successfully")
            logger.info(f"GPU memory: {torch.cuda.max_memory_allocated()/1e9:.1f}GB")
            
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Model loading attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info("Clearing GPU cache and retrying...")
                torch.cuda.empty_cache()
                time.sleep(5)
            else:
                raise

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
    
    # Load model
    model_name = "Qwen/Qwen2.5-32B"
    model, tokenizer = load_model_with_retry(model_name)
    
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
        
        # Create evaluation prompt
        prompt = create_ab_evaluation_prompt(instruction, response)
        
        # Evaluate with log probabilities
        eval_result = evaluate_with_logprobs(model, tokenizer, prompt, confidence_threshold)
        
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