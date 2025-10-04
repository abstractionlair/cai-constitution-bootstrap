#!/usr/bin/env python3
"""
Definitive test of base Qwen2.5-32B model capabilities.
This script tests the raw base model to establish baseline instruction-following ability.
We test with multiple formats to understand what the base model can and cannot do.
"""

import torch
import json
import logging
from pathlib import Path
from datetime import datetime
import sys
import os
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

from utils.clean_model_loader import CleanModelLoader

class BaseModelTester:
    """Test raw base model capabilities definitively"""
    
    def __init__(self):
        """Initialize tester"""
        self.model = None
        self.tokenizer = None
        self.loader = None
        self.provenance = None
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'model': 'Qwen/Qwen2.5-32B',
            'test_categories': {},
            'summary': {}
        }

    def load_base_model(self):
        """Load the raw base model via CleanModelLoader"""
        logger.info("🤖 Loading RAW Qwen2.5-32B base model (no fine-tuning)...")

        # Use CleanModelLoader for guaranteed contamination-free loading
        self.loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
        self.model, self.tokenizer, self.provenance = self.loader.load()

        logger.info("✅ Raw base model loaded successfully via CleanModelLoader")
        logger.info(f"📋 Loader version: {self.provenance['loader_version'][:8]}")
    
    def generate_completion(self, prompt: str, max_new_tokens: int = 50) -> str:
        """Generate a raw completion from the base model via CleanModelLoader"""
        return self.loader.generate(
            self.model,
            self.tokenizer,
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=0.1,  # Low temperature for consistent results
            do_sample=True
        )
    
    def test_raw_completion(self):
        """Test 1: Raw text completion (what base models are trained for)"""
        logger.info("\n📝 TEST 1: Raw Text Completion")
        logger.info("Testing what base models do best - complete text")
        
        test_cases = [
            {
                'prompt': "The capital of France is",
                'expected_contains': ['Paris'],
                'description': 'Simple factual completion'
            },
            {
                'prompt': "Water freezes at",
                'expected_contains': ['0', 'degrees', 'Celsius', '32', 'Fahrenheit'],
                'description': 'Scientific fact completion'
            },
            {
                'prompt': "The sun rises in the",
                'expected_contains': ['east'],
                'description': 'Common knowledge completion'
            },
            {
                'prompt': "2 + 2 =",
                'expected_contains': ['4'],
                'description': 'Math completion'
            },
            {
                'prompt': "Once upon a time, there was a",
                'expected_contains': [],  # Any story continuation is valid
                'description': 'Story continuation'
            }
        ]
        
        results = []
        for case in test_cases:
            response = self.generate_completion(case['prompt'], max_new_tokens=20)
            
            # Check if response contains expected content
            success = True
            if case['expected_contains']:
                success = any(exp.lower() in response.lower() for exp in case['expected_contains'])
            
            result = {
                'prompt': case['prompt'],
                'response': response,
                'success': success,
                'description': case['description']
            }
            results.append(result)
            
            logger.info(f"  {case['description']}:")
            logger.info(f"    Prompt: {case['prompt']}")
            logger.info(f"    Response: {response}")
            logger.info(f"    Success: {'✅' if success else '❌'}")
        
        self.results['test_categories']['raw_completion'] = results
        success_rate = sum(1 for r in results if r['success']) / len(results) * 100
        logger.info(f"\n  Raw Completion Success Rate: {success_rate:.1f}%")
        return success_rate
    
    def test_question_format(self):
        """Test 2: Question format (no instruction prefix)"""
        logger.info("\n❓ TEST 2: Question Format (No Instruction Prefix)")
        logger.info("Testing if base model responds to questions naturally")
        
        test_cases = [
            {
                'prompt': "What is the capital of France?",
                'expected_contains': ['Paris'],
                'description': 'Direct question'
            },
            {
                'prompt': "How many days are in a week?",
                'expected_contains': ['7', 'seven'],
                'description': 'Simple factual question'
            },
            {
                'prompt': "What color is the sky?",
                'expected_contains': ['blue'],
                'description': 'Common knowledge question'
            },
            {
                'prompt': "Q: What is 2+2?\nA:",
                'expected_contains': ['4'],
                'description': 'Q&A format'
            },
            {
                'prompt': "Question: What do bees make?\nAnswer:",
                'expected_contains': ['honey'],
                'description': 'Explicit Q&A format'
            }
        ]
        
        results = []
        for case in test_cases:
            response = self.generate_completion(case['prompt'], max_new_tokens=30)
            
            # Check if response contains expected content
            success = any(exp.lower() in response.lower() for exp in case['expected_contains'])
            
            result = {
                'prompt': case['prompt'],
                'response': response,
                'success': success,
                'description': case['description']
            }
            results.append(result)
            
            logger.info(f"  {case['description']}:")
            logger.info(f"    Prompt: {case['prompt']}")
            logger.info(f"    Response: {response[:50]}..." if len(response) > 50 else f"    Response: {response}")
            logger.info(f"    Success: {'✅' if success else '❌'}")
        
        self.results['test_categories']['question_format'] = results
        success_rate = sum(1 for r in results if r['success']) / len(results) * 100
        logger.info(f"\n  Question Format Success Rate: {success_rate:.1f}%")
        return success_rate
    
    def test_instruction_format(self):
        """Test 3: Our training format (Instruction:/Response:)"""
        logger.info("\n📋 TEST 3: Instruction/Response Format")
        logger.info("Testing if base model understands our training format")
        
        test_cases = [
            {
                'prompt': "Instruction: What is the capital of France?\nResponse:",
                'expected_contains': ['Paris'],
                'description': 'Standard instruction format'
            },
            {
                'prompt': "Instruction: Count to 5\nResponse:",
                'expected_contains': ['1', '2', '3', '4', '5'],
                'description': 'Action instruction'
            },
            {
                'prompt': "Instruction: Complete this sentence: The sun rises in the\nResponse:",
                'expected_contains': ['east'],
                'description': 'Completion instruction'
            },
            {
                'prompt': "Instruction: What is 10 divided by 2?\nResponse:",
                'expected_contains': ['5'],
                'description': 'Math instruction'
            },
            {
                'prompt': "Instruction: Say hello\nResponse:",
                'expected_contains': ['hello', 'Hello', 'Hi'],
                'description': 'Simple command'
            }
        ]
        
        results = []
        for case in test_cases:
            response = self.generate_completion(case['prompt'], max_new_tokens=50)
            
            # Check if response contains expected content
            success = any(exp.lower() in response.lower() for exp in case['expected_contains'])
            
            # Also check if it adds END token (would indicate some training)
            has_end = 'END' in response
            
            result = {
                'prompt': case['prompt'],
                'response': response,
                'success': success,
                'has_end_token': has_end,
                'description': case['description']
            }
            results.append(result)
            
            logger.info(f"  {case['description']}:")
            logger.info(f"    Prompt: {case['prompt']}")
            logger.info(f"    Response: {response[:50]}..." if len(response) > 50 else f"    Response: {response}")
            logger.info(f"    Success: {'✅' if success else '❌'}")
            logger.info(f"    Has END token: {'Yes' if has_end else 'No'}")
        
        self.results['test_categories']['instruction_format'] = results
        success_rate = sum(1 for r in results if r['success']) / len(results) * 100
        end_token_rate = sum(1 for r in results if r['has_end_token']) / len(results) * 100
        logger.info(f"\n  Instruction Format Success Rate: {success_rate:.1f}%")
        logger.info(f"  END Token Rate: {end_token_rate:.1f}%")
        return success_rate
    
    def test_imperative_commands(self):
        """Test 4: Imperative commands (no explicit instruction prefix)"""
        logger.info("\n🎯 TEST 4: Imperative Commands")
        logger.info("Testing if base model follows direct commands")
        
        test_cases = [
            {
                'prompt': "List three colors:",
                'expected_patterns': ['color', 'red', 'blue', 'green', 'yellow', 'black', 'white'],
                'description': 'List command'
            },
            {
                'prompt': "Write a haiku about nature:",
                'expected_patterns': ['tree', 'sky', 'water', 'leaf', 'wind', 'mountain', 'flower'],
                'description': 'Creative command'
            },
            {
                'prompt': "Translate 'hello' to Spanish:",
                'expected_contains': ['hola', 'Hola'],
                'description': 'Translation command'
            },
            {
                'prompt': "Define the word 'courage':",
                'expected_patterns': ['brave', 'fear', 'strength', 'face', 'difficult'],
                'description': 'Definition command'
            },
            {
                'prompt': "Calculate 15 + 27:",
                'expected_contains': ['42'],
                'description': 'Calculation command'
            }
        ]
        
        results = []
        for case in test_cases:
            response = self.generate_completion(case['prompt'], max_new_tokens=60)
            
            # Check for expected content or patterns
            if 'expected_contains' in case:
                success = any(exp.lower() in response.lower() for exp in case['expected_contains'])
            else:
                # For pattern-based checks, look for any relevant word
                success = any(pattern.lower() in response.lower() for pattern in case['expected_patterns'])
            
            result = {
                'prompt': case['prompt'],
                'response': response,
                'success': success,
                'description': case['description']
            }
            results.append(result)
            
            logger.info(f"  {case['description']}:")
            logger.info(f"    Prompt: {case['prompt']}")
            logger.info(f"    Response: {response[:60]}..." if len(response) > 60 else f"    Response: {response}")
            logger.info(f"    Success: {'✅' if success else '❌'}")
        
        self.results['test_categories']['imperative_commands'] = results
        success_rate = sum(1 for r in results if r['success']) / len(results) * 100
        logger.info(f"\n  Imperative Commands Success Rate: {success_rate:.1f}%")
        return success_rate
    
    def test_chat_style(self):
        """Test 5: Chat-style prompts (testing if model has chat training)"""
        logger.info("\n💬 TEST 5: Chat-Style Prompts")
        logger.info("Testing if base model has any chat/assistant training")
        
        test_cases = [
            {
                'prompt': "Human: What is the capital of France?\nAssistant:",
                'expected_contains': ['Paris'],
                'description': 'Human/Assistant format'
            },
            {
                'prompt': "User: Hello\nBot:",
                'expected_patterns': ['hello', 'hi', 'greet'],
                'description': 'User/Bot format'
            },
            {
                'prompt': "### Instruction: Count to 5\n### Response:",
                'expected_contains': ['1', '2', '3', '4', '5'],
                'description': 'Markdown instruction format'
            },
            {
                'prompt': "[INST] What is 2+2? [/INST]",
                'expected_contains': ['4'],
                'description': 'Special token format'
            },
            {
                'prompt': "<|user|>\nWhat color is the sky?\n<|assistant|>\n",
                'expected_contains': ['blue'],
                'description': 'Chat template format'
            }
        ]
        
        results = []
        for case in test_cases:
            response = self.generate_completion(case['prompt'], max_new_tokens=30)
            
            # Check for expected content or patterns
            if 'expected_contains' in case:
                success = any(exp.lower() in response.lower() for exp in case['expected_contains'])
            else:
                success = any(pattern.lower() in response.lower() for pattern in case.get('expected_patterns', []))
            
            result = {
                'prompt': case['prompt'],
                'response': response,
                'success': success,
                'description': case['description']
            }
            results.append(result)
            
            logger.info(f"  {case['description']}:")
            logger.info(f"    Prompt: {case['prompt'][:50]}..." if len(case['prompt']) > 50 else f"    Prompt: {case['prompt']}")
            logger.info(f"    Response: {response[:50]}..." if len(response) > 50 else f"    Response: {response}")
            logger.info(f"    Success: {'✅' if success else '❌'}")
        
        self.results['test_categories']['chat_style'] = results
        success_rate = sum(1 for r in results if r['success']) / len(results) * 100
        logger.info(f"\n  Chat-Style Success Rate: {success_rate:.1f}%")
        return success_rate
    
    def run_all_tests(self):
        """Run all tests and compile results"""
        logger.info("="*60)
        logger.info("🔬 DEFINITIVE BASE MODEL TEST")
        logger.info("Testing raw Qwen2.5-32B with NO fine-tuning")
        logger.info("="*60)
        
        # Load model
        self.load_base_model()
        
        # Run all test categories
        test_results = {}
        test_results['raw_completion'] = self.test_raw_completion()
        test_results['question_format'] = self.test_question_format()
        test_results['instruction_format'] = self.test_instruction_format()
        test_results['imperative_commands'] = self.test_imperative_commands()
        test_results['chat_style'] = self.test_chat_style()
        
        # Calculate overall summary
        self.results['summary'] = {
            'raw_completion_rate': test_results['raw_completion'],
            'question_format_rate': test_results['question_format'],
            'instruction_format_rate': test_results['instruction_format'],
            'imperative_commands_rate': test_results['imperative_commands'],
            'chat_style_rate': test_results['chat_style'],
            'overall_average': sum(test_results.values()) / len(test_results)
        }
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("📊 FINAL RESULTS SUMMARY")
        logger.info("="*60)
        logger.info(f"Raw Completion (what base models do): {test_results['raw_completion']:.1f}%")
        logger.info(f"Question Format: {test_results['question_format']:.1f}%")
        logger.info(f"Instruction/Response Format: {test_results['instruction_format']:.1f}%")
        logger.info(f"Imperative Commands: {test_results['imperative_commands']:.1f}%")
        logger.info(f"Chat-Style Prompts: {test_results['chat_style']:.1f}%")
        logger.info(f"\nOverall Average: {self.results['summary']['overall_average']:.1f}%")
        
        # Key findings
        logger.info("\n📌 KEY FINDINGS:")
        if test_results['raw_completion'] > 80:
            logger.info("✅ Base model excels at text completion (as expected)")
        if test_results['instruction_format'] > 60:
            logger.info("⚠️ Base model shows surprising instruction-following ability")
            logger.info("   This might indicate:")
            logger.info("   - Qwen2.5-32B has some instruction tuning")
            logger.info("   - Or we're actually loading a fine-tuned version")
        elif test_results['instruction_format'] < 30:
            logger.info("✅ Base model struggles with instruction format (expected)")
            logger.info("   This confirms we have the raw base model")
        
        # Check for END tokens
        instruction_results = self.results['test_categories'].get('instruction_format', [])
        end_token_count = sum(1 for r in instruction_results if r.get('has_end_token', False))
        if end_token_count > 0:
            logger.info(f"⚠️ Found END tokens in {end_token_count} responses!")
            logger.info("   This suggests the model has been fine-tuned")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = ARTIFACTS_DIR / f"base_model_definitive_test_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"\n💾 Full results saved to: {results_file}")
        logger.info("\n" + "="*60)
        logger.info("✅ DEFINITIVE TEST COMPLETE")
        logger.info("This is the authoritative baseline for Qwen2.5-32B")
        logger.info("="*60)
        
        return self.results

def main():
    """Main function"""
    tester = BaseModelTester()
    results = tester.run_all_tests()
    
    # Print clear conclusion
    print("\n" + "#"*60)
    print("# CONCLUSION")
    print("#"*60)
    
    if results['summary']['instruction_format_rate'] > 60:
        print("# The base model CAN follow instructions reasonably well")
        print("# This explains the 78.9% score in our evaluation")
        print("# Our fine-tuning improved from ~79% to ~84%")
    else:
        print("# The base model CANNOT follow instructions well")
        print("# The 78.9% score suggests a model swap in evaluation")
        print("# We need to fix the evaluation script")
    
    print("#"*60)

if __name__ == "__main__":
    main()