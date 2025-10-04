#!/usr/bin/env python3
"""
Stage 1 Response Generation with Checkpoint Review
Generates responses from base model for all instructions
"""

import json
import sys
import os
import torch
from pathlib import Path
from datetime import datetime
import logging
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))
sys.path.insert(0, str(BASE_DIR / 'scripts' / 'utils'))

def save_jsonl(data, filepath):
    """Save data in JSONL format"""
    with open(filepath, 'w') as f:
        for item in data:
            json.dump(item, f)
            f.write('\n')

def create_artifact_summary(responses, output_file):
    """Create human-readable summary of responses"""
    
    # Basic stats
    total = len(responses)
    by_type = Counter(r['instruction_type'] for r in responses)
    
    # Evaluate responses using basic heuristics
    evaluated = []
    for resp in responses:
        response_text = resp['response'].strip()
        success = evaluate_response_quality(resp['instruction'], response_text, resp['instruction_type'])
        evaluated.append({**resp, 'success': success})
    
    success_rate = sum(1 for r in evaluated if r['success']) / total
    
    summary = f"""📊 Response Generation Summary
================================

Total Responses: {total}
Overall Success Rate: {success_rate:.1%}

Distribution by Type:
"""
    
    for inst_type, count in by_type.items():
        type_success = sum(1 for r in evaluated if r['instruction_type'] == inst_type and r['success']) / count
        summary += f"  {inst_type}: {count} ({type_success:.1%} success)\n"
    
    summary += f"""
Sample Successful Responses:
----------------------------
"""
    
    successful = [r for r in evaluated if r['success']][:5]
    for i, resp in enumerate(successful):
        summary += f"""
{i+1}. [{resp['instruction_type']}] {resp['instruction'][:60]}...
   Response: {resp['response'][:100]}...
"""
    
    summary += f"""
Sample Failed Responses:
-----------------------
"""
    
    failed = [r for r in evaluated if not r['success']][:3]
    for i, resp in enumerate(failed):
        summary += f"""
{i+1}. [{resp['instruction_type']}] {resp['instruction'][:60]}...
   Response: {resp['response'][:100]}...
"""
    
    with open(output_file, 'w') as f:
        f.write(summary)
    
    return evaluated, success_rate

def evaluate_response_quality(instruction, response, inst_type):
    """Basic heuristic evaluation of response quality"""
    
    if not response or len(response.strip()) < 3:
        return False
        
    response_lower = response.lower().strip()
    instruction_lower = instruction.lower().strip()
    
    # General bad patterns
    bad_patterns = [
        'i cannot', 'i can\'t', 'as an ai', 'i\'m sorry',
        'i don\'t know', 'i am not', 'unable to'
    ]
    
    if any(pattern in response_lower for pattern in bad_patterns):
        return False
    
    # Just repeating the instruction
    if instruction.rstrip(':?.!').lower() in response_lower:
        return False
    
    # Type-specific checks
    if inst_type == 'completion':
        # Should actually complete, not ask questions
        if response.count('?') > response.count('.'):
            return False
        if len(response) > 150:  # Too long for completion
            return False
            
    elif inst_type == 'qa':
        # Should provide answer, not more questions
        if response.startswith(('what', 'how', 'why', 'when', 'where')):
            return False
        if len(response) < 5:  # Too short for answer
            return False
            
    elif inst_type == 'generation':
        # Should generate content, not refuse
        if len(response) < 10:
            return False
            
    elif inst_type == 'response':
        # Should respond appropriately
        if len(response) < 8:
            return False
    
    return True

