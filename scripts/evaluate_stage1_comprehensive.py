#!/usr/bin/env python3
"""
Comprehensive Stage 1 evaluation script with 45 tests across multiple categories
Tests if the Stage 1 model is actually ready for Stage 2 or needs more training
"""

import torch
import time
import json
import logging
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"
SFT_CHECKPOINT = CHECKPOINTS_DIR / "stage1_sft/final"
DPO_CHECKPOINT = CHECKPOINTS_DIR / "stage1_dpo_improved/final"

# Create directories
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

class ComprehensiveEvaluator:
    """Comprehensive evaluation system for Stage 1 model readiness"""
    
    def __init__(self):
        self.base_model = None
        self.sft_model = None 
        self.dpo_model = None
        self.tokenizer = None
        
        # Test categories and scoring
        self.test_categories = {
            'core_instruction_following': 25,
            'format_compliance': 10,
            'edge_cases': 10
        }
        
        # Scoring dimensions (0-2 points each)
        self.scoring_dimensions = ['instruction_following', 'coherence', 'relevance', 'quality']
        self.max_total_score = sum(self.test_categories.values()) * len(self.scoring_dimensions) * 2  # 360 points
        
        logger.info(f"🎯 Initialized comprehensive evaluator (max score: {self.max_total_score})")
        
    def load_models(self):
        """Load base, SFT, and DPO models for comparison"""
        logger.info("🤖 Loading models for comprehensive evaluation...")
        
        # Quantization config for memory efficiency
        bnb_config = BitsAndBytesConfig(
            load_in_8bit=True,
            bnb_8bit_use_double_quant=True,
            bnb_8bit_quant_type="nf8",
            bnb_8bit_compute_dtype=torch.bfloat16
        )
        
        # Load tokenizer
        logger.info("📝 Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-32B",
            trust_remote_code=True,
            padding_side='right'
        )
        
        # Disable chat template - use raw base model
        self.tokenizer.chat_template = None
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        # Load base model
        logger.info("🔵 Loading base model...")
        self.base_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-32B",
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            dtype=torch.bfloat16,
            attn_implementation="flash_attention_2"
        )
        
        # Load SFT model (SEPARATE base + SFT LoRA - don't contaminate base_model!)
        logger.info("🟡 Loading SFT model...")
        sft_base = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-32B",
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            dtype=torch.bfloat16,
            attn_implementation="flash_attention_2"
        )
        self.sft_model = PeftModel.from_pretrained(sft_base, str(SFT_CHECKPOINT))
        
        # Load DPO model (base + merged SFT + DPO LoRA)
        logger.info("🟢 Loading DPO model...")
        # For DPO model, we need to load base, merge SFT, then add DPO
        dpo_base = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-32B",
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            dtype=torch.bfloat16,
            attn_implementation="flash_attention_2"
        )
        
        # Load and merge SFT first
        sft_for_dpo = PeftModel.from_pretrained(dpo_base, str(SFT_CHECKPOINT))
        sft_merged = sft_for_dpo.merge_and_unload()
        
        # Then load DPO adapters on top
        self.dpo_model = PeftModel.from_pretrained(sft_merged, str(DPO_CHECKPOINT))
        
        logger.info("✅ All models loaded successfully")
    
    def generate_response(self, model, instruction: str, max_length: int = 150) -> str:
        """Generate response for an instruction using specified model"""
        # Format exactly like training data
        prompt = f"Instruction: {instruction}\nResponse:"
        
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=256
        ).to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_length,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=1.1
            )
        
        # Decode only the new tokens
        response = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        response = response.strip()
        
        # Clean up response - stop at END token or double newlines
        if "END" in response:
            response = response.split("END")[0].strip()
        if "\n\n" in response:
            response = response.split("\n\n")[0].strip()
        if "Instruction:" in response:
            response = response.split("Instruction:")[0].strip()
            
        return response
    
    def score_response(self, instruction: str, response: str, expected_behavior: str) -> Dict[str, int]:
        """Score a response on all four dimensions (0-2 points each)"""
        scores = {}
        
        # 1. Instruction Following (0-2)
        if not response or len(response.strip()) < 3:
            scores['instruction_following'] = 0
        elif self._follows_instruction_well(instruction, response, expected_behavior):
            scores['instruction_following'] = 2
        else:
            scores['instruction_following'] = 1
            
        # 2. Coherence (0-2)
        if self._is_coherent(response):
            scores['coherence'] = 2
        elif self._is_partially_coherent(response):
            scores['coherence'] = 1
        else:
            scores['coherence'] = 0
            
        # 3. Relevance (0-2)
        if self._is_relevant(instruction, response):
            scores['relevance'] = 2
        elif self._is_partially_relevant(instruction, response):
            scores['relevance'] = 1
        else:
            scores['relevance'] = 0
            
        # 4. Quality (0-2)
        if self._is_high_quality(response):
            scores['quality'] = 2
        elif self._is_decent_quality(response):
            scores['quality'] = 1
        else:
            scores['quality'] = 0
            
        return scores
    
    def _follows_instruction_well(self, instruction: str, response: str, expected_behavior: str) -> bool:
        """Check if response follows the instruction well"""
        instruction_lower = instruction.lower()
        response_lower = response.lower()
        
        # Question answering
        if any(word in instruction_lower for word in ['what', 'who', 'when', 'where', 'why', 'how']):
            # Should provide a direct answer, not ask back
            if '?' in response:
                return False
            if any(phrase in response_lower for phrase in ['i don\'t know', 'not sure', 'unclear']):
                return False
            return len(response.strip()) >= 10
            
        # Completion tasks
        if 'complete' in instruction_lower:
            return len(response.strip()) >= 5 and not response.endswith('...')
            
        # Generation tasks
        if any(word in instruction_lower for word in ['write', 'create', 'generate']):
            return len(response.strip()) >= 20
            
        # Math problems
        if any(word in instruction_lower for word in ['calculate', '+', '-', '*', '/', 'math']):
            # Should contain numbers or mathematical reasoning
            return bool(re.search(r'\d+', response))
            
        # Default: response should be substantive and not deflective
        deflective_phrases = ['i can\'t', 'i don\'t know', 'not sure', 'unclear', 'tell me more']
        if any(phrase in response_lower for phrase in deflective_phrases):
            return False
            
        return len(response.strip()) >= 10
    
    def _is_coherent(self, response: str) -> bool:
        """Check if response is coherent"""
        if not response or len(response.strip()) < 3:
            return False
            
        # Check for repetitive text
        words = response.split()
        if len(words) > 5:
            word_set = set(words)
            if len(word_set) / len(words) < 0.5:  # Too much repetition
                return False
                
        # Check for incomplete sentences
        if response.count('...') > 2:
            return False
            
        # Check for gibberish (too many non-alphabetic characters)
        alpha_ratio = sum(c.isalpha() or c.isspace() for c in response) / len(response)
        if alpha_ratio < 0.7:
            return False
            
        return True
    
    def _is_partially_coherent(self, response: str) -> bool:
        """Check if response is partially coherent"""
        return len(response.strip()) >= 3 and not self._is_coherent(response)
    
    def _is_relevant(self, instruction: str, response: str) -> bool:
        """Check if response is relevant to instruction"""
        # Extract key words from instruction
        instruction_words = set(instruction.lower().split())
        response_words = set(response.lower().split())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'what', 'how', 'when', 'where', 'why'}
        instruction_content = instruction_words - stop_words
        
        if not instruction_content:
            return True  # Can't judge relevance without content words
            
        # Check for word overlap
        overlap = len(instruction_content & response_words) / len(instruction_content)
        return overlap >= 0.3
    
    def _is_partially_relevant(self, instruction: str, response: str) -> bool:
        """Check if response is partially relevant"""
        # Basic topic relevance check
        instruction_words = set(instruction.lower().split())
        response_words = set(response.lower().split())
        
        return len(instruction_words & response_words) > 0
    
    def _is_high_quality(self, response: str) -> bool:
        """Check if response is high quality"""
        if not self._is_coherent(response):
            return False
            
        # Should be substantive (not too short)
        if len(response.strip()) < 15:
            return False
            
        # Should not have obvious errors
        if any(pattern in response.lower() for pattern in ['i can\'t help', 'i don\'t understand', 'please clarify']):
            return False
            
        # Should be well-formed
        if response.count('.') == 0 and response.count('!') == 0 and response.count('?') == 0:
            return False  # No sentence endings
            
        return True
    
    def _is_decent_quality(self, response: str) -> bool:
        """Check if response is decent quality"""
        return self._is_coherent(response) and len(response.strip()) >= 5
    
    def create_test_instructions(self) -> List[Dict[str, Any]]:
        """Create comprehensive test suite with 45 instructions"""
        
        tests = []
        
        # CORE INSTRUCTION FOLLOWING (25 tests)
        core_tests = [
            # Basic QA (5 tests)
            {"instruction": "What is the capital of France?", "category": "core_instruction_following", "expected": "Direct answer: Paris"},
            {"instruction": "How many days are in a year?", "category": "core_instruction_following", "expected": "Direct answer: 365 (or 366)"},
            {"instruction": "What do bees make?", "category": "core_instruction_following", "expected": "Direct answer: honey"},
            {"instruction": "Who wrote Romeo and Juliet?", "category": "core_instruction_following", "expected": "Direct answer: Shakespeare"},
            {"instruction": "What is 12 + 8?", "category": "core_instruction_following", "expected": "Direct answer: 20"},
            
            # Completion tasks (5 tests)
            {"instruction": "Complete this sentence: The sun rises in the", "category": "core_instruction_following", "expected": "Simple completion: east"},
            {"instruction": "Water freezes at", "category": "core_instruction_following", "expected": "Temperature value"},
            {"instruction": "The largest ocean is the", "category": "core_instruction_following", "expected": "Ocean name: Pacific"},
            {"instruction": "Photosynthesis is the process where", "category": "core_instruction_following", "expected": "Process description"},
            {"instruction": "The first person to walk on the moon was", "category": "core_instruction_following", "expected": "Person name: Neil Armstrong"},
            
            # Generation tasks (5 tests)
            {"instruction": "Write a sentence about dogs", "category": "core_instruction_following", "expected": "Complete sentence about dogs"},
            {"instruction": "Create a short description of rain", "category": "core_instruction_following", "expected": "Descriptive text about rain"},
            {"instruction": "Generate an example of a fruit", "category": "core_instruction_following", "expected": "Fruit name"},
            {"instruction": "Write a brief explanation of gravity", "category": "core_instruction_following", "expected": "Simple explanation"},
            {"instruction": "Create a sentence using the word 'happy'", "category": "core_instruction_following", "expected": "Sentence containing 'happy'"},
            
            # How-to questions (5 tests)
            {"instruction": "How do you make tea?", "category": "core_instruction_following", "expected": "Step-by-step process"},
            {"instruction": "How do plants grow?", "category": "core_instruction_following", "expected": "Growth process explanation"},
            {"instruction": "How do you add two numbers?", "category": "core_instruction_following", "expected": "Addition process"},
            {"instruction": "How do cars work?", "category": "core_instruction_following", "expected": "Basic car operation"},
            {"instruction": "How is bread made?", "category": "core_instruction_following", "expected": "Bread-making process"},
            
            # Definition requests (5 tests)
            {"instruction": "Define the word 'ocean'", "category": "core_instruction_following", "expected": "Definition of ocean"},
            {"instruction": "What does 'friendship' mean?", "category": "core_instruction_following", "expected": "Definition of friendship"},
            {"instruction": "Explain what 'photosynthesis' means", "category": "core_instruction_following", "expected": "Photosynthesis definition"},
            {"instruction": "What is 'democracy'?", "category": "core_instruction_following", "expected": "Democracy definition"},
            {"instruction": "Define 'ecosystem'", "category": "core_instruction_following", "expected": "Ecosystem definition"},
        ]
        
        # FORMAT COMPLIANCE (10 tests)
        format_tests = [
            {"instruction": "List three colors", "category": "format_compliance", "expected": "List of exactly 3 colors"},
            {"instruction": "Give me a yes or no answer: Is water wet?", "category": "format_compliance", "expected": "Yes or no response"},
            {"instruction": "Answer in one word: What color is grass?", "category": "format_compliance", "expected": "Single word: green"},
            {"instruction": "Provide a number: How many legs does a spider have?", "category": "format_compliance", "expected": "Number: 8"},
            {"instruction": "Write exactly two sentences about cats", "category": "format_compliance", "expected": "Exactly 2 sentences"},
            {"instruction": "Give a brief answer: What is ice?", "category": "format_compliance", "expected": "Short answer about ice"},
            {"instruction": "Name one example of a mammal", "category": "format_compliance", "expected": "Single mammal name"},
            {"instruction": "Provide a short definition of 'book'", "category": "format_compliance", "expected": "Concise definition"},
            {"instruction": "Answer with a single sentence: Why do birds fly?", "category": "format_compliance", "expected": "One sentence explanation"},
            {"instruction": "Give me the first letter of the alphabet", "category": "format_compliance", "expected": "Single letter: A"},
        ]
        
        # EDGE CASES (10 tests)
        edge_tests = [
            {"instruction": "What is 0 divided by 0?", "category": "edge_cases", "expected": "Handle mathematical impossibility"},
            {"instruction": "How many unicorns exist?", "category": "edge_cases", "expected": "Handle fictional entities"},
            {"instruction": "What will happen tomorrow?", "category": "edge_cases", "expected": "Handle unpredictable future"},
            {"instruction": "Translate 'hello' into a language that doesn't exist", "category": "edge_cases", "expected": "Handle impossible request"},
            {"instruction": "What is the color of silence?", "category": "edge_cases", "expected": "Handle abstract/nonsensical question"},
            {"instruction": "How heavy is a thought?", "category": "edge_cases", "expected": "Handle immeasurable concept"},
            {"instruction": "What does the number 7 taste like?", "category": "edge_cases", "expected": "Handle synesthetic question"},
            {"instruction": "When did time begin?", "category": "edge_cases", "expected": "Handle philosophical/cosmic question"},
            {"instruction": "What is the largest possible number?", "category": "edge_cases", "expected": "Handle infinity concept"},
            {"instruction": "How do you count to negative one?", "category": "edge_cases", "expected": "Handle logical impossibility"},
        ]
        
        # Combine all tests
        tests.extend(core_tests)
        tests.extend(format_tests) 
        tests.extend(edge_tests)
        
        # Add test IDs
        for i, test in enumerate(tests, 1):
            test['test_id'] = i
            
        logger.info(f"📋 Created {len(tests)} test instructions across {len(self.test_categories)} categories")
        return tests
    
    def run_comprehensive_evaluation(self) -> Dict[str, Any]:
        """Run the complete evaluation suite"""
        logger.info("🚀 Starting comprehensive Stage 1 evaluation")
        
        # Create test suite
        test_instructions = self.create_test_instructions()
        
        # Results storage
        results = {
            'test_results': [],
            'model_scores': {'base': 0, 'sft': 0, 'dpo': 0},
            'category_scores': {
                'base': {cat: 0 for cat in self.test_categories},
                'sft': {cat: 0 for cat in self.test_categories},
                'dpo': {cat: 0 for cat in self.test_categories}
            },
            'dimension_scores': {
                'base': {dim: 0 for dim in self.scoring_dimensions},
                'sft': {dim: 0 for dim in self.scoring_dimensions},
                'dpo': {dim: 0 for dim in self.scoring_dimensions}
            }
        }
        
        # Run tests
        for i, test in enumerate(test_instructions, 1):
            logger.info(f"🧪 Running test {i}/{len(test_instructions)}: {test['category']}")
            
            instruction = test['instruction']
            expected = test['expected']
            category = test['category']
            
            # Generate responses from all models
            logger.info(f"   Testing: {instruction[:50]}...")
            
            base_response = self.generate_response(self.base_model, instruction)
            sft_response = self.generate_response(self.sft_model, instruction)
            dpo_response = self.generate_response(self.dpo_model, instruction)
            
            # Score all responses
            base_scores = self.score_response(instruction, base_response, expected)
            sft_scores = self.score_response(instruction, sft_response, expected)
            dpo_scores = self.score_response(instruction, dpo_response, expected)
            
            # Store detailed results
            test_result = {
                'test_id': test['test_id'],
                'instruction': instruction,
                'category': category,
                'expected_behavior': expected,
                'responses': {
                    'base': base_response,
                    'sft': sft_response,
                    'dpo': dpo_response
                },
                'scores': {
                    'base': base_scores,
                    'sft': sft_scores,
                    'dpo': dpo_scores
                }
            }
            
            results['test_results'].append(test_result)
            
            # Accumulate scores
            for model in ['base', 'sft', 'dpo']:
                model_scores = test_result['scores'][model]
                total_score = sum(model_scores.values())
                
                results['model_scores'][model] += total_score
                results['category_scores'][model][category] += total_score
                
                for dim, score in model_scores.items():
                    results['dimension_scores'][model][dim] += score
                    
            # Progress update
            if i % 5 == 0:
                logger.info(f"   ✅ Completed {i}/{len(test_instructions)} tests")
        
        # Calculate percentages
        results['model_percentages'] = {
            model: (score / self.max_total_score) * 100 
            for model, score in results['model_scores'].items()
        }
        
        logger.info("✅ Comprehensive evaluation complete")
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive evaluation report"""
        
        report = f"""
