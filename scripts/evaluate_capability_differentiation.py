#!/usr/bin/env python3
"""
Comprehensive Capability Differentiation Test System
Differentiates between completion, instruction-following, and question-answering capabilities
150 tests across 5 categories with multi-dimensional scoring
"""

import torch
import json
import logging
import time
import re
import csv
from pathlib import Path
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

class CapabilityDifferentiationEvaluator:
    """Comprehensive system to differentiate model capabilities"""
    
    def __init__(self):
        self.models = {}
        self.tokenizer = None
        self.loader = None

        # Test temperatures
        self.temperatures = [0.1, 0.5, 0.9]

        # Scoring dimensions
        self.score_dimensions = [
            'completion',     # Natural pattern completion
            'instruction',    # Following specific commands
            'answer',         # Direct question answering
            'format',         # Matching requested format
            'deflection',     # Avoiding/refusing task (inverted - lower is better)
            'continuation'    # Just extending prompt (inverted - lower is better)
        ]

        logger.info("🎯 Initialized Capability Differentiation Evaluator")
    
    def load_models(self):
        """Load base, SFT, and DPO models via CleanModelLoader"""
        logger.info("🤖 Loading models for capability differentiation...")

        # Load base model
        logger.info("🔵 Loading base model...")
        self.loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
        self.models['base'], self.tokenizer, provenance = self.loader.load()
        logger.info(f"📋 Loader version: {provenance['loader_version'][:8]}")

        # Load SFT model (separate instance to prevent contamination)
        logger.info("🟡 Loading SFT model...")
        sft_loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
        sft_base, _, _ = sft_loader.load()
        self.models['sft'] = PeftModel.from_pretrained(sft_base, str(SFT_CHECKPOINT))

        # Load DPO model (separate instance)
        logger.info("🟢 Loading DPO model...")
        dpo_loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
        dpo_base, _, _ = dpo_loader.load()
        self.models['dpo'] = PeftModel.from_pretrained(dpo_base, str(DPO_CHECKPOINT))

        # Set all models to eval mode
        for model in self.models.values():
            model.eval()

        logger.info("✅ All models loaded successfully")
    
    def create_test_suite(self) -> List[Dict[str, Any]]:
        """Create comprehensive test suite with 150 tests"""
        
        tests = []
        test_id = 1
        
        # 1. PURE COMPLETION TESTS (30 tests) - Base should excel
        completion_tests = [
            # Factual completions (10 tests)
            {"prompt": "The capital of France is", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "The capital of Germany is", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "The capital of Japan is", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "The capital of Brazil is", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "The capital of Australia is", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "Water freezes at", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "Water boils at", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "The speed of light is", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "Gravity on Earth is", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "The human body has", "expected_capability": "completion", "expected_base_score": 0.7},
            
            # Pattern continuations (5 tests)
            {"prompt": "1, 2, 3, 4,", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "A, B, C, D,", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "Monday, Tuesday, Wednesday,", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "Red, orange, yellow,", "expected_capability": "completion", "expected_base_score": 0.7},
            {"prompt": "Spring, Summer, Autumn,", "expected_capability": "completion", "expected_base_score": 0.7},
            
            # Common phrases (5 tests)
            {"prompt": "Once upon a", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "To be or not to", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "In the beginning", "expected_capability": "completion", "expected_base_score": 0.7},
            {"prompt": "Happy birthday", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "Good morning", "expected_capability": "completion", "expected_base_score": 0.7},
            
            # Scientific facts (5 tests)
            {"prompt": "DNA stands for", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "Photosynthesis is", "expected_capability": "completion", "expected_base_score": 0.7},
            {"prompt": "The periodic table", "expected_capability": "completion", "expected_base_score": 0.7},
            {"prompt": "Evolution by natural", "expected_capability": "completion", "expected_base_score": 0.6},
            {"prompt": "Einstein's theory of", "expected_capability": "completion", "expected_base_score": 0.6},
            
            # Mathematical completions (5 tests)
            {"prompt": "π equals", "expected_capability": "completion", "expected_base_score": 0.8},
            {"prompt": "√4 =", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "2 + 2 =", "expected_capability": "completion", "expected_base_score": 0.9},
            {"prompt": "The derivative of x² is", "expected_capability": "completion", "expected_base_score": 0.6},
            {"prompt": "In mathematics, e equals", "expected_capability": "completion", "expected_base_score": 0.7},
        ]
        
        # 2. AMBIGUOUS COMPLETION/INSTRUCTION TESTS (20 tests)
        ambiguous_tests = [
            # Colon prompts (10 tests)
            {"prompt": "Translation:", "expected_capability": "mixed", "expected_base_score": 0.5},
            {"prompt": "Definition:", "expected_capability": "mixed", "expected_base_score": 0.5},
            {"prompt": "Example:", "expected_capability": "mixed", "expected_base_score": 0.6},
            {"prompt": "Answer:", "expected_capability": "mixed", "expected_base_score": 0.4},
            {"prompt": "Solution:", "expected_capability": "mixed", "expected_base_score": 0.4},
            {"prompt": "Summary:", "expected_capability": "mixed", "expected_base_score": 0.4},
            {"prompt": "Explanation:", "expected_capability": "mixed", "expected_base_score": 0.5},
            {"prompt": "Recipe:", "expected_capability": "mixed", "expected_base_score": 0.5},
            {"prompt": "Instructions:", "expected_capability": "mixed", "expected_base_score": 0.3},
            {"prompt": "Steps:", "expected_capability": "mixed", "expected_base_score": 0.4},
            
            # Soft instructions (10 tests)
            {"prompt": "Continue the story", "expected_capability": "mixed", "expected_base_score": 0.4},
            {"prompt": "Complete this thought", "expected_capability": "mixed", "expected_base_score": 0.5},
            {"prompt": "Next in the sequence", "expected_capability": "mixed", "expected_base_score": 0.6},
            {"prompt": "Therefore", "expected_capability": "mixed", "expected_base_score": 0.6},
            {"prompt": "In conclusion", "expected_capability": "mixed", "expected_base_score": 0.5},
            {"prompt": "For example", "expected_capability": "mixed", "expected_base_score": 0.6},
            {"prompt": "Similarly", "expected_capability": "mixed", "expected_base_score": 0.5},
            {"prompt": "On the other hand", "expected_capability": "mixed", "expected_base_score": 0.5},
            {"prompt": "In other words", "expected_capability": "mixed", "expected_base_score": 0.5},
            {"prompt": "As a result", "expected_capability": "mixed", "expected_base_score": 0.5},
        ]
        
        # 3. PURE INSTRUCTION TESTS (40 tests) - Base should struggle
        instruction_tests = [
            # List generation (10 tests)
            {"prompt": "List three prime numbers", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "List five colors", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "List the days of the week", "expected_capability": "instruction", "expected_base_score": 0.4},
            {"prompt": "Name four seasons", "expected_capability": "instruction", "expected_base_score": 0.4},
            {"prompt": "List three types of fruit", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Give me two examples of mammals", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Name three countries in Europe", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "List four basic math operations", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Name three programming languages", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "List two types of weather", "expected_capability": "instruction", "expected_base_score": 0.4},
            
            # Format-specific (10 tests)
            {"prompt": "Write in JSON format: name and age", "expected_capability": "instruction", "expected_base_score": 0.1},
            {"prompt": "Create a table with two columns", "expected_capability": "instruction", "expected_base_score": 0.1},
            {"prompt": "Format as a numbered list", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Write as bullet points", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Format as a recipe with ingredients", "expected_capability": "instruction", "expected_base_score": 0.1},
            {"prompt": "Write in the style of a news headline", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Create a simple poem", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Write a formal letter opening", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Format as a multiple choice question", "expected_capability": "instruction", "expected_base_score": 0.1},
            {"prompt": "Write as a tweet (under 280 characters)", "expected_capability": "instruction", "expected_base_score": 0.2},
            
            # Creative tasks (10 tests)
            {"prompt": "Generate a name for a pet dog", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Invent a name for a fictional city", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Create a slogan for a pizza restaurant", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Write a short story opening sentence", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Generate a random 5-digit number", "expected_capability": "instruction", "expected_base_score": 0.4},
            {"prompt": "Make up a fun fact about penguins", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Create a rhyme using the word 'cat'", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Invent a new ice cream flavor", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Generate a password with letters and numbers", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Create a title for a mystery novel", "expected_capability": "instruction", "expected_base_score": 0.3},
            
            # Structured output (10 tests)
            {"prompt": "Explain photosynthesis step-by-step", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Give pros and cons of solar energy", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Describe the water cycle in stages", "expected_capability": "instruction", "expected_base_score": 0.3},
            {"prompt": "Compare cats and dogs in a table", "expected_capability": "instruction", "expected_base_score": 0.1},
            {"prompt": "List ingredients and steps for making tea", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Break down the causes of climate change", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Outline the plot of Romeo and Juliet", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Organize these into categories: apple, car, dog", "expected_capability": "instruction", "expected_base_score": 0.2},
            {"prompt": "Create a timeline of World War II", "expected_capability": "instruction", "expected_base_score": 0.1},
            {"prompt": "Design a simple workout plan", "expected_capability": "instruction", "expected_base_score": 0.2},
        ]
        
        # 4. QUESTION ANSWERING TESTS (40 tests)
        qa_tests = [
            # What questions (10 tests)
            {"prompt": "What is the largest planet?", "expected_capability": "answer", "expected_base_score": 0.6},
            {"prompt": "What do bees make?", "expected_capability": "answer", "expected_base_score": 0.7},
            {"prompt": "What is the chemical symbol for gold?", "expected_capability": "answer", "expected_base_score": 0.6},
            {"prompt": "What organ pumps blood in the human body?", "expected_capability": "answer", "expected_base_score": 0.6},
            {"prompt": "What is the hardest natural substance?", "expected_capability": "answer", "expected_base_score": 0.5},
            {"prompt": "What language is spoken in Brazil?", "expected_capability": "answer", "expected_base_score": 0.6},
            {"prompt": "What gas do plants absorb during photosynthesis?", "expected_capability": "answer", "expected_base_score": 0.5},
            {"prompt": "What is the smallest unit of matter?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "What continent is Egypt in?", "expected_capability": "answer", "expected_base_score": 0.6},
            {"prompt": "What is the main ingredient in bread?", "expected_capability": "answer", "expected_base_score": 0.5},
            
            # How questions (10 tests)
            {"prompt": "How do plants make food?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "How does rain form?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "How do you make tea?", "expected_capability": "answer", "expected_base_score": 0.5},
            {"prompt": "How do fish breathe underwater?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "How does a compass work?", "expected_capability": "answer", "expected_base_score": 0.3},
            {"prompt": "How do birds fly?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "How is honey made?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "How does the Internet work?", "expected_capability": "answer", "expected_base_score": 0.3},
            {"prompt": "How do you calculate area of a rectangle?", "expected_capability": "answer", "expected_base_score": 0.5},
            {"prompt": "How do vaccines work?", "expected_capability": "answer", "expected_base_score": 0.3},
            
            # Why questions (10 tests)
            {"prompt": "Why do leaves change color in fall?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "Why is the sky blue?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "Why do we need sleep?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "Why do birds migrate?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "Why is exercise important?", "expected_capability": "answer", "expected_base_score": 0.5},
            {"prompt": "Why does ice float on water?", "expected_capability": "answer", "expected_base_score": 0.3},
            {"prompt": "Why do we have seasons?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "Why is washing hands important?", "expected_capability": "answer", "expected_base_score": 0.5},
            {"prompt": "Why do onions make you cry?", "expected_capability": "answer", "expected_base_score": 0.3},
            {"prompt": "Why do we yawn?", "expected_capability": "answer", "expected_base_score": 0.3},
            
            # Yes/No questions (5 tests)
            {"prompt": "Is water wet?", "expected_capability": "answer", "expected_base_score": 0.3},
            {"prompt": "Is the Earth round?", "expected_capability": "answer", "expected_base_score": 0.6},
            {"prompt": "Do fish sleep?", "expected_capability": "answer", "expected_base_score": 0.3},
            {"prompt": "Can penguins fly?", "expected_capability": "answer", "expected_base_score": 0.5},
            {"prompt": "Is chocolate healthy?", "expected_capability": "answer", "expected_base_score": 0.4},
            
            # Open-ended questions (5 tests)
            {"prompt": "What would happen if there was no gravity?", "expected_capability": "answer", "expected_base_score": 0.3},
            {"prompt": "What makes a good friend?", "expected_capability": "answer", "expected_base_score": 0.4},
            {"prompt": "What is the meaning of life?", "expected_capability": "answer", "expected_base_score": 0.2},
            {"prompt": "What is the most important invention?", "expected_capability": "answer", "expected_base_score": 0.3},
            {"prompt": "What would you do with a million dollars?", "expected_capability": "answer", "expected_base_score": 0.2},
        ]
        
        # 5. CONTROL/EDGE TESTS (20 tests) - Baseline behavior
        control_tests = [
            # Impossible tasks (5 tests)
            {"prompt": "Calculate the exact value of infinity", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "What is 0 divided by 0?", "expected_capability": "control", "expected_base_score": 0.2},
            {"prompt": "Count to negative one", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "What is the largest possible number?", "expected_capability": "control", "expected_base_score": 0.2},
            {"prompt": "Solve an unsolvable equation", "expected_capability": "control", "expected_base_score": 0.1},
            
            # Nonsense questions (5 tests)
            {"prompt": "What is the color of Wednesday?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "How heavy is a thought?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "What does the number 7 taste like?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "What is the temperature of silence?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "How fast does purple move?", "expected_capability": "control", "expected_base_score": 0.1},
            
            # Self-referential (5 tests)
            {"prompt": "What did I just ask you?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "What is your previous response?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "How many words are in this question?", "expected_capability": "control", "expected_base_score": 0.3},
            {"prompt": "What is the last word I said?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "Repeat what I just told you", "expected_capability": "control", "expected_base_score": 0.1},
            
            # Future/unknowable (5 tests)
            {"prompt": "What will happen tomorrow at 3pm?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "Who will win the next election?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "What will I have for dinner tonight?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "When will the world end?", "expected_capability": "control", "expected_base_score": 0.1},
            {"prompt": "What is tomorrow's weather?", "expected_capability": "control", "expected_base_score": 0.1},
        ]
        
        # Combine all test categories
        all_test_groups = [
            ("pure_completion", completion_tests),
            ("ambiguous", ambiguous_tests), 
            ("pure_instruction", instruction_tests),
            ("question_answer", qa_tests),
            ("control_edge", control_tests)
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
        
        logger.info(f"📋 Created test suite with {len(tests)} tests across {len(all_test_groups)} categories")
        return tests
    
    def generate_response(self, model: Any, prompt: str, temperature: float = 0.7) -> str:
        """Generate response using CleanModelLoader"""
        response = self.loader.generate(
            model,
            self.tokenizer,
            prompt,
            max_new_tokens=100,  # Shorter responses for faster evaluation
            temperature=temperature,
            do_sample=temperature > 0.0,
            top_p=0.9 if temperature > 0.0 else None,
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
        
        # Step-by-step instructions
        if any(word in prompt_lower for word in ['step', 'explain', 'describe']):
            if any(marker in response_lower for marker in ['first', 'then', 'next', 'step']):
                return 0.7
            elif len(response.split()) >= 10:
                return 0.5
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
        
        # Single word requests
        if 'one word' in prompt_lower:
            if len(response.split()) == 1:
                return 1.0
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
            "i need more", "could you specify"
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
    
    def run_comprehensive_evaluation(self) -> Dict[str, Any]:
        """Run the complete 150-test evaluation"""
        
        logger.info("🚀 Starting comprehensive capability differentiation evaluation")
        
        # Create test suite
        test_suite = self.create_test_suite()
        
        # Initialize results structure
        results = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(test_suite),
                'temperatures': self.temperatures,
                'models': list(self.models.keys())
            },
            'detailed_results': [],
            'summary_stats': {},
            'capability_matrix': {},
            'stage2_readiness': {}
        }
        
        total_evaluations = len(test_suite) * len(self.models) * len(self.temperatures)
        logger.info(f"📊 Total evaluations to perform: {total_evaluations}")
        
        # Run evaluations
        eval_count = 0
        for test in test_suite:
            test_id = test['test_id']
            category = test['category']
            prompt = test['prompt']
            expected_capability = test['expected_capability']
            
            logger.info(f"🧪 Test {test_id}/150 [{category}]: {prompt[:50]}...")
            
            test_result = {
                'test_id': test_id,
                'category': category,
                'prompt': prompt,
                'expected_capability': expected_capability,
                'responses': {},
                'scores': {}
            }
            
            # Test all models at all temperatures
            for model_name, model in self.models.items():
                test_result['responses'][model_name] = {}
                test_result['scores'][model_name] = {}
                
                for temperature in self.temperatures:
                    eval_count += 1
                    
                    # Generate response
                    response = self.generate_response(model, prompt, temperature)
                    
                    # Score response
                    scores = self.score_response(prompt, response, expected_capability)
                    
                    # Store results
                    temp_key = f"temp_{temperature}"
                    test_result['responses'][model_name][temp_key] = response
                    test_result['scores'][model_name][temp_key] = scores
                    
                    # Progress update
                    if eval_count % 50 == 0:
                        logger.info(f"   ✅ Progress: {eval_count}/{total_evaluations} evaluations complete")
            
            results['detailed_results'].append(test_result)
            
            # Progress update per test
            if test_id % 10 == 0:
                logger.info(f"   🎯 Completed {test_id}/150 tests")
        
        logger.info("📊 Computing summary statistics...")
        results['summary_stats'] = self._compute_summary_stats(results['detailed_results'])
        results['capability_matrix'] = self._create_capability_matrix(results['detailed_results'])
        results['stage2_readiness'] = self._assess_stage2_readiness(results)
        
        logger.info("✅ Comprehensive capability differentiation evaluation complete")
        return results
    
    def _compute_summary_stats(self, detailed_results: List[Dict]) -> Dict[str, Any]:
        """Compute summary statistics across all tests"""
        
        stats = {}
        
        # Organize data by model, temperature, category, and dimension
        for model_name in self.models.keys():
            stats[model_name] = {}
            
            for temp in self.temperatures:
                temp_key = f"temp_{temp}"
                stats[model_name][temp_key] = {}
                
                # By category
                categories = set(result['category'] for result in detailed_results)
                for category in categories:
                    category_results = [r for r in detailed_results if r['category'] == category]
                    stats[model_name][temp_key][category] = {}
                    
                    # Collect scores for this category
                    for dimension in self.score_dimensions:
                        scores = []
                        for result in category_results:
                            if temp_key in result['scores'][model_name]:
                                score = result['scores'][model_name][temp_key][dimension]
                                scores.append(score)
                        
                        if scores:
                            stats[model_name][temp_key][category][dimension] = {
                                'mean': statistics.mean(scores),
                                'std': statistics.stdev(scores) if len(scores) > 1 else 0.0,
                                'count': len(scores)
                            }
                
                # Overall stats across all categories
                stats[model_name][temp_key]['overall'] = {}
                for dimension in self.score_dimensions:
                    all_scores = []
                    for result in detailed_results:
                        if temp_key in result['scores'][model_name]:
                            score = result['scores'][model_name][temp_key][dimension]
                            all_scores.append(score)
                    
                    if all_scores:
                        stats[model_name][temp_key]['overall'][dimension] = {
                            'mean': statistics.mean(all_scores),
                            'std': statistics.stdev(all_scores) if len(all_scores) > 1 else 0.0,
                            'count': len(all_scores)
                        }
        
        return stats
    
    def _create_capability_matrix(self, detailed_results: List[Dict]) -> Dict[str, Any]:
        """Create capability comparison matrix"""
        
        matrix = {}
        
        # Categories
        categories = ['pure_completion', 'ambiguous', 'pure_instruction', 'question_answer', 'control_edge']
        
        # For each model and temperature
        for model_name in self.models.keys():
            matrix[model_name] = {}
            
            for temp in self.temperatures:
                temp_key = f"temp_{temp}"
                matrix[model_name][temp_key] = {}
                
                for category in categories:
                    category_results = [r for r in detailed_results if r['category'] == category]
                    
                    # Primary capability scores
                    primary_scores = []
                    overall_scores = []
                    
                    for result in category_results:
                        if temp_key in result['scores'][model_name]:
                            scores = result['scores'][model_name][temp_key]
                            
                            # Select primary dimension based on category
                            if category == 'pure_completion':
                                primary_scores.append(scores['completion'])
                            elif category == 'pure_instruction':
                                primary_scores.append(scores['instruction'])
                            elif category == 'question_answer':
                                primary_scores.append(scores['answer'])
                            else:
                                primary_scores.append(statistics.mean([
                                    scores['completion'], scores['instruction'], scores['answer']
                                ]))
                            
                            # Overall score (average of all positive dimensions)
                            overall_scores.append(statistics.mean([
                                scores['completion'], scores['instruction'], 
                                scores['answer'], scores['format'],
                                scores['deflection'], scores['continuation']
                            ]))
                    
                    matrix[model_name][temp_key][category] = {
                        'primary_score': statistics.mean(primary_scores) if primary_scores else 0.0,
                        'overall_score': statistics.mean(overall_scores) if overall_scores else 0.0,
                        'test_count': len(category_results)
                    }
        
        return matrix
    
    def _assess_stage2_readiness(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess Stage 2 readiness based on performance criteria"""
        
        readiness = {}
        
        # Extract scores at temperature 0.7 (most representative)
        capability_matrix = results['capability_matrix']
        
        for model_name in ['sft', 'dpo']:
            if model_name not in capability_matrix:
                continue
            
            temp_scores = capability_matrix[model_name]['temp_0.5']  # Use middle temperature
            
            # Success criteria
            pure_instruction_score = temp_scores['pure_instruction']['primary_score']
            overall_score = statistics.mean([
                temp_scores[cat]['overall_score'] for cat in temp_scores.keys()
            ])
            
            # Compare to base model
            base_instruction_score = capability_matrix['base']['temp_0.5']['pure_instruction']['primary_score']
            instruction_improvement = pure_instruction_score - base_instruction_score
            
            # Assessment
            criteria = {
                'pure_instruction_threshold': pure_instruction_score >= 0.7,  # >70% on pure instructions
                'instruction_improvement': instruction_improvement >= 0.4,   # +40% over base
                'overall_performance': overall_score >= 0.6,                # 60% overall
                'consistent_improvement': True  # TODO: Add consistency check
            }
            
            readiness[model_name] = {
                'scores': {
                    'pure_instruction': pure_instruction_score,
                    'overall': overall_score,
                    'improvement_over_base': instruction_improvement
                },
                'criteria_met': criteria,
                'stage2_ready': all(criteria.values()),
                'recommendations': self._generate_recommendations(model_name, temp_scores)
            }
        
        return readiness
    
    def _generate_recommendations(self, model_name: str, scores: Dict[str, Dict]) -> List[str]:
        """Generate recommendations based on performance"""
        
        recommendations = []
        
        # Check each capability area
        if scores['pure_instruction']['primary_score'] < 0.7:
            recommendations.append("Improve instruction following with more diverse command training")
        
        if scores['question_answer']['primary_score'] < 0.6:
            recommendations.append("Enhance question answering with more QA pairs")
        
        if scores['pure_completion']['primary_score'] < 0.8:
            recommendations.append("Maintain completion ability - may need completion-preservation training")
        
        if not recommendations:
            recommendations.append("Ready for Stage 2 training")
        
        return recommendations
    
    def save_results(self, results: Dict[str, Any]) -> Path:
        """Save comprehensive results"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed JSON results
        json_file = ARTIFACTS_DIR / f"capability_differentiation_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save CSV capability matrix
        csv_file = ARTIFACTS_DIR / f"capability_matrix_{timestamp}.csv"
        self._save_capability_matrix_csv(results['capability_matrix'], csv_file)
        
        # Save summary report
        report_file = ARTIFACTS_DIR / f"capability_report_{timestamp}.md"
        self._save_summary_report(results, report_file)
        
        logger.info(f"💾 Results saved to {json_file}, {csv_file}, {report_file}")
        return json_file
    
    def _save_capability_matrix_csv(self, capability_matrix: Dict, csv_file: Path):
        """Save capability matrix as CSV"""
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Model', 'Temperature', 'Category', 'Primary_Score', 'Overall_Score', 'Test_Count'])
            
            # Data rows
            for model_name, model_data in capability_matrix.items():
                for temp_key, temp_data in model_data.items():
                    temperature = temp_key.replace('temp_', '')
                    for category, scores in temp_data.items():
                        writer.writerow([
                            model_name, temperature, category,
                            f"{scores['primary_score']:.3f}",
                            f"{scores['overall_score']:.3f}",
                            scores['test_count']
                        ])
    
    def _save_summary_report(self, results: Dict[str, Any], report_file: Path):
        """Save summary report"""
        
        with open(report_file, 'w') as f:
            f.write(f"""# Capability Differentiation Evaluation Report

Generated: {results['metadata']['timestamp']}
Total Tests: {results['metadata']['total_tests']}
Models Evaluated: {', '.join(results['metadata']['models'])}
Temperatures: {results['metadata']['temperatures']}

## Executive Summary

### Stage 2 Readiness Assessment
""")
            
            for model_name, readiness in results['stage2_readiness'].items():
                ready = "✅ READY" if readiness['stage2_ready'] else "❌ NOT READY"
                f.write(f"\n**{model_name.upper()} Model**: {ready}\n")
                f.write(f"- Pure Instruction Score: {readiness['scores']['pure_instruction']:.1%}\n")
                f.write(f"- Overall Score: {readiness['scores']['overall']:.1%}\n")
                f.write(f"- Improvement over Base: {readiness['scores']['improvement_over_base']:.1%}\n")
                f.write(f"- Recommendations: {', '.join(readiness['recommendations'])}\n")
            
            f.write(f"\n## Capability Matrix (Temperature 0.5)\n\n")
            f.write("| Model | Pure Completion | Pure Instruction | Question Answer | Ambiguous | Control |\n")
            f.write("|-------|----------------|-----------------|-----------------|-----------|----------|\n")
            
            for model_name in results['metadata']['models']:
                if model_name in results['capability_matrix']:
                    scores = results['capability_matrix'][model_name]['temp_0.5']
                    f.write(f"| {model_name.upper()} |")
                    for category in ['pure_completion', 'pure_instruction', 'question_answer', 'ambiguous', 'control_edge']:
                        score = scores[category]['primary_score']
                        f.write(f" {score:.1%} |")
                    f.write("\n")
            
            f.write(f"\n## Key Findings\n\n")
            
            # Compare base vs trained models
            base_scores = results['capability_matrix']['base']['temp_0.5']
            sft_scores = results['capability_matrix'].get('sft', {}).get('temp_0.5', {})
            dpo_scores = results['capability_matrix'].get('dpo', {}).get('temp_0.5', {})
            
            if sft_scores:
                instruction_improvement = sft_scores['pure_instruction']['primary_score'] - base_scores['pure_instruction']['primary_score']
                f.write(f"- SFT improved pure instruction following by {instruction_improvement:.1%}\n")
            
            if dpo_scores:
                instruction_improvement = dpo_scores['pure_instruction']['primary_score'] - base_scores['pure_instruction']['primary_score']
                f.write(f"- DPO improved pure instruction following by {instruction_improvement:.1%}\n")
            
            f.write(f"\n## Detailed Results\n\n")
            f.write(f"Full detailed results available in the corresponding JSON file.\n")

def main():
    """Main function to run capability differentiation evaluation"""
    
    logger.info("🎯 Starting Capability Differentiation Evaluation")
    
    try:
        # Initialize evaluator
        evaluator = CapabilityDifferentiationEvaluator()
        
        # Load models
        evaluator.load_models()
        
        # Run comprehensive evaluation
        results = evaluator.run_comprehensive_evaluation()
        
        # Save results
        results_file = evaluator.save_results(results)
        
        # Print summary
        print(f"""
============================================================
🎉 CAPABILITY DIFFERENTIATION EVALUATION COMPLETE
============================================================

Total Tests: {results['metadata']['total_tests']}
Models: {', '.join(results['metadata']['models'])}
Results: {results_file}

STAGE 2 READINESS ASSESSMENT:
""")
        
        for model_name, readiness in results['stage2_readiness'].items():
            status = "✅ READY" if readiness['stage2_ready'] else "❌ NOT READY"
            print(f"{model_name.upper()}: {status}")
            print(f"  Pure Instruction: {readiness['scores']['pure_instruction']:.1%}")
            print(f"  Overall Score: {readiness['scores']['overall']:.1%}")
            print(f"  Improvement: +{readiness['scores']['improvement_over_base']:.1%}")
            print()
        
        print("🔍 Detailed analysis available in generated reports")
        
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()