def generate_responses():
    """Generate responses for all instructions"""
    
    logger.info("🚀 Starting response generation phase")
    logger.info(f"📁 Artifacts directory: {ARTIFACTS_DIR}")
    
    # Load instructions
    instructions_file = ARTIFACTS_DIR / "instructions.jsonl"
    if not instructions_file.exists():
        raise FileNotFoundError(f"Instructions file not found: {instructions_file}")
    
    with open(instructions_file) as f:
        instructions = [json.loads(line) for line in f]
    
    logger.info(f"📝 Loaded {len(instructions)} instructions")
    
    # Load base model
    logger.info("📥 Loading Qwen-2.5-32B base model (8-bit)...")
    from transformers import AutoModelForCausalLM, AutoTokenizer
    
    model_name = "Qwen/Qwen2.5-32B"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        load_in_8bit=True,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    
    logger.info(f"✅ Model loaded. GPU memory: {torch.cuda.max_memory_allocated()/1e9:.1f}GB")
    
    # Generate responses with progress tracking
    from data_formatter import CompletionStylePrompts
    
    responses = []
    batch_size = 1  # Conservative for 32B model
    
    logger.info(f"🔄 Generating responses (batch_size={batch_size})...")
    
    for i, instruction_data in enumerate(instructions):
        if i % 10 == 0:
            logger.info(f"Progress: {i}/{len(instructions)} ({i/len(instructions)*100:.1f}%)")
            logger.info(f"GPU memory: {torch.cuda.memory_allocated()/1e9:.1f}GB")
        
        instruction = instruction_data['instruction']
        inst_type = instruction_data['instruction_type']
        
        # Use completion-style prompting for base model
        formatted_prompt = CompletionStylePrompts.create_response_generation_prompt(instruction)
        
        # Tokenize
        inputs = tokenizer(formatted_prompt, return_tensors='pt', truncation=True, max_length=1800)
        inputs = inputs.to(model.device)
        
        # Generate
        with torch.no_grad():
            try:
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=120,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id
                )
                
                # Extract just the new tokens
                new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
                response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
                
                responses.append({
                    'id': instruction_data.get('id', f"inst_{i}"),
                    'instruction': instruction,
                    'response': response,
                    'instruction_type': inst_type,
                    'raw_prompt': instruction_data.get('raw_prompt', ''),
                    'formatted_prompt': formatted_prompt
                })
                
            except Exception as e:
                logger.warning(f"Failed to generate response for instruction {i}: {e}")
                responses.append({
                    'id': instruction_data.get('id', f"inst_{i}"),
                    'instruction': instruction,
                    'response': f"[ERROR: {str(e)}]",
                    'instruction_type': inst_type,
                    'raw_prompt': instruction_data.get('raw_prompt', ''),
                    'formatted_prompt': formatted_prompt
                })
                
        # Clear cache periodically
        if i % 25 == 0 and i > 0:
            torch.cuda.empty_cache()
    
    logger.info("✅ Response generation complete!")
    logger.info(f"Final GPU memory: {torch.cuda.max_memory_allocated()/1e9:.1f}GB")
    
    # Save responses
    responses_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    save_jsonl(responses, responses_file)
    logger.info(f"💾 Saved {len(responses)} responses to {responses_file}")
    
    # Create summary
    summary_file = ARTIFACTS_DIR / "response_summary.txt"
    evaluated_responses, success_rate = create_artifact_summary(responses, summary_file)
    
    # Save evaluated responses
    eval_file = ARTIFACTS_DIR / "initial_responses_evaluated.jsonl"
    save_jsonl(evaluated_responses, eval_file)
    
    logger.info(f"📊 Overall success rate: {success_rate:.1%}")
    logger.info(f"📋 Summary saved to: {summary_file}")
    
    # Clear model from memory
    del model
    torch.cuda.empty_cache()
    
    return evaluated_responses, success_rate

if __name__ == "__main__":
    try:
        responses, success_rate = generate_responses()
        
        print("\n" + "="*60)
        print("🎉 RESPONSE GENERATION COMPLETE")
        print("="*60)
        print(f"Generated: {len(responses)} responses")
        print(f"Success rate: {success_rate:.1%}")
        print(f"Artifacts: {ARTIFACTS_DIR}")
        print("\nFiles created:")
        print("  - initial_responses.jsonl")
        print("  - initial_responses_evaluated.jsonl") 
        print("  - response_summary.txt")
        print("\n✅ Ready for review!")
        
    except Exception as e:
        logger.error(f"❌ Response generation failed: {e}")
        raise