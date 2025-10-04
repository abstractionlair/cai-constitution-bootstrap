#!/usr/bin/env python3
"""
Generate clean SFT (Supervised Fine-Tuning) data with proper format for Stage 1
Uses consistent Instruction/Response/END format for loss masking
"""

import json
import random
import logging
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import sys
import os
import torch

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

# Import clean model loader
from utils.clean_model_loader import CleanModelLoader

# Create directories
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

class SFTDataGenerator:
    """Generate clean SFT training data with consistent format"""
    
    def __init__(self, seed=42, load_model=True, min_response_length=50):
        """Initialize with reproducible seed and optional model loading"""
        random.seed(seed)
        torch.manual_seed(seed)
        logger.info(f"🎲 Initialized SFT data generator with seed {seed}")
        
        # Model components
        self.model = None
        self.tokenizer = None
        self.loader: Optional[CleanModelLoader] = None
        self.min_response_length = min_response_length
        
        # Instruction templates (needed even without model)
        self.instruction_types = {
            'qa': {
                'templates': [
                    "Q: {question} A:",
                    "When asked '{question}', the answer is:",
                    "The answer to '{question}' is:",
                ],
                'topics': ['science', 'history', 'geography', 'math', 'general knowledge'],
                'count': 50
            },
            'completion': {
                'templates': [
                    "Complete this sentence: {partial}",
                    "The sentence '{partial}' continues as:",
                    "{partial}",
                ],
                'patterns': [
                    "The sun rises in the",
                    "Water freezes at",
                    "The capital of France is", 
                    "Photosynthesis is the process where",
                    "The largest ocean is the"
                ],
                'count': 50
            },
            'generation': {
                'templates': [
                    "Write {content_type} about {topic}:",
                    "Here is {content_type} about {topic}:",
                    "An example of {content_type} about {topic}:",
                ],
                'content_types': ['a sentence', 'a short paragraph', 'a brief explanation'],
                'topics': ['nature', 'technology', 'food', 'travel', 'learning'],
                'count': 50
            },
            'response': {
                'templates': [
                    "How would you respond to: {input}",
                    "When someone says '{input}', respond with:",
                    "Appropriate response to '{input}':",
                ],
                'inputs': [
                    "What's the weather like?",
                    "Can you help me?",
                    "Thank you very much",
                    "I'm feeling sad today",
                    "Explain this to me"
                ],
                'count': 50
            }
        }
        
        # Load base model for generation if requested
        if load_model:
            try:
                self.load_base_model()
            except Exception as e:
                logger.warning(f"Failed to load base model: {e}. Will use placeholders.")
                self.model = None
                self.tokenizer = None
        
    def load_base_model(self):
        """Load base Qwen model for generating initial responses (using CleanModelLoader)"""
        logger.info("🤖 Loading Qwen-2.5-32B base model for data generation...")

        # Use CleanModelLoader for guaranteed contamination-free loading
        self.loader = CleanModelLoader(
            model_name="Qwen/Qwen2.5-32B",
            load_in_8bit=True,
            load_in_4bit=False
        )

        self.model, self.tokenizer, self.provenance = self.loader.load()
        logger.info("✅ Base model loaded with CleanModelLoader (contamination-free)")
        logger.info(f"📋 Loader version: {self.provenance['loader_version'][:8]}")
    
    def generate_instruction(self, inst_type: str, inst_id: str) -> Dict[str, Any]:
        """Generate a single instruction of given type"""
        
        if inst_type == 'qa':
            topics = self.instruction_types['qa']['topics']
            topic = random.choice(topics)
            
            questions = {
                'science': ["What is gravity?", "How do plants make food?", "What causes rain?"],
                'history': ["When did World War II end?", "Who was the first president?", "What year was the internet created?"],
                'geography': ["What is the largest continent?", "Where is the Sahara Desert?", "Which river is the longest?"],
                'math': ["What is 2 + 2?", "What is 10 divided by 2?", "What is 3 × 4?"],
                'general knowledge': ["What do bees make?", "How many days are in a year?", "What color do you get mixing red and blue?"]
            }
            
            question = random.choice(questions[topic])
            instruction = question
            
        elif inst_type == 'completion':
            patterns = self.instruction_types['completion']['patterns']
            partial = random.choice(patterns)
            instruction = partial
            
        elif inst_type == 'generation':
            content_types = self.instruction_types['generation']['content_types']
            topics = self.instruction_types['generation']['topics']
            content_type = random.choice(content_types)
            topic = random.choice(topics)
            
            templates = [
                f"Write {content_type} about {topic}",
                f"Generate {content_type} describing {topic}",
                f"Create {content_type} on the topic of {topic}"
            ]
            instruction = random.choice(templates)
            
        elif inst_type == 'response':
            inputs = self.instruction_types['response']['inputs']
            input_text = random.choice(inputs)
            
            templates = [
                f"Respond to: {input_text}",
                f"How would you reply to: {input_text}",
                f"What would you say to: {input_text}"
            ]
            instruction = random.choice(templates)
        
        return {
            'id': inst_id,
            'instruction': instruction,
            'instruction_type': inst_type,
            'generated_for': 'sft_training',
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_all_instructions(self, total_count=200) -> List[Dict[str, Any]]:
        """Generate all instructions for SFT training"""
        logger.info(f"🏗️ Generating {total_count} instructions for SFT training")
        
        instructions = []
        inst_id = 1
        
        for inst_type, config in self.instruction_types.items():
            count = min(config['count'], total_count // 4)  # Distribute evenly
            logger.info(f"  - {inst_type}: {count} instructions")
            
            for i in range(count):
                instruction = self.generate_instruction(inst_type, f"sft_{inst_id}")
                instructions.append(instruction)
                inst_id += 1
        
        # Shuffle for good training dynamics
        random.shuffle(instructions)
        
        logger.info(f"✅ Generated {len(instructions)} instructions")
        return instructions
    
    def create_completion_prompt(self, instruction: str, inst_type: str) -> str:
        """Create completion-style prompt for base model"""
        
        # Use completion-style prompting that works with base models
        if inst_type == 'qa':
            if instruction.startswith('Q:'):
                return instruction  # Already formatted
            else:
                return f"Q: {instruction} A:"
                
        elif inst_type == 'completion':
            return instruction  # Direct completion
            
        elif inst_type == 'generation':
            return f"Here is an example: {instruction} The result is:"
            
        elif inst_type == 'response':
            return f"Example response to '{instruction}': "
        
        return instruction
    
    def generate_response_with_base_model(self, instruction_data: Dict[str, Any]) -> str:
        """Generate response using actual base model or fallback to placeholders"""
        
        inst_type = instruction_data['instruction_type']
        instruction = instruction_data['instruction']
        
        # Try actual model generation first
        if self.model is not None and self.tokenizer is not None:
            try:
                return self._generate_with_model(instruction, inst_type)
            except Exception as e:
                logger.warning(f"Model generation failed: {e}. Using placeholder.")
                
        # Fallback to placeholders if model unavailable
        return self._generate_placeholder_response(instruction, inst_type)
    
    def _generate_with_model(self, instruction: str, inst_type: str) -> str:
        """Generate response using the loaded base model (via CleanModelLoader)"""

        # Create completion-style prompt
        completion_prompt = self.create_completion_prompt(instruction, inst_type)

        # Use CleanModelLoader's generate method (handles all contamination prevention)
        generated_text = self.loader.generate(
            self.model,
            self.tokenizer,
            completion_prompt,
            max_new_tokens=150,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=True
        )

        # Clean and validate the response
        return self._clean_response(generated_text, inst_type)
    
    def _clean_response(self, response: str, inst_type: str) -> str:
        """Clean and validate generated response"""
        
        # Remove common unwanted prefixes/suffixes
        response = response.strip()
        
        # Remove any continuation prompts or repetitions
        stop_phrases = ['\nQ:', '\nInstruction:', '\nA:', 'Human:', 'Assistant:']
        for phrase in stop_phrases:
            if phrase in response:
                response = response.split(phrase)[0].strip()
        
        # Ensure reasonable length (not too short or too long)
        if len(response) < max(3, self.min_response_length):
            return self._generate_placeholder_response("fallback", inst_type, self.min_response_length)
        
        if len(response) > 300:
            # Truncate at sentence boundary if possible
            sentences = response.split('. ')
            if len(sentences) > 1:
                response = '. '.join(sentences[:-1]) + '.'
            else:
                response = response[:300] + '...'
        
        return response
    
    def _generate_placeholder_response(self, instruction: str, inst_type: str, min_length: int = 50) -> str:
        """Generate placeholder response when model is unavailable"""
        
        if inst_type == 'qa':
            responses = {
                "What is gravity?": "Gravity is a fundamental force of nature that causes objects with mass to attract each other. This force is what keeps us grounded to Earth and governs the motion of planets around stars. Einstein's theory describes gravity not as a force, but as a curvature in space-time caused by mass and energy.",
                "How do plants make food?": "Plants make food through a process called photosynthesis, where they use sunlight, carbon dioxide from the air, and water from the soil. Chlorophyll in their leaves captures light energy and converts it into chemical energy, producing glucose sugar and releasing oxygen as a byproduct. This process is essential for all life on Earth.",
                "What causes rain?": "Rain is caused by the water cycle, where water evaporates from oceans, lakes, and rivers, rises into the atmosphere as water vapor, and condenses into tiny droplets around particles in clouds. When these droplets grow heavy enough, they fall as precipitation. Temperature, humidity, and atmospheric pressure all play important roles in this process.",
                "When did World War II end?": "World War II ended in 1945, with Germany surrendering on May 8th (VE Day in Europe) and Japan surrendering on August 15th following the atomic bombings of Hiroshima and Nagasaki. The formal surrender ceremony took place on September 2, 1945, aboard the USS Missouri in Tokyo Bay, marking the official end of the deadliest conflict in human history.",
            }
            base_response = responses.get(instruction, "This is an important question that requires careful consideration of multiple factors and historical context to provide a complete and accurate answer.")
            
        elif inst_type == 'completion':
            completions = {
                "The sun rises in the": "east due to Earth's rotation from west to east, creating the daily cycle of day and night that has been fundamental to human civilization and natural rhythms throughout history.",
                "Water freezes at": "0 degrees Celsius (32 degrees Fahrenheit) at standard atmospheric pressure, a critical temperature that affects weather patterns, seasonal changes, and many biological and physical processes on Earth.", 
                "The capital of France is": "Paris, a historic city known for its art, culture, architecture, and cuisine. It serves as the political, economic, and cultural center of France and is one of the most visited cities in the world.",
            }
            base_response = completions.get(instruction, "a concept that requires detailed explanation considering various scientific, historical, or cultural factors that influence our understanding of this topic.")
            
        elif inst_type == 'generation':
            if 'nature' in instruction:
                base_response = "Trees and forests are essential ecosystems that provide oxygen, absorb carbon dioxide, prevent soil erosion, and create habitats for countless species. They also offer resources like timber, medicines, and food while contributing to climate regulation and biodiversity conservation."
            elif 'technology' in instruction:
                base_response = "Technology continues to evolve rapidly, transforming how we communicate, work, learn, and solve complex problems. From artificial intelligence to renewable energy systems, technological advances offer both opportunities and challenges that require careful consideration and responsible implementation."
            elif 'food' in instruction:
                base_response = "Nutrition and food systems play crucial roles in human health and environmental sustainability. Fresh, whole foods provide essential vitamins, minerals, and nutrients while supporting local communities and reducing environmental impact through sustainable farming practices."
            else:
                base_response = "This topic involves multiple interconnected concepts that merit thorough exploration. Understanding the various perspectives, historical context, and current developments helps us form comprehensive insights and make informed decisions about complex issues."
                
        elif inst_type == 'response':
            base_response = "I appreciate your question and would be happy to provide detailed assistance. To give you the most helpful and accurate information, I'd like to understand more about your specific needs, goals, and any particular aspects you'd like me to focus on in my response."
        
        else:
            base_response = "This is an interesting and complex topic that benefits from careful analysis. I'll do my best to provide comprehensive information while considering multiple perspectives and relevant factors that contribute to a complete understanding."
        
        # Ensure minimum length by expanding if necessary
        if len(base_response) < min_length:
            padding = " This requires consideration of various factors, contexts, and implications to provide a thorough and well-rounded understanding of the subject matter."
            base_response += padding
            
            # Add more padding if still too short
            while len(base_response) < min_length:
                base_response += " Additional research and analysis may provide further insights into this important topic."
        
        return base_response
    
    def create_sft_format(self, instruction: str, response: str) -> str:
        """Create the standard SFT format: Instruction/Response/END"""
        return f"Instruction: {instruction}\nResponse: {response}\nEND"
    
    def generate_sft_dataset(self, count=200) -> Tuple[List[Dict[str, Any]], str]:
        """Generate complete SFT dataset"""
        logger.info(f"🚀 Generating SFT dataset with {count} examples")
        
        # Generate instructions
        instructions = self.generate_all_instructions(count)
        
        # Generate responses and format for SFT
        sft_examples = []
        
        for inst_data in instructions:
            # Generate response (placeholder for now)
            response = self.generate_response_with_base_model(inst_data)
            
            # Create SFT format
            formatted_text = self.create_sft_format(inst_data['instruction'], response)
            
            # Store example
            example = {
                **inst_data,
                'response': response,
                'formatted_text': formatted_text,
                'prompt': self.create_completion_prompt(inst_data['instruction'], inst_data['instruction_type']),
                'completion': f" {response}\nEND"  # Space before response for tokenization
            }
            
            sft_examples.append(example)
        
        # Create summary
        by_type = {}
        for example in sft_examples:
            inst_type = example['instruction_type']
            by_type[inst_type] = by_type.get(inst_type, 0) + 1
        
        summary = f"""📊 SFT Dataset Generated
===========================

Total Examples: {len(sft_examples)}
Format: Instruction: <text>\\nResponse: <text>\\nEND

Distribution by Type:
"""
        
        for inst_type, count in by_type.items():
            summary += f"  {inst_type}: {count}\n"
        
        summary += f"""
Sample Examples:
----------------
"""
        
        for i, example in enumerate(sft_examples[:3]):
            summary += f"""
{i+1}. [{example['instruction_type']}] {example['instruction']}
   → {example['response']}
"""
        
        logger.info(f"✅ SFT dataset generated: {len(sft_examples)} examples")
        return sft_examples, summary

def main():
    """Main function to generate SFT data"""
    parser = argparse.ArgumentParser(description="Generate SFT training data for Stage 1")
    parser.add_argument("--no-model", action="store_true", help="Skip model loading (use placeholders only)")
    parser.add_argument("--count", type=int, default=200, help="Number of examples to generate")
    parser.add_argument("--min-response-length", type=int, default=50, help="Minimum response length in characters")
    args = parser.parse_args()
    
    logger.info("🎯 Starting SFT data generation for Stage 1")
    
    # Generate dataset
    load_model = not args.no_model
    generator = SFTDataGenerator(seed=12345, load_model=load_model, min_response_length=args.min_response_length)  # Different seed from test data
    sft_examples, summary = generator.generate_sft_dataset(count=args.count)
    
    # Save dataset
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_file = ARTIFACTS_DIR / f"sft_training_data_{timestamp}.jsonl"
    
    with open(dataset_file, 'w') as f:
        for example in sft_examples:
            f.write(json.dumps(example) + '\n')
    
    # Save summary
    summary_file = ARTIFACTS_DIR / f"sft_data_summary_{timestamp}.txt"
    with open(summary_file, 'w') as f:
        f.write(summary)
    
    logger.info(f"💾 Dataset saved to {dataset_file}")
    logger.info(f"📋 Summary saved to {summary_file}")
    
    print(f"\n{summary}")
    print(f"\n✅ SFT data generation complete!")
    print(f"Dataset: {dataset_file}")
    print(f"Summary: {summary_file}")

if __name__ == "__main__":
    main()