#!/usr/bin/env python3
"""
Ultra-clean base model test to definitively establish Qwen-2.5-32B capabilities
Eliminates ALL sources of chat template contamination
"""

import json
import logging
import torch
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys
import os
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

# Create directories
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

class UltraCleanBaseTest:
    """Ultra-clean base model testing with zero template contamination"""
    
    def __init__(self):
        """Initialize with strict contamination prevention"""
        
        logger.info("🧪 Initializing ultra-clean base model test")
        
        # Load model and tokenizer with strict settings
        model_name = "Qwen/Qwen2.5-32B"
        
        # Load tokenizer first
        logger.info("📝 Loading tokenizer with chat template disabled...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
            use_fast=True
        )
        
        # CRITICAL: Completely disable chat template
        self.tokenizer.chat_template = None
        if hasattr(self.tokenizer, 'default_chat_template'):
            self.tokenizer.default_chat_template = None
        
        # Set pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model with quantization for memory efficiency
        logger.info("🤖 Loading base model with quantization...")
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True,
            bnb_8bit_use_double_quant=True,
            bnb_8bit_quant_type="nf8",
            bnb_8bit_compute_dtype=torch.bfloat16
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
            dtype=torch.bfloat16,
            attn_implementation="flash_attention_2" if torch.cuda.is_available() else "eager"
        )
        
        self.model.eval()
        logger.info("✅ Model loaded in ultra-clean mode")
        
        # Define test cases (sentinel tests from BASE_MODEL_TRUTH.md)
        self.test_cases = {
            'sentinel_translation': {
                'prompt': "Translate to Pig Latin: hello world",
                'expected_behavior': "Should NOT produce clean translation",
                'success_criteria': lambda x: not self._is_clean_translation(x)
            },
            'sentinel_list': {
                'prompt': "List three prime numbers",
                'expected_behavior': "Should NOT produce numbered list",
                'success_criteria': lambda x: not self._is_numbered_list(x)
            },
            'sentinel_json': {
                'prompt': "Write a JSON with keys a,b and integers",
                'expected_behavior': "Should NOT produce valid JSON",
                'success_criteria': lambda x: not self._is_valid_json(x)
            },
            'sentinel_describe': {
                'prompt': "Describe the seasons",
                'expected_behavior': "Should continue/ramble, not structured description",
                'success_criteria': lambda x: not self._is_structured_description(x)
            },
            'completion_water': {
                'prompt': "Water freezes at",
                'expected_behavior': "Should complete with temperature",
                'success_criteria': lambda x: self._mentions_temperature(x)
            },
            'completion_capital': {
                'prompt': "The capital of France is",
                'expected_behavior': "Should complete with Paris",
                'success_criteria': lambda x: "paris" in x.lower()
            },
            'question_direct': {
                'prompt': "What is 2 + 2?",
                'expected_behavior': "May not answer directly, might continue",
                'success_criteria': lambda x: self._answers_math_directly(x)
            },
            'instruction_direct': {
                'prompt': "Answer this: What color is the sky?",
                'expected_behavior': "Should NOT follow instruction cleanly",
                'success_criteria': lambda x: not self._follows_instruction_cleanly(x)
            }
        }
    
    def _generate_ultra_clean(self, prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate with absolute zero template contamination"""
        
        # Tokenize with add_special_tokens=False - CRITICAL!
        inputs = self.tokenizer(
            prompt,
            add_special_tokens=False,  # This prevents template application!
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=False
        ).to(self.model.device)
        
        # Log tokenization for verification
        first_10_tokens = inputs['input_ids'][0][:10].tolist()
        token_preview = self.tokenizer.decode(first_10_tokens, skip_special_tokens=True)
        
        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=128,
                temperature=temperature,
                do_sample=temperature > 0.0,
                top_p=0.9 if temperature > 0.0 else None,
                repetition_penalty=1.1,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id,
                return_dict_in_generate=True
            )
        
        # Decode only new tokens
        input_length = inputs['input_ids'].shape[1]
        generated_tokens = outputs.sequences[0][input_length:]
        response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        
        return {
            'prompt': prompt,
            'response': response,
            'temperature': temperature,
            'input_tokens': first_10_tokens,
            'token_preview': token_preview,
            'has_template_markers': self._check_template_contamination(token_preview, response)
        }
    
    def _check_template_contamination(self, token_preview: str, response: str) -> List[str]:
        """Check for any signs of template contamination"""
        
        contamination_markers = []
        
        # Check for chat template tokens
        template_tokens = ['<|im_start|>', '<|im_end|>', 'system', 'user', 'assistant', 
                          'You are a helpful', 'I am an AI', 'As an AI']
        
        for marker in template_tokens:
            if marker in token_preview or marker in response:
                contamination_markers.append(f"Found template marker: {marker}")
        
        # Check for structured assistant-like responses
        if response.strip().startswith(("I ", "As an", "Here is", "Sure,", "Of course")):
            contamination_markers.append("Assistant-like response start")
        
        # Check for proper sentence endings (base model often doesn't stop cleanly)
        if response.strip().endswith(('.', '!', '?')) and len(response.strip()) > 10:
            contamination_markers.append("Clean sentence ending (suspicious for base model)")
        
        return contamination_markers
    
    # Success criteria functions
    def _is_clean_translation(self, text: str) -> bool:
        """Check if text is a clean Pig Latin translation"""
        # Look for "ello-hay orld-way" or similar
        pig_latin_markers = ['ello-hay', 'orld-way', '-ay ', '-way ']
        return any(marker in text.lower() for marker in pig_latin_markers)
    
    def _is_numbered_list(self, text: str) -> bool:
        """Check if text contains a numbered list"""
        lines = text.strip().split('\n')
        numbered_lines = sum(1 for line in lines if line.strip() and 
                           (line.strip()[0].isdigit() or line.strip().startswith(('1.', '2.', '3.'))))
        return numbered_lines >= 2
    
    def _is_valid_json(self, text: str) -> bool:
        """Check if text contains valid JSON"""
        try:
            # Look for JSON-like structure
            if '{' in text and '}' in text:
                json_part = text[text.index('{'):text.rindex('}')+1]
                json.loads(json_part)
                return True
        except:
            pass
        return False
    
    def _is_structured_description(self, text: str) -> bool:
        """Check if text is a structured description of seasons"""
        season_words = ['spring', 'summer', 'fall', 'autumn', 'winter']
        season_count = sum(1 for word in season_words if word.lower() in text.lower())
        
        # Structured if mentions multiple seasons or has clear organization
        if season_count >= 2:
            return True
        
        # Check for structured language
        structured_markers = ['first', 'second', 'then', 'during', 'characterized by']
        return any(marker in text.lower() for marker in structured_markers)
    
    def _mentions_temperature(self, text: str) -> bool:
        """Check if text mentions temperature/freezing point"""
        temp_markers = ['0', '32', 'degree', 'celsius', 'fahrenheit', 'freezing', 'zero']
        return any(marker.lower() in text.lower() for marker in temp_markers)
    
    def _answers_math_directly(self, text: str) -> bool:
        """Check if text directly answers 2+2=4"""
        # Look for "4" as answer
        return '4' in text and not any(wrong in text for wrong in ['3', '5', '6'])
    
    def _follows_instruction_cleanly(self, text: str) -> bool:
        """Check if text cleanly follows the instruction format"""
        # Look for direct answer about sky color
        sky_words = ['blue', 'gray', 'grey', 'clear']
        if any(word in text.lower() for word in sky_words):
            # But not if it's just continuing the prompt
            if not text.lower().startswith('answer this'):
                return True
        return False
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run the comprehensive ultra-clean test"""
        
        logger.info("🚀 Starting comprehensive ultra-clean base model test")
        
        results = {
            'model_name': "Qwen/Qwen2.5-32B",
            'test_type': 'ultra_clean_base_model',
            'timestamp': datetime.now().isoformat(),
            'contamination_prevention': [
                'chat_template = None',
                'add_special_tokens = False',
                'no system/user/assistant markers',
                'strict tokenization verification'
            ],
            'test_results': {},
            'temperature_comparison': {},
            'contamination_analysis': {},
            'summary': {}
        }
        
        # Test at two temperatures
        temperatures = [0.1, 0.7]
        
        for temp in temperatures:
            logger.info(f"🌡️ Testing at temperature {temp}")
            temp_results = {}
            
            for test_name, test_config in self.test_cases.items():
                logger.info(f"  Testing {test_name}: {test_config['prompt'][:30]}...")
                
                # Generate response
                result = self._generate_ultra_clean(test_config['prompt'], temperature=temp)
                
                # Evaluate success
                success = test_config['success_criteria'](result['response'])
                
                temp_results[test_name] = {
                    **result,
                    'expected_behavior': test_config['expected_behavior'],
                    'success': success,
                    'contamination_markers': result['has_template_markers']
                }
                
                logger.info(f"    Response: {result['response'][:50]}...")
                logger.info(f"    Success: {success}")
                if result['has_template_markers']:
                    logger.warning(f"    ⚠️ Contamination detected: {result['has_template_markers']}")
            
            results['test_results'][f'temp_{temp}'] = temp_results
        
        # Analyze contamination
        all_contamination = []
        for temp_results in results['test_results'].values():
            for test_result in temp_results.values():
                all_contamination.extend(test_result['contamination_markers'])
        
        results['contamination_analysis'] = {
            'total_contamination_flags': len(all_contamination),
            'unique_contamination_types': list(set(all_contamination)),
            'is_clean_test': len(all_contamination) == 0
        }
        
        # Create summary
        for temp in temperatures:
            temp_key = f'temp_{temp}'
            temp_results = results['test_results'][temp_key]
            
            # Sentinel tests (should FAIL for clean base model)
            sentinel_tests = ['sentinel_translation', 'sentinel_list', 'sentinel_json', 'sentinel_describe']
            sentinel_failures = sum(1 for test in sentinel_tests if temp_results[test]['success'])
            
            # Completion tests (should PASS)
            completion_tests = ['completion_water', 'completion_capital']
            completion_successes = sum(1 for test in completion_tests if temp_results[test]['success'])
            
            # Instruction tests (should mostly FAIL for base model)
            instruction_tests = ['question_direct', 'instruction_direct']
            instruction_successes = sum(1 for test in instruction_tests if temp_results[test]['success'])
            
            results['summary'][temp_key] = {
                'sentinel_failures': f"{sentinel_failures}/{len(sentinel_tests)} (good - base should fail these)",
                'completion_successes': f"{completion_successes}/{len(completion_tests)} (expected for base)",
                'instruction_successes': f"{instruction_successes}/{len(instruction_tests)} (low expected for base)",
                'interpretation': self._interpret_results(sentinel_failures, completion_successes, instruction_successes)
            }
        
        return results
    
    def _interpret_results(self, sentinel_failures: int, completion_successes: int, instruction_successes: int) -> str:
        """Interpret the test results"""
        
        if sentinel_failures == 0 and completion_successes >= 1:
            return "✅ CLEAN BASE MODEL BEHAVIOR: Fails instructions, good at completions"
        elif sentinel_failures >= 3:
            return "❌ TEMPLATE CONTAMINATION: Too good at following instructions"
        elif completion_successes == 0:
            return "⚠️ MODEL ISSUE: Can't even do basic completions"
        else:
            return "❓ MIXED RESULTS: Needs further investigation"

def main():
    """Main function to run ultra-clean base model test"""
    
    logger.info("🎯 Starting ultra-clean base model test")
    
    try:
        # Run test
        tester = UltraCleanBaseTest()
        results = tester.run_comprehensive_test()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = ARTIFACTS_DIR / f"base_model_ultra_clean_test_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        print(f"""
============================================================
🧪 ULTRA-CLEAN BASE MODEL TEST COMPLETE
============================================================

Model: {results['model_name']}
Test Type: {results['test_type']}
Contamination Prevention: {', '.join(results['contamination_prevention'])}

Contamination Analysis:
- Total flags: {results['contamination_analysis']['total_contamination_flags']}
- Unique types: {len(results['contamination_analysis']['unique_contamination_types'])}
- Clean test: {results['contamination_analysis']['is_clean_test']}

Results Summary:
""")
        
        for temp, summary in results['summary'].items():
            print(f"\nTemperature {temp.split('_')[1]}:")
            print(f"  Sentinel failures: {summary['sentinel_failures']}")
            print(f"  Completion successes: {summary['completion_successes']}")
            print(f"  Instruction successes: {summary['instruction_successes']}")
            print(f"  Interpretation: {summary['interpretation']}")
        
        # Show sample responses
        print(f"\nSample Responses (Temperature 0.7):")
        temp_results = results['test_results']['temp_0.7']
        for i, (test_name, result) in enumerate(list(temp_results.items())[:4]):
            print(f"\n{i+1}. {test_name}")
            print(f"   Prompt: {result['prompt']}")
            print(f"   Response: {result['response'][:100]}...")
            print(f"   Success: {result['success']} | Contamination: {bool(result['contamination_markers'])}")
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        if not results['contamination_analysis']['is_clean_test']:
            print(f"\n⚠️ WARNING: Template contamination detected!")
            print(f"Contamination types: {results['contamination_analysis']['unique_contamination_types']}")
        else:
            print(f"\n✅ Test appears clean - no template contamination detected")
            
    except Exception as e:
        logger.error(f"❌ Ultra-clean test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()