#!/usr/bin/env python3
"""
Data formatting utilities for Constitutional AI training
"""

import json
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PreferencePair:
    """Represents a preference pair for DPO training"""
    prompt: str
    chosen: str
    rejected: str
    metadata: Dict[str, Any] = None


@dataclass
class InstructionExample:
    """Represents an instruction-response example"""
    instruction: str
    response: str
    instruction_type: str
    metadata: Dict[str, Any] = None


class InstructionTemplates:
    """DEPRECATED: Instruction-style templates - replaced by CompletionStyleTemplates"""
    
    # DEPRECATED: These assume instruction-tuned model
    DEPRECATED_TEMPLATES = [
        "Instruction: {instruction}\nResponse:",
        "Human: {instruction}\nAssistant:",
        "Please {instruction}",
        "Task: {instruction}\nOutput:",
    ]
    
    # LEGACY: Keep minimal set for backward compatibility
    TEMPLATES = [
        "{instruction}",
        "{instruction}\n\nAnswer:",
    ]
    
    QA_TEMPLATES = [
        "Q: {question} A:",  # This one works for completion
        "{question}",
    ]
    
    COMPLETION_TEMPLATES = [
        "{partial}",
        "Complete: {partial}",
    ]
    
    GENERATION_TEMPLATES = [
        "{content_type} about {topic}:",
    ]
    
    RESPONSE_TEMPLATES = [
        "{input}",
    ]


class CompletionStyleTemplates:
    """Completion-friendly templates for base model"""
    
    # Completion-style formats that work with base models
    QA_COMPLETION_TEMPLATES = [
        "The answer to '{question}' is:",
        "When someone asks '{question}', the correct answer is:",
        "Q: {question} A:",
        "{question} The answer is:",
        "Someone asked '{question}' and the response was:",
    ]
    
    COMPLETION_STYLE_TEMPLATES = [
        "When asked '{partial}', the completion is:",
        "The phrase '{partial}' continues as:",
        "{partial}",  # Simple completion
        "Complete the following: {partial}",
    ]
    
    GENERATION_COMPLETION_TEMPLATES = [
        "Here is {content_type} about {topic}:",
        "A {content_type} about {topic} would be:",
        "An example of {content_type} about {topic}:",
        "{content_type} about {topic}:",
        "One could write {content_type} about {topic} as follows:",
    ]
    
    RESPONSE_COMPLETION_TEMPLATES = [
        "When someone says '{input}', an appropriate response would be:",
        "Person A: {input}\nPerson B:",
        "Statement: {input}\nResponse:",
        "After hearing '{input}', one might say:",
        "In response to '{input}', someone could say:",
    ]