# Stage 1 Comprehensive Evaluation Report
Generated: {datetime.now().isoformat()}
Total Tests: {len(results['test_results'])}
Maximum Possible Score: {self.max_total_score} points

## Overall Results

### Model Performance Summary
"""
        
        for model in ['base', 'sft', 'dpo']:
            score = results['model_scores'][model]
            percentage = results['model_percentages'][model]
            report += f"- **{model.upper()} Model**: {score}/{self.max_total_score} points ({percentage:.1f}%)\n"
        
        # Decision criteria
        dpo_percentage = results['model_percentages']['dpo']
        
        report += f"\n## Stage 2 Readiness Decision\n"
        
        if dpo_percentage >= 75:
            decision = "✅ **READY FOR STAGE 2**"
            reasoning = "DPO model shows strong instruction following across all test categories."
        elif dpo_percentage >= 50:
            decision = "⚠️ **NEEDS MORE TRAINING**" 
            reasoning = "DPO model shows improvement but insufficient for Stage 2 progression."
        else:
            decision = "❌ **TRAINING FAILED**"
            reasoning = "DPO model shows poor instruction following. Major issues need addressing."
            
        report += f"{decision}\n\n**Reasoning**: {reasoning}\n"
        
        # Category breakdown
        report += f"\n## Performance by Category\n"
        
        for category, max_tests in self.test_categories.items():
            max_score = max_tests * len(self.scoring_dimensions) * 2
            report += f"\n### {category.replace('_', ' ').title()}\n"
            
            for model in ['base', 'sft', 'dpo']:
                score = results['category_scores'][model][category]
                percentage = (score / max_score) * 100
                report += f"- {model.upper()}: {score}/{max_score} ({percentage:.1f}%)\n"
        
        # Dimension analysis
        report += f"\n## Performance by Scoring Dimension\n"
        
        for dimension in self.scoring_dimensions:
            max_score = len(results['test_results']) * 2  # 2 points max per test
            report += f"\n### {dimension.replace('_', ' ').title()}\n"
            
            for model in ['base', 'sft', 'dpo']:
                score = results['dimension_scores'][model][dimension]
                percentage = (score / max_score) * 100
                report += f"- {model.upper()}: {score}/{max_score} ({percentage:.1f}%)\n"
        
        # Sample test results
        report += f"\n## Sample Test Results\n"
        
        for category in self.test_categories:
            category_tests = [t for t in results['test_results'] if t['category'] == category]
            if category_tests:
                sample_test = category_tests[0]  # First test of each category
                report += f"\n### {category.replace('_', ' ').title()} Example\n"
                report += f"**Instruction**: {sample_test['instruction']}\n\n"
                
                for model in ['base', 'sft', 'dpo']:
                    response = sample_test['responses'][model]
                    scores = sample_test['scores'][model]
                    total_score = sum(scores.values())
                    
                    report += f"**{model.upper()}** ({total_score}/8 pts): {response}\n"
                    score_details = ", ".join([f"{dim}: {score}/2" for dim, score in scores.items()])
                    report += f"  *Scores: {score_details}*\n\n"
        
        # Recommendations
        report += f"\n## Recommendations\n"
        
        if dpo_percentage >= 75:
            report += """
