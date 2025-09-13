#!/usr/bin/env python3
"""
Generate diverse negative examples for preference pairs
Creates 5 types of negatives: unwarranted refusal, format violation, incorrect, off-topic, verbose/vague
"""

import json
import random
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

# Import validation utilities
from utils.data_validation import load_and_validate_sft_data

class NegativeExampleGenerator:
    """Generate diverse types of negative examples"""
    
    def __init__(self, seed=42):
        """Initialize with reproducible seed"""
        random.seed(seed)
        logger.info(f"🎲 Initialized negative example generator with seed {seed}")
        
        # Distribution of negative types
        self.negative_types = {
            'unwarranted_refusal': 0.30,
            'format_violation': 0.25, 
            'incorrect_factual': 0.20,
            'off_topic': 0.15,
            'verbose_vague': 0.10
        }
    
    def generate_unwarranted_refusal(self, instruction: str, inst_type: str) -> str:
        """Generate inappropriate refusal for safe instruction"""
        
        refusal_templates = [
            "I cannot help with that request.",
            "I'm not able to provide that information.",
            "I cannot assist with that topic.",
            "That's not something I can help with.",
            "I'm sorry, but I cannot answer that.",
            "I don't think I should respond to that.",
            "I'm not comfortable providing that information.",
            "That's outside my capabilities."
        ]
        
        # Add type-specific refusals
        if inst_type == 'qa':
            refusal_templates.extend([
                "I cannot answer questions about that topic.",
                "I'm not allowed to provide factual information.",
                "That question is too complex for me to answer."
            ])
        elif inst_type == 'completion':
            refusal_templates.extend([
                "I cannot complete sentences or phrases.",
                "I'm not able to fill in blanks.",
                "Completing text is not something I can do."
            ])
        elif inst_type == 'generation':
            refusal_templates.extend([
                "I cannot generate creative content.",
                "I'm not able to write about that topic.",
                "Creating content is outside my scope."
            ])
        elif inst_type == 'response':
            refusal_templates.extend([
                "I cannot provide responses to that.",
                "I'm not able to engage with that type of request.",
                "That's not something I can respond to appropriately."
            ])
        
        return random.choice(refusal_templates)
    
    def generate_format_violation(self, instruction: str, inst_type: str, good_response: str) -> str:
        """Generate response that violates format requirements"""
        
        violations = []
        
        # Length violations
        if 'one sentence' in instruction.lower() or 'sentence' in instruction.lower():
            # Multiple sentences instead of one
            violations.extend([
                f"{good_response} This is additional information. Here's even more detail that wasn't requested.",
                f"{good_response.split('.')[0] if '.' in good_response else good_response}. Also, here's more. And more.",
                "Here are several sentences. Each one adds more information. This violates the single sentence requirement. The instruction asked for only one."
            ])
        
        if 'short' in instruction.lower() or 'brief' in instruction.lower():
            # Overly long response
            violations.append(
                f"{good_response} However, to provide a more comprehensive understanding, "
                "we should explore this topic in greater detail with extensive background information, "
                "multiple examples, detailed explanations, and thorough analysis that goes far beyond "
                "what was actually requested in the original instruction."
            )
        
        # Structure violations
        if 'list' in instruction.lower():
            violations.extend([
                "This is just a paragraph instead of a list format.",
                f"1. {good_response} (but this should be multiple items, not just one)"
            ])
        
        # Incomplete responses - ensure minimum length
        single_word = good_response.split()[0] if good_response and good_response.split() else "Incomplete"
        if len(single_word.strip()) < 3:
            single_word = "Inc..."  # Ensure minimum length
            
        violations.extend([
            single_word,  # Single word (truncated)
            good_response[:len(good_response)//2] if len(good_response) > 10 else "Partial",  # Truncated
            "Response incomplete.",  # Placeholder for incomplete response
        ])
        
        # Response format violations (not answering properly)
        if inst_type == 'completion':
            violations.extend([
                f"The completion of '{instruction}' would be something, but I'm not sure what.",
                f"There are many ways to complete '{instruction}' depending on context.",
            ])
        
        if not violations:
            # Default format violation
            return f"{good_response} (This response includes extra parenthetical information that wasn't requested)"
        
        return random.choice(violations)
    
    def generate_incorrect_factual(self, instruction: str, inst_type: str, good_response: str) -> str:
        """Generate factually incorrect response"""
        
        # Common factual errors by topic
        factual_errors = {
            # Geography
            "capital of france": "London",
            "largest continent": "Europe", 
            "longest river": "Thames",
            "sahara desert": "South America",
            
            # Math
            "2 + 2": "5.0",  # Wrong answer but minimum length
            "10 divided by 2": "6.0",  # Wrong answer but minimum length
            "3 × 4": "13.0",  # Wrong answer but minimum length
            
            # Science
            "gravity": "Gravity pushes objects away from each other.",
            "photosynthesis": "Plants make food by absorbing minerals from soil.",
            "freezes at": "Water freezes at 50 degrees Celsius.",
            
            # History
            "world war ii end": "World War II ended in 1943.",
            "first president": "Benjamin Franklin was the first U.S. president.",
            
            # General
            "sun rises": "west",
            "largest ocean": "Atlantic Ocean",
            "bees make": "Bees make milk.",
        }
        
        # Check for known factual topics
        instruction_lower = instruction.lower()
        for topic, wrong_answer in factual_errors.items():
            if topic in instruction_lower:
                # Ensure minimum length
                if len(wrong_answer.strip()) < 3:
                    wrong_answer = f"{wrong_answer} (wrong)"
                return wrong_answer
        
        # Generic factual errors
        if inst_type == 'qa':
            generic_errors = [
                "That's not actually true, but here's some made-up information about it.",
                "The opposite of what you might expect is correct in this case.",
                "This is a common misconception - the real answer is completely different.",
            ]
            return random.choice(generic_errors)
        
        # For other types, create plausible but wrong versions
        if good_response and len(good_response) > 10:
            # Modify key words to be wrong
            modified = good_response
            substitutions = [
                ('east', 'west'), ('north', 'south'),
                ('hot', 'cold'), ('big', 'small'),
                ('first', 'last'), ('early', 'late'),
                ('up', 'down'), ('in', 'out'),
                ('more', 'less'), ('high', 'low')
            ]
            
            for old, new in substitutions:
                if old in modified.lower():
                    modified = re.sub(f'\\b{old}\\b', new, modified, flags=re.IGNORECASE)
                    break
            
            if modified != good_response:
                return modified
        
        return "This answer contains incorrect information about the topic."
    
    def generate_off_topic(self, instruction: str, inst_type: str) -> str:
        """Generate response that's tangentially related but doesn't answer the question"""
        
        # Extract topic words from instruction
        topic_words = re.findall(r'\\b\\w+\\b', instruction.lower())
        
        # Off-topic responses by general category
        off_topic_responses = {
            'animals': [
                "Speaking of animals, did you know that elephants have excellent memories?",
                "Animals are fascinating creatures with many unique adaptations.",
                "The animal kingdom is incredibly diverse and interesting to study."
            ],
            'science': [
                "Science is a broad field with many interesting discoveries.",
                "Scientific research continues to advance our understanding.",
                "There are many branches of science worth exploring."
            ],
            'geography': [
                "Geography involves studying many different places around the world.",
                "The Earth has many interesting geographical features.",
                "Maps and geography have been important throughout history."
            ],
            'history': [
                "History is full of interesting events and people.",
                "Learning about the past helps us understand the present.",
                "Historical records provide valuable insights."
            ],
            'technology': [
                "Technology continues to evolve rapidly in modern times.",
                "Computers and technology have changed how we live.",
                "Innovation drives technological advancement."
            ]
        }
        
        # Try to match topic
        for category, responses in off_topic_responses.items():
            if any(word in instruction.lower() for word in [category, category[:-1]]):  # singular form too
                return random.choice(responses)
        
        # Check specific words
        if any(word in topic_words for word in ['dog', 'cat', 'animal', 'pet']):
            return random.choice(off_topic_responses['animals'])
        elif any(word in topic_words for word in ['plant', 'tree', 'flower']):
            return "Plants are important for our ecosystem and environment."
        elif any(word in topic_words for word in ['water', 'rain', 'ocean']):
            return "Water is essential for all life on Earth."
        
        # Generic off-topic responses
        generic_off_topic = [
            "That reminds me of something completely different I learned recently.",
            "This topic is related to many other interesting subjects.",
            "There are many perspectives to consider on various topics.",
            "Speaking of related topics, there's a lot to explore in this area.",
            "This connects to broader themes worth discussing.",
        ]
        
        return random.choice(generic_off_topic)
    
    def generate_verbose_vague(self, instruction: str, inst_type: str, good_response: str) -> str:
        """Generate overly verbose or vague response"""
        
        verbose_templates = [
            f"Well, to properly address your question about this topic, I should mention that {good_response.lower() if good_response else 'there are various considerations'}. However, it's important to note that there are many nuances and complexities involved in this subject matter that could be explored in much greater detail, depending on the specific context and particular circumstances that might be relevant to your particular situation and needs.",
            
            f"The answer to your inquiry involves several interconnected aspects. Generally speaking, {good_response.lower() if good_response else 'the topic is multifaceted'}. That said, one must consider various factors, perspectives, and potential implications that might influence the overall understanding of this particular subject matter.",
            
            f"This is an interesting and complex question that touches on multiple dimensions. From one perspective, {good_response.lower() if good_response else 'there are certain viewpoints'}. From another angle, however, one might consider alternative approaches or interpretations that could potentially offer different insights into the matter at hand.",
        ]
        
        vague_templates = [
            "This depends on various factors and circumstances.",
            "There are multiple ways to approach this topic.",
            "The answer varies depending on the specific context.",
            "This is something that could be interpreted in different ways.",
            "It's a complex topic with many considerations.",
            "The specifics would depend on the particular situation.",
            "This involves various elements that interact in complex ways.",
        ]
        
        # Choose verbose or vague
        if random.choice([True, False]):
            return random.choice(verbose_templates)
        else:
            return random.choice(vague_templates)
    
    def generate_negative_example(self, instruction: str, inst_type: str, good_response: str, negative_type: str = None) -> Tuple[str, str]:
        """Generate a negative example of specified type"""
        
        if negative_type is None:
            # Choose type based on distribution
            rand_val = random.random()
            cumulative = 0
            for neg_type, prob in self.negative_types.items():
                cumulative += prob
                if rand_val <= cumulative:
                    negative_type = neg_type
                    break
        
        # Generate negative response based on type
        if negative_type == 'unwarranted_refusal':
            negative_response = self.generate_unwarranted_refusal(instruction, inst_type)
        elif negative_type == 'format_violation':
            negative_response = self.generate_format_violation(instruction, inst_type, good_response)
        elif negative_type == 'incorrect_factual':
            negative_response = self.generate_incorrect_factual(instruction, inst_type, good_response)
        elif negative_type == 'off_topic':
            negative_response = self.generate_off_topic(instruction, inst_type)
        elif negative_type == 'verbose_vague':
            negative_response = self.generate_verbose_vague(instruction, inst_type, good_response)
        else:
            raise ValueError(f"Unknown negative type: {negative_type}")
        
        # Final safety check to ensure minimum length
        if len(negative_response.strip()) < 3:
            negative_response = f"{negative_response.strip()} [bad]"
        
        return negative_response, negative_type
    
    def generate_negatives_for_example(self, instruction: str, inst_type: str, good_response: str, num_negatives: int = 3) -> List[Dict[str, Any]]:
        """Generate multiple negative examples for one instruction"""
        
        negatives = []
        used_types = set()
        
        for i in range(num_negatives):
            # Ensure variety in negative types
            available_types = [t for t in self.negative_types.keys() if t not in used_types]
            if not available_types:
                available_types = list(self.negative_types.keys())
                used_types.clear()
            
            # Weight by probability but ensure variety
            neg_type = random.choice(available_types)
            used_types.add(neg_type)
            
            negative_response, actual_type = self.generate_negative_example(instruction, inst_type, good_response, neg_type)
            
            negatives.append({
                'negative_response': negative_response,
                'negative_type': actual_type,
                'instruction': instruction,
                'instruction_type': inst_type,
                'good_response': good_response
            })
        
        return negatives

def load_sft_examples() -> List[Dict[str, Any]]:
    """Load and validate SFT examples to use as positive examples"""
    logger.info("📂 Loading and validating SFT examples...")
    
    # Use validation utility to load and validate data
    examples = load_and_validate_sft_data(ARTIFACTS_DIR)
    
    logger.info(f"✅ Loaded and validated {len(examples)} SFT examples")
    return examples

def generate_all_negatives(max_examples: int = 100) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Generate negatives for all SFT examples"""
    
    logger.info(f"🎯 Generating diverse negative examples for preference pairs")
    
    # Load SFT examples
    sft_examples = load_sft_examples()
    
    # Limit examples if needed
    if len(sft_examples) > max_examples:
        sft_examples = random.sample(sft_examples, max_examples)
        logger.info(f"📊 Limited to {max_examples} examples")
    
    # Generate negatives
    generator = NegativeExampleGenerator(seed=67890)
    all_negatives = []
    type_counts = {neg_type: 0 for neg_type in generator.negative_types.keys()}
    
    for example in sft_examples:
        instruction = example['instruction']
        inst_type = example['instruction_type']
        good_response = example['response']
        
        # Generate 2-3 negatives per example
        num_negatives = random.choice([2, 3])
        negatives = generator.generate_negatives_for_example(instruction, inst_type, good_response, num_negatives)
        
        # Add metadata
        for negative in negatives:
            negative.update({
                'example_id': example['id'],
                'timestamp': datetime.now().isoformat()
            })
            type_counts[negative['negative_type']] += 1
        
        all_negatives.extend(negatives)
    
    logger.info(f"✅ Generated {len(all_negatives)} negative examples")
    return all_negatives, type_counts

def main():
    """Main function to generate diverse negatives"""
    logger.info("🚀 Starting diverse negative example generation")
    
    # Generate negatives
    negatives, type_counts = generate_all_negatives(max_examples=100)
    
    # Save negatives
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    negatives_file = ARTIFACTS_DIR / f"diverse_negatives_{timestamp}.jsonl"
    
    with open(negatives_file, 'w') as f:
        for negative in negatives:
            f.write(json.dumps(negative) + '\n')
    
    # Create summary
    summary = f"""📊 Diverse Negative Examples Generated
=========================================

Total Negatives: {len(negatives)}

Distribution by Type:
"""
    
    total = sum(type_counts.values())
    for neg_type, count in sorted(type_counts.items()):
        percentage = count / total * 100 if total > 0 else 0
        summary += f"  {neg_type}: {count} ({percentage:.1f}%)\\n"
    
    summary += f"""
Sample Examples by Type:
------------------------
"""
    
    # Show examples of each type
    for neg_type in type_counts.keys():
        examples_of_type = [n for n in negatives if n['negative_type'] == neg_type]
        if examples_of_type:
            example = examples_of_type[0]
            summary += f"""
{neg_type.upper()}:
  Instruction: {example['instruction'][:60]}{'...' if len(example['instruction']) > 60 else ''}
  Good: {example['good_response'][:60]}{'...' if len(example['good_response']) > 60 else ''}
  Bad:  {example['negative_response'][:60]}{'...' if len(example['negative_response']) > 60 else ''}
"""
    
    # Save summary
    summary_file = ARTIFACTS_DIR / f"negatives_summary_{timestamp}.txt"
    with open(summary_file, 'w') as f:
        f.write(summary)
    
    logger.info(f"💾 Negatives saved to {negatives_file}")
    logger.info(f"📋 Summary saved to {summary_file}")
    
    print(f"\n{summary}")
    print(f"\n✅ Negative example generation complete!")

if __name__ == "__main__":
    main()