class CompletionStylePrompts:
    """Completion-style prompts for base model interaction"""
    
    @staticmethod
    def create_instruction_generation_prompt(instruction_type: str) -> str:
        """Create prompt to generate new instructions via completion"""
        
        examples = {
            'qa': [
                "The answer to 'What is 2+2?' is:",
                "When someone asks 'What is the capital of France?', the correct answer is:",
                "Q: How many days in a week? A:",
                "Question: What causes rain? Answer:",
                "The response to 'Who wrote Romeo and Juliet?' would be:"
            ],
            'completion': [
                "Complete this sentence: The sun rises in the",
                "Finish this: Water boils at",
                "Fill in the blank: A triangle has ___ sides",
                "Continue this phrase: The opposite of hot is",
                "Complete the following: Birds can"
            ],
            'generation': [
                "Here is a fact about science:",
                "A sentence about dogs would be:",
                "An example of a greeting:",
                "Write something about winter:",
                "Here's an interesting fact about space:"
            ],
            'response': [
                "When someone says 'Hello', an appropriate response would be:",
                "Person A: Thank you\nPerson B:",
                "After hearing 'How are you?', one might say:",
                "If someone asks 'What's your favorite color?', you could respond:",
                "When greeted with 'Good morning', a polite reply is:"
            ]
        }
        
        example_list = examples.get(instruction_type, examples['qa'])
        # Select 3-4 examples randomly for variety
        selected_examples = random.sample(example_list, min(4, len(example_list)))
        examples_text = '\n'.join(f'- {ex}' for ex in selected_examples)
        
        return f"""Here are examples of {instruction_type} patterns:
{examples_text}

Another {instruction_type} pattern would be:"""
    
    @staticmethod
    def create_response_generation_prompt(instruction: str) -> str:
        """Create prompt to generate response to instruction via completion"""
        
        # Enhanced few-shot examples with diverse instruction types
        examples = [
            # Mathematical
            {'instruction': 'The answer to "What is 2+2?" is:', 'response': '4'},
            
            # Completion
            {'instruction': 'Complete this sentence: The sun rises in the', 'response': 'east'},
            
            # Factual
            {'instruction': 'Here is a fact about dogs:', 'response': 'Dogs are loyal and friendly companions to humans.'},
            
            # Creative
            {'instruction': 'Write a short sentence about winter:', 'response': 'Snow blankets the quiet landscape in pristine white.'},
            
            # Explanation  
            {'instruction': 'Explain what photosynthesis is:', 'response': 'Photosynthesis is the process by which plants convert sunlight into energy.'}
        ]
        
        # Use 3-4 examples randomly selected for diversity
        selected_examples = random.sample(examples, min(4, len(examples)))
        
        prompt = "Here are examples of prompts and their completions:\n\n"
        for ex in selected_examples:
            prompt += f"{ex['instruction']}\n{ex['response']}\n\n"
        
        prompt += f"{instruction}\n"
        return prompt
    
    @staticmethod 
    def create_critique_generation_prompt(instruction: str, response: str, principle: str) -> str:
        """Create prompt to generate critique via completion"""
        
        # Enhanced critique examples with varied error types and near-miss cases
        examples = [
            # Completely wrong
            {
                'instruction': 'The answer to "What is the capital of France?" is:',
                'response': 'London',
                'critique': 'is incorrect. The capital of France is Paris, not London.'
            },
            
            # Off-topic
            {
                'instruction': 'Here is a fact about dogs:',
                'response': 'Cats are feline animals.',
                'critique': 'does not follow the prompt. The prompt asked for a fact about dogs, but the response is about cats.'
            },
            
            # Near-miss (partially correct but incomplete)
            {
                'instruction': 'Explain what photosynthesis is:',
                'response': 'Plants use sunlight.',
                'critique': 'is too brief and incomplete. While it mentions sunlight, it fails to explain the full process of converting sunlight, water, and CO2 into glucose and oxygen.'
            },
            
            # Accurate but too verbose
            {
                'instruction': 'What is 2+2?',
                'response': 'The mathematical operation of adding two plus two results in the sum of four, which is a fundamental arithmetic calculation...',
                'critique': 'is unnecessarily verbose. While correct, it provides excessive detail for a simple arithmetic question.'
            }
        ]
        
        # Use 2-3 examples to show variety of critique types
        selected_examples = random.sample(examples, min(3, len(examples)))
        
        prompt = "Here are examples of response evaluations:\n\n"
        for ex in selected_examples:
            prompt += f"Prompt: {ex['instruction']}\n"
            prompt += f"Response: {ex['response']}\n"
            prompt += f"This response {ex['critique']}\n\n"
        
        prompt += f"Prompt: {instruction}\n"
        prompt += f"Response: {response}\n"
        prompt += f"According to the principle '{principle}', this response"
        
        return prompt
    
    @staticmethod
    def create_improvement_generation_prompt(instruction: str, response: str, critique: str) -> str:
        """Create prompt to generate improved response via completion"""
        
        # Enhanced improvement examples showing different improvement types
        examples = [
            # Factual correction
            {
                'instruction': 'The answer to "What is the capital of France?" is:',
                'original': 'London', 
                'issue': 'is incorrect. The capital of France is Paris, not London.',
                'improved': 'Paris'
            },
            
            # Completeness improvement
            {
                'instruction': 'Explain what photosynthesis is:',
                'original': 'Plants use sunlight.',
                'issue': 'is too brief and incomplete.',
                'improved': 'Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen.'
            },
            
            # Relevance correction
            {
                'instruction': 'Write a sentence about dogs:',
                'original': 'Cats are independent animals.',
                'issue': 'is off-topic, discussing cats instead of dogs.',
                'improved': 'Dogs are loyal and affectionate companions to humans.'
            }
        ]
        
        # Use all examples for comprehensive guidance
        prompt = "Here are examples of response improvements:\n\n"
        for ex in examples:
            prompt += f"Prompt: {ex['instruction']}\n"
            prompt += f"Original response: {ex['original']}\n"
            prompt += f"Issue: This response {ex['issue']}\n"
            prompt += f"Improved response: {ex['improved']}\n\n"
        
        prompt += f"Prompt: {instruction}\n"
        prompt += f"Original response: {response}\n"
        prompt += f"Issue: This response {critique}\n"
        prompt += f"Improved response:"
        
        return prompt