- ✅ Proceed to Stage 2 (Implicit Instructions)
- Use this DPO model as the base for Stage 2 data generation
- Monitor performance on implicit instruction types in Stage 2
"""
        elif dpo_percentage >= 50:
            report += """
- 🔄 Additional training recommended before Stage 2
- Consider generating more SFT data (current: 200 examples)
- Consider generating more preference pairs (current: 100 pairs)  
- Focus on categories with lowest scores
- Re-evaluate after additional training
"""
        else:
            report += """
- ❌ Significant issues need addressing before Stage 2
- Review training data quality and diversity
- Check model loading and training procedures
- Consider different hyperparameters or training approach
- Investigate poor performance categories specifically
"""
        
        return report
    
    def cleanup_models(self):
        """Clean up model memory"""
        logger.info("🧹 Cleaning up models...")
        
        if self.base_model is not None:
            del self.base_model
        if self.sft_model is not None:
            del self.sft_model
        if self.dpo_model is not None:
            del self.dpo_model
        if self.tokenizer is not None:
            del self.tokenizer
            
        torch.cuda.empty_cache()
        logger.info("✅ Memory cleanup complete")

def main():
    """Main evaluation function"""
    logger.info("🎯 Starting Stage 1 Comprehensive Evaluation")
    
    evaluator = ComprehensiveEvaluator()
    
    try:
        # Load all models
        evaluator.load_models()
        
        # Run comprehensive evaluation
        results = evaluator.run_comprehensive_evaluation()
        
        # Generate report
        report = evaluator.generate_report(results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = ARTIFACTS_DIR / f"stage1_comprehensive_evaluation_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        # Save report
        report_file = ARTIFACTS_DIR / f"stage1_evaluation_report_{timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(report)
            
        # Print summary
        print(report)
        
        logger.info(f"💾 Results saved to {results_file}")
        logger.info(f"📋 Report saved to {report_file}")
        
        # Return key metrics
        dpo_percentage = results['model_percentages']['dpo']
        if dpo_percentage >= 75:
            logger.info("🎉 STAGE 2 READY: DPO model passed comprehensive evaluation")
        elif dpo_percentage >= 50:
            logger.info("⚠️ MORE TRAINING NEEDED: DPO model shows improvement but needs work")
        else:
            logger.info("❌ TRAINING FAILED: DPO model shows poor instruction following")
            
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        raise
    finally:
        evaluator.cleanup_models()

if __name__ == "__main__":
    main()