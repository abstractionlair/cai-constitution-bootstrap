#!/usr/bin/env python3
"""
Stage 1 Data Generation: Explicit Instruction Following
Generates training data to improve instruction-following consistency
"""

import json
import torch
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
import yaml
import os
import sys
from tqdm import tqdm

# Configure base directory for RunPod deployment
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/cai-constitution-bootstrap'))

# Add utils to path
sys.path.append(str(BASE_DIR / 'scripts' / 'utils'))

from data_formatter import Stage1DataGenerator, PreferencePair, save_jsonl, create_train_test_split
from model_loader import load_base_model, generate_text, clear_gpu_cache
from metrics import InstructionFollowingEvaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Stage1DataPipeline:
    """Complete data generation pipeline for Stage 1"""
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-32B"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.generator = Stage1DataGenerator()
        self.evaluator = InstructionFollowingEvaluator()
        self.constitution = self.load_constitution()
        
        # Paths
        self.data_dir = BASE_DIR / "data" / "stage1"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🏗️  Stage 1 data pipeline initialized for: {model_name}")
    
    def load_constitution(self) -> Dict[str, Any]:
        """Load constitutional principles"""
        constitution_path = BASE_DIR / "constitution.yaml"
        
        if constitution_path.exists():
            with open(constitution_path, 'r') as f:
                constitution = yaml.safe_load(f)
            logger.info("📜 Constitution loaded")
            return constitution
        else:
            logger.warning("⚠️  Constitution not found, using default principles")
            return {
                'principles': [
                    {'id': 'follow_instruction', 'text': 'Follow the instruction exactly as given'},
                    {'id': 'be_accurate', 'text': 'Provide accurate and factual information'},
                    {'id': 'be_complete', 'text': 'Fully address what was requested'},
                    {'id': 'be_concise', 'text': 'Be concise and avoid unnecessary elaboration'}
                ]
            }
    
    def load_model(self):
        """Load model for data generation"""
        if self.model is None:
            logger.info("📥 Loading model for data generation...")
            # Use higher precision for quality data generation (8-bit instead of 4-bit)
            from unsloth import FastLanguageModel
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.model_name,
                max_seq_length=2048,
                dtype=None,
                load_in_8bit=True,  # Higher precision for better generation quality
            )
            logger.info("✅ Model loaded with 8-bit precision for generation")
    
    def generate_initial_responses(self, instructions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate initial responses to instructions using completion-style prompting"""
        logger.info(f"🤖 Generating initial responses for {len(instructions)} instructions...")
        logger.info("📝 Using completion-style prompting for base model")
        
        self.load_model()
        
        responses = []
        for instruction_data in tqdm(instructions, desc="Generating responses"):
            instruction = instruction_data['instruction']
            
            # CRITICAL FIX: Use completion-style prompting instead of raw instruction
            from data_formatter import CompletionStylePrompts
            completion_prompt = CompletionStylePrompts.create_response_generation_prompt(instruction)
            
            # Generate response using completion prompt
            response = generate_text(
                self.model, 
                self.tokenizer, 
                completion_prompt,
                max_new_tokens=150,
                temperature=0.7
            )
            
            # Clean up response (remove any repeated prompt text)
            response = self._clean_completion_response(response, completion_prompt)
            
            # Store result
            result = {
                **instruction_data,
                'initial_response': response,
                'completion_prompt_used': completion_prompt,
                'timestamp': datetime.now().isoformat()
            }
            responses.append(result)
        
        logger.info(f"✅ Generated {len(responses)} initial responses using completion-style")
        return responses
    
    def _clean_completion_response(self, response: str, prompt: str) -> str:
        """Clean completion response by removing any repeated prompt text"""
        # Remove the prompt if it appears at the start of response
        lines = response.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines and lines that look like they're repeating the prompt pattern
            if line and not any(pattern in line.lower() for pattern in 
                             ['here are examples', 'prompt:', 'response:', 'another', 'would be:']):
                cleaned_lines.append(line)
                break  # Take only the first actual completion
        
        return ' '.join(cleaned_lines).strip() if cleaned_lines else response.strip()
    
    def critique_responses(self, responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Critique responses against Stage 1 principles"""
        logger.info(f"🔍 Critiquing {len(responses)} responses...")
        
        critiqued = []
        # Use constitution from YAML if available, otherwise use defaults
        if self.constitution and 'principles' in self.constitution:
            stage1_principles = [p['text'] for p in self.constitution['principles']][:4]  # Take first 4 for Stage 1
        else:
            stage1_principles = [
                "Follow the instruction exactly as given",
                "Provide accurate and factual information", 
                "Fully address what was requested",
                "Be concise and avoid unnecessary elaboration"
            ]
        
        for response_data in tqdm(responses, desc="Critiquing responses"):
            instruction = response_data['instruction']
            response = response_data['initial_response']
            instruction_type = response_data['instruction_type']
            
            # Evaluate using our metrics
            success, reason, details = self.evaluator.evaluate_response(
                instruction, response, instruction_type
            )
            
            # Generate critique using completion-style prompting
            critique = self._generate_completion_critique(instruction, response, stage1_principles)
            
            # Store critique
            result = {
                **response_data,
                'success': success,
                'evaluation_reason': reason,
                'evaluation_details': details,
                'critique': critique,
                'needs_improvement': not success
            }
            critiqued.append(result)
        
        success_rate = sum(1 for r in critiqued if r['success']) / len(critiqued)
        logger.info(f"📊 Initial success rate: {success_rate:.1%}")
        logger.info(f"🔧 {sum(1 for r in critiqued if not r['success'])} responses need improvement")
        
        return critiqued
    
    def _generate_completion_critique(self, instruction: str, response: str, principles: List[str]) -> str:
        """Generate critique using completion-style prompting"""
        from data_formatter import CompletionStylePrompts
        
        # Use the first principle for focused critique
        main_principle = principles[0] if principles else "Follow the instruction exactly as given"
        
        critique_prompt = CompletionStylePrompts.create_critique_generation_prompt(
            instruction, response, main_principle
        )
        
        critique = generate_text(
            self.model,
            self.tokenizer,
            critique_prompt,
            max_new_tokens=100,
            temperature=0.3
        )
        
        # Clean the critique response
        critique = self._clean_completion_response(critique, critique_prompt)
        return critique
    
    def _create_critique_prompt(self, instruction: str, response: str, principles: List[str]) -> str:
        """DEPRECATED: Old instruction-style critique prompt - replaced by completion-style"""
        # Keep for reference but mark as deprecated
        principles_text = "\n".join(f"- {p}" for p in principles)
        
        prompt = f"""Critique this response according to these principles:

{principles_text}

Instruction: {instruction}
Response: {response}

Critique: Does this response follow the instruction? Is it accurate, complete, and appropriately concise? What could be improved?"""
        
        return prompt
    
    def generate_improvements(self, critiqued_responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate improved responses for failed cases"""
        logger.info("🔧 Generating improved responses...")
        
        improved = []
        failed_responses = [r for r in critiqued_responses if not r['success']]
        
        logger.info(f"📝 Improving {len(failed_responses)} failed responses...")
        
        for response_data in tqdm(failed_responses, desc="Generating improvements"):
            instruction = response_data['instruction']
            original_response = response_data['initial_response']
            critique = response_data['critique']
            
            # Generate improvement using completion-style prompting
            from data_formatter import CompletionStylePrompts
            improvement_prompt = CompletionStylePrompts.create_improvement_generation_prompt(
                instruction, original_response, critique
            )
            
            improved_response = generate_text(
                self.model,
                self.tokenizer,
                improvement_prompt,
                max_new_tokens=150,
                temperature=0.5
            )
            
            # Clean the improved response
            improved_response = self._clean_completion_response(improved_response, improvement_prompt)
            
            # Evaluate the improvement
            success, reason, details = self.evaluator.evaluate_response(
                instruction, improved_response, response_data['instruction_type']
            )
            
            result = {
                **response_data,
                'improved_response': improved_response,
                'improved_success': success,
                'improved_reason': reason
            }
            improved.append(result)
        
        # Also include already successful responses (no improvement needed)
        successful_responses = [r for r in critiqued_responses if r['success']]
        for response_data in successful_responses:
            result = {
                **response_data,
                'improved_response': response_data['initial_response'],  # Same as original
                'improved_success': True,
                'improved_reason': 'Already successful'
            }
            improved.append(result)
        
        improvement_rate = sum(1 for r in improved if r.get('improved_success', False)) / len(improved)
        logger.info(f"📈 Post-improvement success rate: {improvement_rate:.1%}")
        
        return improved
    
    def create_preference_pairs(self, improved_responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create preference pairs for DPO training"""
        logger.info("⚖️  Creating preference pairs...")
        
        preference_pairs = []
        
        for response_data in improved_responses:
            instruction = response_data['instruction']
            original = response_data['initial_response']
            improved = response_data['improved_response']
            
            # Skip if responses are identical
            if original.strip() == improved.strip():
                continue
            
            # Skip if neither response is good
            if not response_data['success'] and not response_data.get('improved_success', False):
                continue
            
            # Determine which is better
            if response_data.get('improved_success', False) and not response_data['success']:
                # Improvement is better
                chosen = improved
                rejected = original
                reason = "Improved response follows instruction better"
            elif response_data['success'] and not response_data.get('improved_success', False):
                # Original is better (rare case)
                chosen = original
                rejected = improved
                reason = "Original response was already good"
            elif response_data['success'] and response_data.get('improved_success', False):
                # Both are good, prefer the improved one
                chosen = improved
                rejected = original
                reason = "Both good, prefer improved version"
            else:
                # Neither is good, skip
                continue
            
            pair = {
                'prompt': instruction,
                'chosen': chosen,
                'rejected': rejected,
                'reason': reason,
                'instruction_type': response_data['instruction_type'],
                'metadata': {
                    'original_success': response_data['success'],
                    'improved_success': response_data.get('improved_success', False),
                    'stage': 1
                }
            }
            preference_pairs.append(pair)
        
        logger.info(f"⚖️  Created {len(preference_pairs)} preference pairs")
        return preference_pairs
    
    def save_data(self, instructions: List[Dict], responses: List[Dict], 
                  critiques: List[Dict], improvements: List[Dict], 
                  preference_pairs: List[Dict]):
        """Save all generated data"""
        logger.info("💾 Saving generated data...")
        
        # Save raw instructions
        save_jsonl(instructions, self.data_dir / "raw_instructions.jsonl")
        
        # CRITICAL FIX: Save training instructions for cross-run leakage prevention
        train_instructions_file = self.data_dir / "train_instructions.jsonl"
        save_jsonl(instructions, train_instructions_file)
        logger.info(f"🔒 Saved {len(instructions)} training instructions for leakage prevention")
        
        # Save initial responses
        save_jsonl(responses, self.data_dir / "initial_responses.jsonl")
        
        # Save critiques
        save_jsonl(critiques, self.data_dir / "critiques.jsonl")
        
        # Save improvements
        save_jsonl(improvements, self.data_dir / "improvements.jsonl")
        
        # Save preference pairs
        save_jsonl(preference_pairs, self.data_dir / "preference_pairs.jsonl")
        
        # Create train/test split for preference pairs
        train_pairs, test_pairs = create_train_test_split(preference_pairs, test_ratio=0.1)
        save_jsonl(train_pairs, self.data_dir / "train_preference_pairs.jsonl")
        save_jsonl(test_pairs, self.data_dir / "test_preference_pairs.jsonl")
        
        # Save summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'model': self.model_name,
            'stage': 1,
            'total_instructions': len(instructions),
            'total_responses': len(responses),
            'total_preference_pairs': len(preference_pairs),
            'train_pairs': len(train_pairs),
            'test_pairs': len(test_pairs),
            'initial_success_rate': sum(1 for r in critiques if r['success']) / len(critiques),
            'improved_success_rate': sum(1 for r in improvements if r.get('improved_success', False)) / len(improvements)
        }
        
        with open(self.data_dir / "generation_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info("✅ All data saved")
        return summary
    
    def run_pipeline(self, total_instructions: int = 1000) -> Dict[str, Any]:
        """Run the complete data generation pipeline"""
        logger.info("🚀 Starting Stage 1 data generation pipeline...")
        logger.info(f"📊 Target: {total_instructions} instructions")
        
        try:
            # Step 1: Generate instructions
            logger.info("📝 Step 1: Generating diverse instructions...")
            # Fix integer division to ensure we get exactly the requested count
            counts = [total_instructions // 4] * 4
            counts[0] += total_instructions % 4  # Add remainder to first category
            
            instructions = self.generator.generate_all_instructions(
                qa_count=counts[0],
                completion_count=counts[1],
                generation_count=counts[2],
                response_count=counts[3]
            )
            
            # Step 2: Generate initial responses
            logger.info("🤖 Step 2: Generating initial responses...")
            responses = self.generate_initial_responses(instructions)
            
            # Step 3: Critique responses
            logger.info("🔍 Step 3: Critiquing responses...")
            critiques = self.critique_responses(responses)
            
            # Step 4: Generate improvements
            logger.info("🔧 Step 4: Generating improvements...")
            improvements = self.generate_improvements(critiques)
            
            # Step 5: Create preference pairs
            logger.info("⚖️  Step 5: Creating preference pairs...")
            preference_pairs = self.create_preference_pairs(improvements)
            
            # Step 6: Save everything
            logger.info("💾 Step 6: Saving data...")
            summary = self.save_data(instructions, responses, critiques, improvements, preference_pairs)
            
            logger.info("🎉 Stage 1 data generation complete!")
            logger.info(f"📊 Generated {len(preference_pairs)} preference pairs")
            logger.info(f"📈 Improvement: {summary['initial_success_rate']:.1%} → {summary['improved_success_rate']:.1%}")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            raise
        
        finally:
            # Clean up
            clear_gpu_cache()


def main():
    """Run Stage 1 data generation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Stage 1 training data")
    parser.add_argument("--model", default="Qwen/Qwen2.5-32B", help="Base model to use")
    parser.add_argument("--count", type=int, default=1000, help="Number of instructions to generate")
    parser.add_argument("--small-test", action="store_true", help="Run small test (100 instructions)")
    
    args = parser.parse_args()
    
    if args.small_test:
        args.count = 100
        logger.info("🧪 Running small test with 100 instructions")
    
    # Create pipeline
    pipeline = Stage1DataPipeline(args.model)
    
    # Run pipeline
    summary = pipeline.run_pipeline(args.count)
    
    # Print final summary
    print("\n" + "="*60)
    print("📊 STAGE 1 DATA GENERATION SUMMARY")
    print("="*60)
    print(f"Model: {summary['model']}")
    print(f"Total Instructions: {summary['total_instructions']}")
    print(f"Initial Success Rate: {summary['initial_success_rate']:.1%}")
    print(f"Improved Success Rate: {summary['improved_success_rate']:.1%}")
    print(f"Preference Pairs: {summary['total_preference_pairs']}")
    print(f"Training Pairs: {summary['train_pairs']}")
    print(f"Test Pairs: {summary['test_pairs']}")
    print("="*60)
    print("\n🚀 Ready for Stage 1 training!")


if __name__ == "__main__":
    main()