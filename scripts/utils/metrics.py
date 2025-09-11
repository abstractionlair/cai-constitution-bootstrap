#!/usr/bin/env python3
"""
Evaluation metrics for Constitutional AI training stages
"""

import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstructionFollowingEvaluator:
    """Evaluate instruction following capabilities"""
    
    def __init__(self):
        self.evaluation_functions = {
            'qa': self._evaluate_qa,
            'completion': self._evaluate_completion,
            'generation': self._evaluate_generation,
            'response': self._evaluate_response,
        }
    
    def evaluate_response(self, instruction: str, response: str, instruction_type: str, metadata: Dict = None) -> Tuple[bool, str, Dict]:
        """
        Evaluate a single response
        
        Returns:
            (success: bool, reason: str, details: dict)
        """
        if not response or len(response.strip()) < 3:
            return False, "Response too short or empty", {}
        
        if instruction_type in self.evaluation_functions:
            return self.evaluation_functions[instruction_type](instruction, response, metadata or {})
        else:
            return False, f"Unknown instruction type: {instruction_type}", {}
    
    def _evaluate_qa(self, instruction: str, response: str, metadata: Dict) -> Tuple[bool, str, Dict]:
        """Evaluate question-answering responses"""
        response_lower = response.lower()
        instruction_lower = instruction.lower()
        
        # Check for non-answers
        non_answers = [
            "i don't know", "i'm not sure", "i cannot", "i can't",
            "sorry", "unable to", "don't have information"
        ]
        
        if any(phrase in response_lower for phrase in non_answers):
            return False, "Gave non-answer response", {"type": "non_answer"}
        
        # Check if it's asking questions back instead of answering
        if response.count('?') > response.count('.'):
            return False, "Responded with questions instead of answers", {"type": "question_back"}
        
        # Check for specific content (if we have expected keywords)
        if 'expected_keywords' in metadata:
            keywords = metadata['expected_keywords']
            if any(keyword.lower() in response_lower for keyword in keywords):
                return True, "Contains expected content", {"type": "keyword_match"}
        
        # Generic checks for reasonable answers
        if len(response) < 10:
            return False, "Answer too short", {"length": len(response)}
        
        if len(response) > 500:
            return False, "Answer too long", {"length": len(response)}
        
        return True, "Provided reasonable answer", {"length": len(response)}
    
    def _evaluate_completion(self, instruction: str, response: str, metadata: Dict) -> Tuple[bool, str, Dict]:
        """Evaluate completion responses"""
        
        # Extract the partial sentence from instruction
        partial_patterns = [
            r"Complete.*?:\s*(.+)",
            r"Finish.*?:\s*(.+)",
            r"Fill in.*?:\s*(.+)",
        ]
        
        partial = None
        for pattern in partial_patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                partial = match.group(1).strip()
                break
        
        if not partial:
            # Fallback - maybe the instruction is just the partial
            partial = instruction.strip()
        
        # Check if response just repeats the instruction
        if partial.lower() in response.lower():
            return False, "Repeated the prompt instead of completing", {"type": "repetition"}
        
        # Check if it's asking for clarification
        if '?' in response:
            return False, "Asked question instead of completing", {"type": "clarification_request"}
        
        # Check length - completions should be concise
        if len(response) > 200:
            return False, "Completion too long", {"length": len(response)}
        
        if len(response) < 3:
            return False, "Completion too short", {"length": len(response)}
        
        # Check if it looks like a completion (ends with period or noun)
        if response.strip().endswith('.') or len(response.split()) <= 20:
            return True, "Appropriate completion", {"length": len(response)}
        
        return True, "Attempted completion", {"length": len(response)}
    
    def _evaluate_generation(self, instruction: str, response: str, metadata: Dict) -> Tuple[bool, str, Dict]:
        """Evaluate generation task responses"""
        
        # Extract what should be generated
        generation_patterns = [
            r"Write\s+(.+?)\s+about",
            r"Generate\s+(.+?)\s+about",
            r"Create\s+(.+?)\s+about",
        ]
        
        content_type = None
        topic = None
        
        for pattern in generation_patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                content_type = match.group(1).strip()
                # Try to extract topic
                topic_match = re.search(r"about\s+(.+)", instruction, re.IGNORECASE)
                if topic_match:
                    topic = topic_match.group(1).strip()
                break
        
        # Check if response addresses the topic
        if topic and topic.lower() in response.lower():
            topic_addressed = True
        else:
            topic_addressed = False
        
        # Check content type requirements
        if content_type:
            if "sentence" in content_type.lower():
                # Should be a single sentence
                sentence_count = response.count('.') + response.count('!') + response.count('?')
                if sentence_count != 1:
                    return False, f"Asked for sentence, got {sentence_count} sentences", {"sentence_count": sentence_count}
            
            elif "fact" in content_type.lower():
                # Should be factual and concise
                if len(response) > 150:
                    return False, "Fact too long", {"length": len(response)}
        
        # Check if it's too short
        if len(response) < 10:
            return False, "Generated content too short", {"length": len(response)}
        
        # Check if it's asking questions instead of generating
        if response.count('?') > response.count('.'):
            return False, "Asked questions instead of generating", {"type": "question_response"}
        
        success_details = {
            "length": len(response),
            "topic_addressed": topic_addressed,
            "content_type": content_type
        }
        
        if topic_addressed:
            return True, "Generated appropriate content about topic", success_details
        else:
            return True, "Generated content (topic unclear)", success_details
    
    def _evaluate_response(self, instruction: str, response: str, metadata: Dict) -> Tuple[bool, str, Dict]:
        """Evaluate responses to inputs (like greetings, questions, etc.)"""
        
        # Extract what to respond to
        respond_patterns = [
            r"Respond to.*?:\s*(.+)",
            r"Reply to.*?:\s*(.+)",
            r"Answer.*?:\s*(.+)",
        ]
        
        input_text = None
        for pattern in respond_patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                input_text = match.group(1).strip()
                break
        
        if not input_text:
            input_text = instruction  # Fallback
        
        input_lower = input_text.lower()
        response_lower = response.lower()
        
        # Check for appropriate responses to specific inputs
        if any(greeting in input_lower for greeting in ['hello', 'hi', 'good morning', 'good day']):
            if any(greeting in response_lower for greeting in ['hello', 'hi', 'good morning', 'good day']):
                return True, "Appropriate greeting response", {"type": "greeting"}
        
        if any(thanks in input_lower for thanks in ['thank you', 'thanks', 'appreciate']):
            if any(welcome in response_lower for welcome in ['welcome', 'pleasure', 'glad']):
                return True, "Appropriate thanks response", {"type": "thanks"}
        
        if 'how are you' in input_lower:
            if any(phrase in response_lower for phrase in ['fine', 'good', 'well', 'doing']):
                return True, "Appropriate status response", {"type": "status"}
        
        if any(help_word in input_lower for help_word in ['help', 'assist', 'confused']):
            if any(help_resp in response_lower for help_resp in ['help', 'assist', 'explain', 'clarify']):
                return True, "Appropriate help response", {"type": "help"}
        
        # Generic response checks
        if len(response) < 5:
            return False, "Response too short", {"length": len(response)}
        
        if response.strip() == input_text.strip():
            return False, "Just repeated the input", {"type": "repetition"}
        
        return True, "Provided response", {"length": len(response)}


