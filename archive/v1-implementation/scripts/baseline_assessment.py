#!/usr/bin/env python3
"""
Baseline Assessment for Qwen-2.5-32B Base Model
CRITICAL: Run this FIRST to establish what the model can already do
"""

import json
import torch
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import sys

# Configure base directory for RunPod deployment
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/cai-constitution-bootstrap'))

# Add utils to path
sys.path.append(str(BASE_DIR / 'scripts' / 'utils'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaselineAssessment:
    """Test base model capabilities before any training"""
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-32B"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.results = {}
        
        # Ensure we're using the TRUE base model, not instruct
        if "Instruct" in model_name:
            logger.warning("⚠️  Using Instruct model! Switch to base model for honest assessment.")
        
        logger.info(f"🧪 Initializing baseline assessment for: {model_name}")
        logger.info("📝 Using raw instructions to measure baseline instruction-following")
        
    def load_model(self):
        """Load the base model for testing"""
        logger.info(f"📥 Loading base model: {self.model_name}")
        
        # Check GPU availability
        if torch.cuda.is_available():
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"🎮 GPU: {torch.cuda.get_device_name()}")
            logger.info(f"💾 GPU Memory: {gpu_memory:.1f} GB")
            
            logger.info("Using 8-bit precision for consistency with evaluation")
        else:
            logger.warning("No GPU available, using CPU (this will be slow)")
        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with 8-bit precision (consistent with evaluation)
            if torch.cuda.is_available():
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    load_in_8bit=True,
                    device_map="auto",
                    low_cpu_mem_usage=True,
                )
            else:
                # Fallback for CPU
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float32,
                    device_map="auto",
                    low_cpu_mem_usage=True,
                )
            
            logger.info("✅ Model loaded successfully")
            
            # Print memory usage
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1e9
                reserved = torch.cuda.memory_reserved() / 1e9
                logger.info(f"🎮 GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise
    
    def generate_response(self, prompt: str, max_new_tokens: int = 50) -> str:
        """Generate response from the model"""
        try:
            # Tokenize
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True)
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=0.1,  # Low temperature for consistent testing
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            
            # Decode (remove input tokens)
            input_length = inputs["input_ids"].shape[1]
            generated_tokens = outputs[0][input_length:]
            response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Generation failed for prompt '{prompt}': {e}")
            return ""
    
    def get_test_prompts(self) -> Dict[str, List[str]]:
        """Get test prompts organized by category"""
        return {
            'completions': [
                "The capital of France is",
                "Water boils at",
                "2 + 2 equals",
                "The sun is a",
                "Python is a programming",
                "Shakespeare wrote Romeo and",
                "The largest planet is",
                "Ice melts at",
                "Gravity causes objects to",
                "The speed of light is",
            ],
            
            'questions': [
                "What is the capital of France?",
                "How does photosynthesis work?",
                "Why is the sky blue?",
                "When was World War II?",
                "Who invented the telephone?",
                "What causes rain?",
                "How many sides does a triangle have?",
                "What is DNA?",
                "Where is the Great Wall of China?",
                "What is gravity?",
            ],
            
            'instructions': [
                "Answer this question: What is gravity?",
                "Complete the following: The moon orbits",
                "Tell me about the water cycle.",
                "List three primary colors.",
                "Explain what DNA is.",
                "Define photosynthesis.",
                "Describe how rain forms.",
                "Answer: Who wrote Romeo and Juliet?",
                "Complete this sentence: Water freezes at",
                "Tell me the capital of Japan.",
            ],
            
            'commands': [
                "Write a sentence about dogs.",
                "Generate a fact about space.",
                "Create a short description of rain.",
                "Produce a statement about mathematics.",
                "Output information about computers.",
                "Write one fact about gravity.",
                "Generate a sentence about the ocean.",
                "Create a description of trees.",
                "Produce information about the sun.",
                "Write about the human heart.",
            ]
        }
    
    def evaluate_response(self, prompt: str, response: str, category: str) -> Tuple[bool, str]:
        """Evaluate if response is successful for the category"""
        
        if not response or len(response) < 3:
            return False, "Empty or too short response"
        
        response_lower = response.lower()
        prompt_lower = prompt.lower()
        
        if category == 'completions':
            # Should complete the sentence sensibly, not repeat the prompt
            if prompt.rstrip() in response:
                return False, "Just repeated the prompt"
            if len(response) > 100:
                return False, "Response too long for completion"
            if response.endswith('?'):
                return False, "Completion ended with question"
            return True, "Completed appropriately"
        
        elif category == 'questions':
            # Should provide an answer, not ask more questions
            if response.count('?') > response.count('.'):
                return False, "Responded with more questions"
            if any(phrase in response_lower for phrase in ['what is', 'how does', 'why is', 'when was']):
                return False, "Continued with more questions"
            if len(response) < 10:
                return False, "Answer too short"
            return True, "Provided an answer"
        
        elif category == 'instructions':
            # Should follow the instruction, not ignore it
            
            # Specific instruction checks
            if 'gravity' in prompt_lower:
                if 'gravity' in response_lower or 'force' in response_lower:
                    return True, "Addressed gravity question"
                return False, "Didn't address gravity"
            
            if 'moon orbits' in prompt_lower:
                if 'earth' in response_lower:
                    return True, "Completed moon orbit"
                return False, "Didn't complete appropriately"
            
            if 'three primary colors' in prompt_lower:
                color_count = sum(1 for color in ['red', 'blue', 'green', 'yellow'] if color in response_lower)
                if color_count >= 2:
                    return True, "Listed colors"
                return False, "Didn't list colors"
            
            if 'romeo and juliet' in prompt_lower:
                if 'shakespeare' in response_lower:
                    return True, "Answered Shakespeare question"
                return False, "Didn't answer correctly"
            
            if 'water freezes' in prompt_lower:
                if any(temp in response_lower for temp in ['0', 'zero', '32', 'celsius', 'fahrenheit']):
                    return True, "Gave freezing point"
                return False, "Didn't give temperature"
            
            if 'capital of japan' in prompt_lower:
                if 'tokyo' in response_lower:
                    return True, "Answered Japan capital"
                return False, "Didn't answer correctly"
            
            # Generic instruction following
            if len(response) < 10:
                return False, "Response too short for instruction"
            
            return True, "Attempted to follow instruction"
        
        elif category == 'commands':
            # Should generate content as commanded
            
            if 'dogs' in prompt_lower and 'dog' not in response_lower:
                return False, "Didn't write about dogs"
            
            if 'space' in prompt_lower and not any(word in response_lower for word in ['space', 'star', 'planet', 'universe']):
                return False, "Didn't write about space"
            
            if 'rain' in prompt_lower and 'rain' not in response_lower:
                return False, "Didn't describe rain"
            
            if 'mathematics' in prompt_lower and not any(word in response_lower for word in ['math', 'number', 'equation', 'calculate']):
                return False, "Didn't write about mathematics"
            
            if 'computers' in prompt_lower and not any(word in response_lower for word in ['computer', 'digital', 'data', 'technology']):
                return False, "Didn't write about computers"
            
            if len(response) < 15:
                return False, "Response too short for command"
            
            return True, "Generated content as commanded"
        
        return False, "Unknown category"
    
    def test_category(self, category: str, prompts: List[str]) -> Dict[str, Any]:
        """Test all prompts in a category"""
        logger.info(f"🧪 Testing {category} ({len(prompts)} prompts)...")
        
        results = []
        successes = 0
        
        for i, prompt in enumerate(prompts):
            logger.info(f"  Testing {i+1}/{len(prompts)}: {prompt[:50]}...")
            
            # CORRECT METHODOLOGY: Use raw instructions to measure baseline capability
            response = self.generate_response(prompt)
            success, reason = self.evaluate_response(prompt, response, category)
            
            if success:
                successes += 1
            
            result = {
                'prompt': prompt,
                'response': response,
                'success': success,
                'reason': reason
            }
            results.append(result)
            
            # Log interesting failures
            if not success and len(response) > 0:
                logger.debug(f"    ❌ {reason}: '{response[:100]}...'")
        
        success_rate = successes / len(prompts)
        logger.info(f"  ✅ {category}: {success_rate:.1%} ({successes}/{len(prompts)})")
        
        return {
            'success_rate': success_rate,
            'successes': successes,
            'total': len(prompts),
            'examples': results
        }
    
    def run_assessment(self) -> Dict[str, Any]:
        """Run complete baseline assessment"""
        logger.info("🚀 Starting baseline assessment...")
        
        # Load model if not already loaded
        if self.model is None:
            self.load_model()
        
        # Get test prompts
        test_prompts = self.get_test_prompts()
        
        # Test each category
        category_results = {}
        overall_successes = 0
        overall_total = 0
        
        for category, prompts in test_prompts.items():
            result = self.test_category(category, prompts)
            category_results[category] = result
            
            overall_successes += result['successes']
            overall_total += result['total']
        
        overall_success_rate = overall_successes / overall_total
        
        # Compile final results
        self.results = {
            'model': self.model_name,
            'timestamp': datetime.now().isoformat(),
            'methodology': {
                'approach': 'Raw instructions used to measure baseline instruction-following capability',
                'documentation': 'specs/stage_1_evaluation_philosophy.md',
                'note': 'Expected low success rate for base model - this is not a failure but baseline measurement'
            },
            'categories': category_results,
            'overall_success_rate': overall_success_rate,
            'overall_successes': overall_successes,
            'overall_total': overall_total
        }
        
        # Print summary
        logger.info("📊 BASELINE ASSESSMENT RESULTS:")
        logger.info("-" * 50)
        for category, result in category_results.items():
            logger.info(f"{category.capitalize():12}: {result['success_rate']:.1%} ({result['successes']}/{result['total']})")
        logger.info("-" * 50)
        logger.info(f"{'Overall':12}: {overall_success_rate:.1%} ({overall_successes}/{overall_total})")
        
        return self.results
    
    def save_results(self, filepath: str = None):
        """Save results to JSON file"""
        if filepath is None:
            # Create results directory
            results_dir = BASE_DIR / "results"
            results_dir.mkdir(exist_ok=True)
            filepath = results_dir / "baseline_assessment.json"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"💾 Results saved to: {filepath}")
    
    def print_examples(self, category: str = None, num_examples: int = 3):
        """Print example results for inspection"""
        if not self.results:
            logger.error("No results to display. Run assessment first.")
            return
        
        categories = [category] if category else self.results['categories'].keys()
        
        for cat in categories:
            logger.info(f"\n📝 Example {cat} results:")
            examples = self.results['categories'][cat]['examples']
            
            for i, example in enumerate(examples[:num_examples]):
                status = "✅" if example['success'] else "❌"
                logger.info(f"  {status} Prompt: {example['prompt']}")
                logger.info(f"     Response: {example['response'][:100]}{'...' if len(example['response']) > 100 else ''}")
                logger.info(f"     Reason: {example['reason']}")
                logger.info("")


def main():
    """Run baseline assessment"""
    # Set up assessment
    assessment = BaselineAssessment()
    
    # Run assessment
    try:
        results = assessment.run_assessment()
        
        # Save results
        assessment.save_results()
        
        # Show examples
        assessment.print_examples(num_examples=2)
        
        logger.info("🎉 Baseline assessment complete!")
        logger.info("💡 Now we know what the base model can actually do.")
        logger.info("🚀 Proceed with Stage 1 training to improve these scores!")
        
    except Exception as e:
        logger.error(f"❌ Assessment failed: {e}")
        raise
    
    finally:
        # Clean up GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


if __name__ == "__main__":
    main()