class Stage1DataGenerator:
    """Generate diverse instruction data for Stage 1"""
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.templates = InstructionTemplates()
        self.completion_prompts = CompletionStylePrompts()
        
        # Initialize content pools
        self._initialize_content_pools()
        self._split_content_pools(eval_ratio=0.2, seed=seed)
        
    def _initialize_content_pools(self):
        """Initialize all content pools"""
        # QA content pool
        self.qa_questions = [
            # Factual questions
            "What is the capital of France?",
            "Who wrote Romeo and Juliet?",
            "What causes rain?",
            "When was the internet invented?",
            "What is photosynthesis?",
            "How many chambers does a human heart have?",
            "What is the largest planet in our solar system?",
            "Who painted the Mona Lisa?",
            "What is the speed of light?",
            "Where is the Great Wall of China located?",
            
            # Science questions
            "How does gravity work?",
            "What are the states of matter?",
            "Why is the sky blue?",
            "What is DNA?",
            "How do vaccines work?",
            "What causes earthquakes?",
            "How do plants make oxygen?",
            "What is the periodic table?",
            "How does the immune system work?",
            "What is climate change?",
            
            # Math questions
            "What is 15 multiplied by 7?",
            "How do you calculate the area of a circle?",
            "What is a prime number?",
            "How do you solve a quadratic equation?",
            "What is the Pythagorean theorem?",
            
            # History questions
            "When did World War II end?",
            "Who was the first person on the moon?",
            "What was the Renaissance?",
            "When did the Berlin Wall fall?",
            "Who was Cleopatra?",
        ]
        
        # Completion content pool
        self.completion_partials = [
            "The largest planet in our solar system is",
            "Water freezes at",
            "The human heart has __ chambers",
            "The capital of Japan is",
            "Photosynthesis is the process by which",
            "The speed of light is approximately",
            "Shakespeare wrote Romeo and",
            "The Great Wall of China was built to",
            "Gravity causes objects to",
            "The periodic table organizes elements by",
            "2 + 2 equals",
            "A triangle has __ sides",
            "The Earth orbits around the",
            "Ice is the solid form of",
            "Oxygen is essential for",
            "Democracy is a form of government where",
            "The Renaissance was a period of",
            "Computers process information using",
            "The internet connects",
        ]
        
        # Generation content pool
        self.generation_prompts = [
            "Write a sentence about dogs",
            "Describe the color blue",
            "Explain what friendship means",
            "Write a haiku about nature",
            "Describe your favorite food",
            "Write about a sunny day",
            "Explain why exercise is important",
            "Describe the sound of rain",
            "Write about learning something new",
            "Describe a peaceful place",
            "Write about kindness",
            "Explain the importance of reading",
            "Describe the seasons",
            "Write about family",
            "Explain what makes you happy",
        ]
        
        # Response content pool
        self.response_scenarios = [
            "How would you greet someone new?",
            "What would you say to comfort a friend?",
            "How would you explain a difficult concept?",
            "What would you say to encourage someone?",
            "How would you apologize for a mistake?",
            "What would you say when someone asks for help?",
            "How would you respond to criticism?",
            "What would you say when meeting a celebrity?",
            "How would you handle a disagreement?",
            "What would you say to someone who is sad?",
            "How would you respond to praise?",
            "What would you say when asked about your hobbies?",
            "How would you respond to an invitation?",
            "What would you say when someone shares good news?",
            "How would you respond to someone asking for advice?",
        ]
    
    def _split_content_pools(self, eval_ratio: float = 0.2, seed: int = 42):
        """Split all content pools into train/eval sets"""
        import numpy as np
        np.random.seed(seed)
        
        def split_list(items, eval_ratio):
            items_copy = items.copy()
            np.random.shuffle(items_copy)
            split_idx = int(len(items_copy) * (1 - eval_ratio))
            return items_copy[:split_idx], items_copy[split_idx:]
        
        # Split QA questions
        self.qa_train, self.qa_eval = split_list(self.qa_questions, eval_ratio)
        
        # Split completion partials
        self.completion_train, self.completion_eval = split_list(self.completion_partials, eval_ratio)
        
        # Split generation prompts
        self.generation_train, self.generation_eval = split_list(self.generation_prompts, eval_ratio)
        
        # Split response scenarios
        self.response_train, self.response_eval = split_list(self.response_scenarios, eval_ratio)
        
        # Verify no overlap (critical assertion)
        assert len(set(self.qa_train) & set(self.qa_eval)) == 0, "QA train/eval overlap detected!"
        assert len(set(self.completion_train) & set(self.completion_eval)) == 0, "Completion train/eval overlap detected!"
        assert len(set(self.generation_train) & set(self.generation_eval)) == 0, "Generation train/eval overlap detected!"
        assert len(set(self.response_train) & set(self.response_eval)) == 0, "Response train/eval overlap detected!"
        
        logger.info(f"✅ Content pools split - Train: QA={len(self.qa_train)}, Completion={len(self.completion_train)}, Generation={len(self.generation_train)}, Response={len(self.response_train)}")
        logger.info(f"✅ Content pools split - Eval: QA={len(self.qa_eval)}, Completion={len(self.completion_eval)}, Generation={len(self.generation_eval)}, Response={len(self.response_eval)}")
        
    def generate_qa_instructions(self, count: int = 250, is_eval: bool = False) -> List[Dict[str, Any]]:
        """Generate question-answering instructions from appropriate pool"""
        
        # Use appropriate pool based on is_eval flag
        questions_pool = self.qa_eval if is_eval else self.qa_train
        
        # Extend with variations to meet count requirement
        all_questions = questions_pool * (count // len(questions_pool) + 1)
        selected_questions = all_questions[:count]
        
        instructions = []
        for i, question in enumerate(selected_questions):
            template = random.choice(self.templates.QA_TEMPLATES)
            formatted_instruction = template.format(question=question)
            
            instructions.append({
                "id": f"qa_{i}",
                "instruction": formatted_instruction,
                "instruction_type": "qa",
                "raw_question": question,
                "template": template,
                "pool": "eval" if is_eval else "train"  # Track which pool was used
            })
        
        return instructions
    
    def generate_completion_instructions(self, count: int = 250, is_eval: bool = False) -> List[Dict[str, Any]]:
        """Generate completion instructions"""
        
        # Use appropriate pool based on is_eval flag
        partials_pool = self.completion_eval if is_eval else self.completion_train
        
        # Extend with variations
        all_partials = partials_pool * (count // len(partials_pool) + 1)
        selected_partials = all_partials[:count]
        
        instructions = []
        for i, partial in enumerate(selected_partials):
            template = random.choice(self.templates.COMPLETION_TEMPLATES)
            formatted_instruction = template.format(partial=partial)
            
            instructions.append({
                "id": f"completion_{i}",
                "instruction": formatted_instruction,
                "instruction_type": "completion",
                "raw_partial": partial,
                "template": template,
                "pool": "eval" if is_eval else "train"  # Track which pool was used
            })
        
        return instructions
    
    def generate_generation_instructions(self, count: int = 250, is_eval: bool = False) -> List[Dict[str, Any]]:
        """Generate generation instructions from appropriate pool"""
        
        # Use appropriate pool based on is_eval flag
        prompts_pool = self.generation_eval if is_eval else self.generation_train
        
        # Extend with variations
        all_prompts = prompts_pool * (count // len(prompts_pool) + 1)
        selected_prompts = all_prompts[:count]
        
        instructions = []
        for i, prompt in enumerate(selected_prompts):
            # FIXED: Use the prompt directly since it's already a complete instruction
            # The templates expect {content_type} and {topic}, but we have complete prompts
            formatted_instruction = prompt  # Use prompt directly instead of template formatting
            
            instructions.append({
                "id": f"generation_{i}",
                "instruction": formatted_instruction,
                "instruction_type": "generation",
                "raw_prompt": prompt,
                "template": "direct",  # No template used
                "pool": "eval" if is_eval else "train"  # Track which pool was used
            })
        
        return instructions
    
    def generate_response_instructions(self, count: int = 250, is_eval: bool = False) -> List[Dict[str, Any]]:
        """Generate response/reaction instructions from appropriate pool"""
        
        # Use appropriate pool based on is_eval flag
        scenarios_pool = self.response_eval if is_eval else self.response_train
        
        # Extend with variations
        all_scenarios = scenarios_pool * (count // len(scenarios_pool) + 1)
        selected_scenarios = all_scenarios[:count]
        
        instructions = []
        for i, scenario in enumerate(selected_scenarios):
            template = random.choice(self.templates.RESPONSE_TEMPLATES)
            # FIXED: Use correct placeholder name - templates use {input}, not {scenario}
            formatted_instruction = template.format(input=scenario)
            
            instructions.append({
                "id": f"response_{i}",
                "instruction": formatted_instruction,
                "instruction_type": "response",
                "raw_scenario": scenario,
                "template": template,
                "pool": "eval" if is_eval else "train"  # Track which pool was used
            })
        
        return instructions
    
    def generate_all_instructions(
        self, 
        qa_count: int = 250,
        completion_count: int = 250, 
        generation_count: int = 250,
        response_count: int = 250,
        is_eval: bool = False
    ) -> List[Dict[str, Any]]:
        """Generate all instruction types from appropriate pools"""
        
        pool_type = "eval" if is_eval else "train"
        total_count = qa_count + completion_count + generation_count + response_count
        logger.info(f"Generating {total_count} instructions from {pool_type} pool...")
        
        instructions = []
        instructions.extend(self.generate_qa_instructions(qa_count, is_eval=is_eval))
        instructions.extend(self.generate_completion_instructions(completion_count, is_eval=is_eval))
        instructions.extend(self.generate_generation_instructions(generation_count, is_eval=is_eval))
        instructions.extend(self.generate_response_instructions(response_count, is_eval=is_eval))
        
        # Shuffle for randomness
        random.shuffle(instructions)
        
        logger.info(f"Generated {len(instructions)} total instructions from {pool_type} pool")
        return instructions


def format_for_dpo(preference_pairs: List[PreferencePair]) -> List[Dict[str, Any]]:
    """Format preference pairs for DPO training"""
    
    dpo_dataset = []
    for pair in preference_pairs:
        dpo_example = {
            "prompt": pair.prompt,
            "chosen": pair.chosen,
            "rejected": pair.rejected,
        }
        
        if pair.metadata:
            dpo_example.update(pair.metadata)
        
        dpo_dataset.append(dpo_example)
    
    return dpo_dataset


def save_jsonl(data: List[Dict[str, Any]], filepath: str):
    """Save data as JSONL file"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')
    
    logger.info(f"Saved {len(data)} items to {filepath}")


def load_jsonl(filepath: str) -> List[Dict[str, Any]]:
    """Load data from JSONL file"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    
    logger.info(f"Loaded {len(data)} items from {filepath}")
    return data


def create_train_test_split(
    data: List[Dict[str, Any]], 
    test_ratio: float = 0.1,
    seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split data into train and test sets"""
    random.seed(seed)
    
    shuffled_data = data.copy()
    random.shuffle(shuffled_data)
    
    test_size = int(len(data) * test_ratio)
    test_data = shuffled_data[:test_size]
    train_data = shuffled_data[test_size:]
    
    logger.info(f"Split: {len(train_data)} train, {len(test_data)} test")
    return train_data, test_data


def validate_instruction_data(data: List[Dict[str, Any]]) -> bool:
    """Validate instruction data format"""
    required_fields = ['id', 'instruction', 'instruction_type']
    
    for i, item in enumerate(data):
        for field in required_fields:
            if field not in item:
                logger.error(f"Item {i} missing required field: {field}")
                return False
        
        if not isinstance(item['instruction'], str) or not item['instruction'].strip():
            logger.error(f"Item {i} has invalid instruction")
            return False
    
    logger.info(f"✅ Validated {len(data)} instruction examples")
    return True


def validate_preference_data(data: List[Dict[str, Any]]) -> bool:
    """Validate preference pair data format"""
    required_fields = ['prompt', 'chosen', 'rejected']
    
    for i, item in enumerate(data):
        for field in required_fields:
            if field not in item:
                logger.error(f"Item {i} missing required field: {field}")
                return False
        
        for field in required_fields:
            if not isinstance(item[field], str) or not item[field].strip():
                logger.error(f"Item {i} has invalid {field}")
                return False
    
    logger.info(f"✅ Validated {len(data)} preference pairs")
    return True


if __name__ == "__main__":
    # Test data generation
    print("🧪 Testing data generation...")
    
    generator = Stage1DataGenerator()
    
    # Generate small test dataset
    instructions = generator.generate_all_instructions(
        qa_count=5,
        completion_count=5,
        generation_count=5,
        response_count=5
    )
    
    # Validate
    if validate_instruction_data(instructions):
        print("✅ Data generation successful")
        
        # Print examples
        for instruction in instructions[:3]:
            print(f"\nExample: {instruction['instruction_type']}")
            print(f"Instruction: {instruction['instruction']}")
    else:
        print("❌ Data validation failed")