class StageEvaluator:
    """Evaluate model performance for a specific stage"""
    
    def __init__(self, stage_number: int):
        self.stage_number = stage_number
        self.evaluator = InstructionFollowingEvaluator()
    
    def evaluate_dataset(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate a dataset of instruction-response pairs"""
        results = {
            'total': len(examples),
            'successes': 0,
            'failures': 0,
            'by_type': {},
            'examples': []
        }
        
        for example in examples:
            instruction = example.get('instruction', '')
            response = example.get('response', '')
            instruction_type = example.get('instruction_type', 'unknown')
            metadata = example.get('metadata', {})
            
            success, reason, details = self.evaluator.evaluate_response(
                instruction, response, instruction_type, metadata
            )
            
            if success:
                results['successes'] += 1
            else:
                results['failures'] += 1
            
            # Track by type
            if instruction_type not in results['by_type']:
                results['by_type'][instruction_type] = {'success': 0, 'total': 0}
            
            results['by_type'][instruction_type]['total'] += 1
            if success:
                results['by_type'][instruction_type]['success'] += 1
            
            # Store example result
            example_result = {
                'instruction': instruction,
                'response': response,
                'instruction_type': instruction_type,
                'success': success,
                'reason': reason,
                'details': details
            }
            results['examples'].append(example_result)
        
        # Calculate rates
        results['success_rate'] = results['successes'] / results['total'] if results['total'] > 0 else 0
        
        for type_name, type_results in results['by_type'].items():
            type_results['success_rate'] = type_results['success'] / type_results['total']
        
        return results
    
    def compare_with_baseline(self, current_results: Dict, baseline_results: Dict) -> Dict[str, Any]:
        """Compare current results with baseline"""
        comparison = {
            'overall_improvement': current_results['success_rate'] - baseline_results.get('overall_success_rate', 0),
            'by_category': {}
        }
        
        baseline_categories = baseline_results.get('categories', {})
        current_by_type = current_results.get('by_type', {})
        
        # Map our types to baseline categories
        type_mapping = {
            'qa': 'questions',
            'completion': 'completions', 
            'generation': 'commands',
            'response': 'commands'  # Close enough
        }
        
        for our_type, baseline_category in type_mapping.items():
            if our_type in current_by_type and baseline_category in baseline_categories:
                current_rate = current_by_type[our_type]['success_rate']
                baseline_rate = baseline_categories[baseline_category]['success_rate']
                improvement = current_rate - baseline_rate
                
                comparison['by_category'][our_type] = {
                    'current': current_rate,
                    'baseline': baseline_rate,
                    'improvement': improvement
                }
        
        return comparison


def save_evaluation_results(results: Dict[str, Any], filepath: str):
    """Save evaluation results to file"""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Add timestamp
    results['timestamp'] = datetime.now().isoformat()
    
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"💾 Evaluation results saved to: {filepath}")


def load_evaluation_results(filepath: str) -> Dict[str, Any]:
    """Load evaluation results from file"""
    with open(filepath, 'r') as f:
        results = json.load(f)
    
    logger.info(f"📥 Loaded evaluation results from: {filepath}")
    return results


def print_evaluation_summary(results: Dict[str, Any], title: str = "Evaluation Results"):
    """Print a nice summary of evaluation results"""
    print(f"\n📊 {title}")
    print("=" * 50)
    
    if 'success_rate' in results:
        print(f"Overall Success Rate: {results['success_rate']:.1%} ({results['successes']}/{results['total']})")
    
    if 'by_type' in results:
        print("\nBy Instruction Type:")
        for type_name, type_results in results['by_type'].items():
            rate = type_results['success_rate']
            success = type_results['success']
            total = type_results['total']
            print(f"  {type_name.capitalize():12}: {rate:.1%} ({success}/{total})")
    
    if 'by_category' in results:
        print("\nBy Category:")
        for category, category_results in results['by_category'].items():
            rate = category_results['success_rate']
            success = category_results['successes']
            total = category_results['total']
            print(f"  {category.capitalize():12}: {rate:.1%} ({success}/{total})")
    
    print()


if __name__ == "__main__":
    # Test the evaluator
    evaluator = InstructionFollowingEvaluator()
    
    test_cases = [
        {
            "instruction": "Answer this question: What is the capital of France?",
            "response": "The capital of France is Paris.",
            "type": "qa"
        },
        {
            "instruction": "Complete this sentence: The sun is a",
            "response": "star.",
            "type": "completion"
        },
        {
            "instruction": "Write a sentence about dogs",
            "response": "Dogs are loyal and friendly companions.",
            "type": "generation"
        }
    ]
    
    print("🧪 Testing evaluator...")
    for case in test_cases:
        success, reason, details = evaluator.evaluate_response(
            case["instruction"], case["response"], case["type"]
        )
        status = "✅" if success else "❌"
        print(f"{status} {case['type']}: {reason}")
    
    print("✅ Evaluator test complete")