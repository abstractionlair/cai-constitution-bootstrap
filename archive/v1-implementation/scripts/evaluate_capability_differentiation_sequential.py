#!/usr/bin/env python3
"""
Memory-optimized Capability Differentiation Test - Sequential Model Loading
Differentiates between completion, instruction-following, and question-answering capabilities
Loads models one at a time to avoid GPU memory issues
"""

import torch
import json
import logging
import time
import re
import csv
import gc
from pathlib import Path
from transformers import AutoTokenizer
from peft import PeftModel
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any
import numpy as np
import statistics

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))
from utils.clean_model_loader import CleanModelLoader

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

class SequentialCapabilityEvaluator:
    """Memory-optimized evaluator that loads models sequentially"""
    
    def __init__(self):
        self.tokenizer = None
        self.loader = None

        # Test temperature (use single temperature to save time/memory)
        self.temperature = 0.5
        
        # Scoring dimensions
        self.score_dimensions = [
            'completion',     # Natural pattern completion
            'instruction',    # Following specific commands
            'answer',         # Direct question answering
            'format',         # Matching requested format
            'deflection',     # Avoiding/refusing task (inverted - lower is better)
            'continuation'    # Just extending prompt (inverted - lower is better)
        ]
        
        logger.info("🎯 Initialized Sequential Capability Evaluator")
    
    def setup_tokenizer(self):
        """Setup tokenizer once (CleanModelLoader handles contamination prevention in model loading)"""
        logger.info("📝 Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-32B",
            trust_remote_code=True,
            padding_side='right'
        )

        # Template contamination is prevented by CleanModelLoader during model loading
        # But set pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        logger.info("✅ Tokenizer setup complete")
    
    def load_single_model(self, model_type: str):
        """Load a single model, cleaning up GPU memory first"""
        
        # Clear GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        
        if model_type == 'base':
            logger.info("🔵 Loading base model...")
            self.loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
            model, _, provenance = self.loader.load()
            logger.info(f"📋 Loader version: {provenance['loader_version'][:8]}")

        elif model_type == 'sft':
            logger.info("🟡 Loading SFT model...")
            self.loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
            base_model, _, _ = self.loader.load()
            model = PeftModel.from_pretrained(base_model, str(SFT_CHECKPOINT))

        elif model_type == 'dpo':
            logger.info("🟢 Loading DPO model...")
            self.loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
            base_model, _, _ = self.loader.load()
            model = PeftModel.from_pretrained(base_model, str(DPO_CHECKPOINT))
        
        model.eval()
        logger.info(f"✅ {model_type.upper()} model loaded successfully")
        return model
    
    def create_test_suite(self) -> List[Dict[str, Any]]:
        """Create focused test suite - reduced to 50 tests for speed"""
        
        tests = []
        test_id = 1
        
        # 1. PURE COMPLETION TESTS (15 tests) - Base should excel
        completion_tests = [
            # Factual completions (5 tests)
            {"prompt": "The capital of France is", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "Water freezes at", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "The speed of light is", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "π equals", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "2 + 2 =", "expected_capability": "completion", "expected_base_score": 0.9},
            
            # Pattern continuations (5 tests)
            {"prompt": "1, 2, 3, 4,", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "A, B, C, D,", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "Monday, Tuesday, Wednesday,", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "Red, orange, yellow,", "expected_capability": "completion", "expected_base_score": 0.7},
            {"prompt": "Once upon a", "expected_capability": "completion", "expected_base_score": 0.8},
            
            # Scientific facts (5 tests)
            {"prompt": "DNA stands for", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "Photosynthesis is", "expected_capability": "completion", "expected_base_score": 0.7},
            {"prompt": "Einstein's theory of", "expected_capability": "completion", "expected_base_score": 0.6},
            {"prompt": "Evolution by natural", "expected_capability": "completion", "expected_base_score": 0.6},
            {"prompt": "The periodic table", "expected_capability": "completion", "expected_base_score": 0.7},
        ]
        
        # 2. PURE INSTRUCTION TESTS (20 tests) - Base should struggle
        instruction_tests = [
            # List generation (10 tests)
            {"prompt": "List three prime numbers", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "List five colors", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Name four seasons", "expected_capability": "instruction", "expected_base_score": 0.4},
            {"prompt": "List three types of fruit", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Give me two examples of mammals", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Name three countries in Europe", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "List four basic math operations", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Name three programming languages", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "List two types of weather", "expected_capability": "instruction", "expected_base_score": 0.4},
            {"prompt": "Name five days of the week", "expected_capability": "instruction", "expected_base_score": 0.4},
            
            # Format-specific (5 tests)
            {"prompt": "Write in JSON format: name and age", "expected_capability": "instruction", "expected_base_score": 0.1},
            {"prompt": "Create a table with two columns", "expected_capability": "instruction", "expected_base_score": 0.1},
            {"prompt": "Format as a numbered list", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Write as bullet points", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Write a formal letter opening", "expected_capability": "instruction", "expected_base_score": 0.2},
            
            # Creative tasks (5 tests)
            {"prompt": "Generate a name for a pet dog", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Create a slogan for a pizza restaurant", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Generate a random 5-digit number", "expected_capability": "instruction", "expected_base_score": 0.4},
            {"prompt": "Invent a new ice cream flavor", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Create a title for a mystery novel", "expected_capability": "instruction", "expected_base_score": 0.3},
        ]
        
        # 3. QUESTION ANSWERING TESTS (15 tests)
        qa_tests = [
            # What questions (5 tests)
            {"prompt": "What is the largest planet?", "expected_capability": "answer", "expected_base_score": 0.6},
            {"prompt": "What do bees make?", "expected_capability": "answer", "expected_base_score": 0.7},
            {"prompt": "What is the chemical symbol for gold?", "expected_capability": "answer", "expected_base_score": 0.6},
            {"prompt": "What organ pumps blood in the human body?", "expected_capability": "answer", "expected_base_score": 0.6},
            {"prompt": "What language is spoken in Brazil?", "expected_capability": "answer", "expected_base_score": 0.6},
            
            # How questions (5 tests)
            {"prompt": "How do plants make food?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "How does rain form?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "How do you make tea?", "expected_capability": "answer", "expected_base_score": 0.5},
            {"prompt": "How do fish breathe underwater?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "How do birds fly?", "expected_capability": "answer", "expected_base_score": 0.4},
            
            # Why questions (5 tests)
            {"prompt": "Why do leaves change color in fall?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "Why is the sky blue?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "Why do we need sleep?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "Why do birds migrate?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "Why is exercise important?", "expected_capability": "answer", "expected_base_score": 0.5},
        ]
        
        # Combine all test categories
        all_test_groups = [
            ("pure_completion", completion_tests),
            ("pure_instruction", instruction_tests),
            ("question_answer", qa_tests)
        ]
        
        # Create final test structure
        for category, test_group in all_test_groups:
            for test in test_group:
                tests.append({
                    'test_id': test_id,
                    'category': category,
                    'prompt': test['prompt'],
                    'expected_capability': test['expected_capability'],
                    'expected_base_score': test['expected_base_score']
                })
                test_id += 1
        
        logger.info(f"📋 Created focused test suite with {len(tests)} tests across {len(all_test_groups)} categories")
        return tests
    
    def generate_response(self, model: Any, prompt: str) -> str:
        """Generate response using CleanModelLoader"""
        response = self.loader.generate(
            model,
            self.tokenizer,
            prompt,
            max_new_tokens=80,  # Shorter responses for faster evaluation
            temperature=self.temperature,
            do_sample=True,
            top_p=0.9,
            stop_strings=["END", "\n\n"]
        )

        # Clean response
        if "END" in response:
            response = response.split("END")[0].strip()
        if "\n\n" in response:
            response = response.split("\n\n")[0].strip()

        return response
    
    def score_response(self, prompt: str, response: str, expected_capability: str) -> Dict[str, float]:
        """Multi-dimensional scoring of response"""
        
        scores = {}
        
        # 1. Completion Score (0-1): Natural pattern completion
        scores['completion'] = self._measure_completion_quality(prompt, response)
        
        # 2. Instruction Score (0-1): Following specific command
        scores['instruction'] = self._measure_instruction_following(prompt, response)
        
        # 3. Answer Score (0-1): Direct question response
        scores['answer'] = self._measure_question_answering(prompt, response)
        
        # 4. Format Score (0-1): Matching requested format
        scores['format'] = self._measure_format_compliance(prompt, response)
        
        # 5. Deflection Score (0-1): Avoiding/refusing task (inverted - lower is better)
        scores['deflection'] = 1.0 - self._detect_deflection(response)
        
        # 6. Continuation Score (0-1): Just extending prompt (inverted - lower is better)
        scores['continuation'] = 1.0 - self._detect_prompt_continuation(prompt, response)
        
        return scores
    
    def _measure_completion_quality(self, prompt: str, response: str) -> float:
        """Measure how well response completes the pattern"""
        
        if not response:
            return 0.0
        
        # Check for direct, concise completion
        if len(response.split()) <= 5:  # Short, direct completion
            return 0.8
        
        # Check for relevant content words
        prompt_words = set(prompt.lower().split())
        response_words = set(response.lower().split())
        
        # Good completion doesn't repeat too many prompt words
        overlap = len(prompt_words & response_words) / max(len(prompt_words), 1)
        if overlap > 0.7:  # Too much repetition
            return 0.3
        
        # Check for natural completion patterns
        if any(pattern in prompt.lower() for pattern in ['capital of', 'freezes at', 'boils at']):
            if len(response.split()) <= 3:
                return 0.9
        
        # Default scoring based on response length and coherence
        if 1 <= len(response.split()) <= 10:
            return 0.6
        else:
            return 0.4
    
    def _measure_instruction_following(self, prompt: str, response: str) -> float:
        """Measure instruction following capability"""
        
        if not response:
            return 0.0
        
        prompt_lower = prompt.lower()
        response_lower = response.lower()
        
        # List generation instructions
        if any(word in prompt_lower for word in ['list', 'name three', 'give me']):
            # Check for list-like structure
            if any(marker in response for marker in ['1.', '2.', '•', '-', ',']):
                return 0.8
            elif len(response.split()) >= 3:  # At least some items
                return 0.6
            else:
                return 0.2
        
        # Format-specific instructions
        if any(word in prompt_lower for word in ['json', 'table', 'format', 'bullet']):
            if any(marker in response for marker in ['{', '}', '|', '•', '-']):
                return 0.8
            else:
                return 0.2
        
        # Creation/generation tasks
        if any(word in prompt_lower for word in ['create', 'generate', 'invent', 'write']):
            if len(response.split()) >= 3:
                return 0.6
            else:
                return 0.3
        
        return 0.4  # Default moderate score
    
    def _measure_question_answering(self, prompt: str, response: str) -> float:
        """Measure direct question answering"""
        
        if not response:
            return 0.0
        
        prompt_lower = prompt.lower()
        response_lower = response.lower()
        
        # Check if prompt is actually a question
        is_question = any(word in prompt_lower for word in ['what', 'how', 'why', 'when', 'where', 'who', 'is', 'do', 'does', 'can', 'will'])
        
        if not is_question:
            return 0.0
        
        # Deflection patterns (bad for QA)
        deflective_phrases = ["i don't know", "not sure", "unclear", "i can't", "tell me more"]
        if any(phrase in response_lower for phrase in deflective_phrases):
            return 0.1
        
        # Question marks in response (usually bad for answers)
        if response.count('?') > 0:
            return 0.2
        
        # Direct factual answers (good)
        if len(response.split()) <= 5 and not response_lower.startswith(('the ', 'it ', 'they ')):
            return 0.8
        
        # Longer explanatory answers
        if len(response.split()) >= 5:
            return 0.6
        
        return 0.4  # Default moderate score
    
    def _measure_format_compliance(self, prompt: str, response: str) -> float:
        """Measure format compliance"""
        
        if not response:
            return 0.0
        
        prompt_lower = prompt.lower()
        
        # JSON format requests
        if 'json' in prompt_lower:
            if '{' in response and '}' in response:
                return 0.9
            else:
                return 0.1
        
        # List format requests  
        if any(word in prompt_lower for word in ['list', 'bullet']):
            if any(marker in response for marker in ['1.', '2.', '•', '-']):
                return 0.8
            else:
                return 0.3
        
        # Number requests
        if 'number' in prompt_lower or 'digit' in prompt_lower:
            if bool(re.search(r'\d+', response)):
                return 0.8
            else:
                return 0.2
        
        return 0.5  # Default neutral score
    
    def _detect_deflection(self, response: str) -> float:
        """Detect deflection/avoidance (0-1, higher = more deflection)"""
        
        if not response:
            return 1.0
        
        response_lower = response.lower()
        
        # Explicit deflection phrases
        deflection_phrases = [
            "i don't know", "not sure", "unclear", "i can't", "i cannot",
            "tell me more", "please clarify", "what do you mean",
            "i'm not able", "i don't understand", "that's impossible",
        ]
        
        for phrase in deflection_phrases:
            if phrase in response_lower:
                return 0.8
        
        # Very short non-committal responses
        if len(response.split()) <= 2 and response_lower in ['maybe', 'perhaps', 'unknown', 'unclear']:
            return 0.7
        
        return 0.0  # No deflection detected
    
    def _detect_prompt_continuation(self, prompt: str, response: str) -> float:
        """Detect if response just continues the prompt (0-1, higher = more continuation)"""
        
        if not response:
            return 1.0
        
        # Check for prompt repetition
        prompt_words = prompt.lower().split()
        response_words = response.lower().split()
        
        if len(response_words) == 0:
            return 1.0
        
        # Calculate word overlap
        overlap = len(set(prompt_words) & set(response_words)) / len(set(prompt_words + response_words))
        
        if overlap > 0.5:
            return 0.8
        elif overlap > 0.3:
            return 0.4
        else:
            return 0.0
    
    def evaluate_single_model(self, model_name: str, test_suite: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate a single model on the test suite"""
        
        logger.info(f"🧪 Evaluating {model_name.upper()} model...")
        
        # Load model
        model = self.load_single_model(model_name)
        
        # Run tests
        results = []
        for i, test in enumerate(test_suite, 1):
            if i % 10 == 0:
                logger.info(f"   Progress: {i}/{len(test_suite)} tests")
            
            # Generate response
            response = self.generate_response(model, test['prompt'])
            
            # Score response
            scores = self.score_response(test['prompt'], response, test['expected_capability'])
            
            # Store result
            results.append({
                'test_id': test['test_id'],
                'category': test['category'],
                'prompt': test['prompt'],
                'response': response,
                'scores': scores
            })
        
        # Clean up model
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        
        logger.info(f"✅ {model_name.upper()} evaluation complete")
        return results
    
    def run_sequential_evaluation(self) -> Dict[str, Any]:
        """Run sequential evaluation of all models"""
        
        logger.info("🚀 Starting sequential capability differentiation evaluation")
        
        # Setup tokenizer
        self.setup_tokenizer()
        
        # Create test suite
        test_suite = self.create_test_suite()
        
        # Initialize results
        results = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(test_suite),
                'temperature': self.temperature,
                'models': ['base', 'sft', 'dpo']
            },
            'model_results': {},
            'summary_stats': {},
            'capability_matrix': {},
            'stage2_readiness': {}
        }
        
        # Evaluate each model sequentially
        model_names = ['base', 'sft', 'dpo']
        for model_name in model_names:
            try:
                model_results = self.evaluate_single_model(model_name, test_suite)
                results['model_results'][model_name] = model_results
            except Exception as e:
                logger.error(f"❌ Failed to evaluate {model_name}: {e}")
                if model_name in ['sft', 'dpo']:
                    logger.info(f"⚠️ Continuing without {model_name} model")
                    continue
                else:
                    raise  # Base model is required
        
        # Compute analysis
        logger.info("📊 Computing analysis...")
        results['summary_stats'] = self._compute_summary_stats(results['model_results'])
        results['capability_matrix'] = self._create_capability_matrix(results['model_results'])
        results['stage2_readiness'] = self._assess_stage2_readiness(results)
        
        logger.info("✅ Sequential evaluation complete")
        return results
    
    def _compute_summary_stats(self, model_results: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Compute summary statistics"""
        
        stats = {}
        
        for model_name, results in model_results.items():
            stats[model_name] = {}
            
            # By category
            categories = set(r['category'] for r in results)
            for category in categories:
                category_results = [r for r in results if r['category'] == category]
                stats[model_name][category] = {}
                
                for dimension in self.score_dimensions:
                    scores = [r['scores'][dimension] for r in category_results]
                    stats[model_name][category][dimension] = {
                        'mean': statistics.mean(scores),
                        'std': statistics.stdev(scores) if len(scores) > 1 else 0.0,
                        'count': len(scores)
                    }
            
            # Overall stats
            stats[model_name]['overall'] = {}
            for dimension in self.score_dimensions:
                all_scores = [r['scores'][dimension] for r in results]
                stats[model_name]['overall'][dimension] = {
                    'mean': statistics.mean(all_scores),
                    'std': statistics.stdev(all_scores) if len(all_scores) > 1 else 0.0,
                    'count': len(all_scores)
                }
        
        return stats
    
    def _create_capability_matrix(self, model_results: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Create capability comparison matrix"""
        
        matrix = {}
        categories = ['pure_completion', 'pure_instruction', 'question_answer']
        
        for model_name, results in model_results.items():
            matrix[model_name] = {}
            
            for category in categories:
                category_results = [r for r in results if r['category'] == category]
                
                if not category_results:
                    continue
                
                # Primary capability scores
                primary_scores = []
                overall_scores = []
                
                for result in category_results:
                    scores = result['scores']
                    
                    # Select primary dimension based on category
                    if category == 'pure_completion':
                        primary_scores.append(scores['completion'])
                    elif category == 'pure_instruction':
                        primary_scores.append(scores['instruction'])
                    elif category == 'question_answer':
                        primary_scores.append(scores['answer'])
                    
                    # Overall score (average of all positive dimensions)
                    overall_scores.append(statistics.mean([
                        scores['completion'], scores['instruction'], 
                        scores['answer'], scores['format'],
                        scores['deflection'], scores['continuation']
                    ]))
                
                matrix[model_name][category] = {
                    'primary_score': statistics.mean(primary_scores) if primary_scores else 0.0,
                    'overall_score': statistics.mean(overall_scores) if overall_scores else 0.0,
                    'test_count': len(category_results)
                }
        
        return matrix
    
    def _assess_stage2_readiness(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess Stage 2 readiness"""
        
        readiness = {}
        capability_matrix = results['capability_matrix']
        
        for model_name in ['sft', 'dpo']:
            if model_name not in capability_matrix:
                continue
            
            model_scores = capability_matrix[model_name]
            base_scores = capability_matrix.get('base', {})
            
            # Success criteria
            pure_instruction_score = model_scores.get('pure_instruction', {}).get('primary_score', 0.0)
            overall_score = statistics.mean([
                cat_data['overall_score'] for cat_data in model_scores.values()
            ])
            
            # Compare to base model
            base_instruction_score = base_scores.get('pure_instruction', {}).get('primary_score', 0.0)
            instruction_improvement = pure_instruction_score - base_instruction_score
            
            # Assessment criteria
            criteria = {
                'pure_instruction_threshold': pure_instruction_score >= 0.7,  # >70% on pure instructions
                'instruction_improvement': instruction_improvement >= 0.4,   # +40% over base
                'overall_performance': overall_score >= 0.6,                # 60% overall
            }
            
            readiness[model_name] = {
                'scores': {
                    'pure_instruction': pure_instruction_score,
                    'overall': overall_score,
                    'improvement_over_base': instruction_improvement
                },
                'criteria_met': criteria,
                'stage2_ready': all(criteria.values()),
                'recommendations': self._generate_recommendations(model_name, model_scores)
            }
        
        return readiness
    
    def _generate_recommendations(self, model_name: str, scores: Dict[str, Dict]) -> List[str]:
        """Generate recommendations based on performance"""
        
        recommendations = []
        
        # Check each capability area
        if scores.get('pure_instruction', {}).get('primary_score', 0) < 0.7:
            recommendations.append("Improve instruction following with more diverse command training")
        
        if scores.get('question_answer', {}).get('primary_score', 0) < 0.6:
            recommendations.append("Enhance question answering with more QA pairs")
        
        if scores.get('pure_completion', {}).get('primary_score', 0) < 0.8:
            recommendations.append("Maintain completion ability - may need completion-preservation training")
        
        if not recommendations:
            recommendations.append("Ready for Stage 2 training")
        
        return recommendations
    
    def save_results(self, results: Dict[str, Any]) -> Path:
        """Save results"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        json_file = ARTIFACTS_DIR / f"capability_results_sequential_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save CSV matrix
        csv_file = ARTIFACTS_DIR / f"capability_matrix_sequential_{timestamp}.csv"
        self._save_csv_matrix(results['capability_matrix'], csv_file)
        
        # Save report
        report_file = ARTIFACTS_DIR / f"capability_report_sequential_{timestamp}.md"
        self._save_report(results, report_file)
        
        logger.info(f"💾 Results saved: {json_file}, {csv_file}, {report_file}")
        return json_file
    
    def _save_csv_matrix(self, capability_matrix: Dict, csv_file: Path):
        """Save capability matrix as CSV"""
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Model', 'Category', 'Primary_Score', 'Overall_Score', 'Test_Count'])
            
            for model_name, model_data in capability_matrix.items():
                for category, scores in model_data.items():
                    writer.writerow([
                        model_name, category,
                        f"{scores['primary_score']:.3f}",
                        f"{scores['overall_score']:.3f}",
                        scores['test_count']
                    ])
    
    def _save_report(self, results: Dict[str, Any], report_file: Path):
        """Save summary report"""
        
        with open(report_file, 'w') as f:
            f.write(f"""# Sequential Capability Differentiation Report

Generated: {results['metadata']['timestamp']}
Total Tests: {results['metadata']['total_tests']}
Models: {', '.join(results['metadata']['models'])}
Temperature: {results['metadata']['temperature']}

## Stage 2 Readiness Assessment

""")
            
            for model_name, readiness in results['stage2_readiness'].items():
                ready = "✅ READY" if readiness['stage2_ready'] else "❌ NOT READY"
                f.write(f"**{model_name.upper()}**: {ready}\n")
                f.write(f"- Pure Instruction: {readiness['scores']['pure_instruction']:.1%}\n")
                f.write(f"- Overall: {readiness['scores']['overall']:.1%}\n")
                f.write(f"- Improvement: +{readiness['scores']['improvement_over_base']:.1%}\n\n")
            
            f.write("## Capability Matrix\n\n")
            f.write("| Model | Pure Completion | Pure Instruction | Question Answer |\n")
            f.write("|-------|----------------|------------------|-----------------|\n")
            
            for model_name in results['metadata']['models']:
                if model_name in results['capability_matrix']:
                    scores = results['capability_matrix'][model_name]
                    f.write(f"| {model_name.upper()} |")
                    for category in ['pure_completion', 'pure_instruction', 'question_answer']:
                        score = scores.get(category, {}).get('primary_score', 0.0)
                        f.write(f" {score:.1%} |")
                    f.write("\n")

def main():
    """Main function"""
    
    logger.info("🎯 Starting Sequential Capability Differentiation Evaluation")
    
    try:
        evaluator = SequentialCapabilityEvaluator()
        results = evaluator.run_sequential_evaluation()
        results_file = evaluator.save_results(results)
        
        print(f"""
============================================================
🎉 SEQUENTIAL EVALUATION COMPLETE
============================================================

Total Tests: {results['metadata']['total_tests']}
Results: {results_file}

STAGE 2 READINESS:
""")
        
        for model_name, readiness in results['stage2_readiness'].items():
            status = "✅ READY" if readiness['stage2_ready'] else "❌ NOT READY"
            print(f"{model_name.upper()}: {status}")
            print(f"  Instruction: {readiness['scores']['pure_instruction']:.1%}")
            print(f"  Overall: {readiness['scores']['overall']:.1%}")
            print(f"  Improvement: +{readiness['scores']['improvement_over_base']:.1%}")
        
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()