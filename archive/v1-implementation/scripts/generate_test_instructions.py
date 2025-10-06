#!/usr/bin/env python3
"""
Generate New Held-Out Test Instructions
Creates instructions that are completely different from training set to avoid data leakage
"""

import json
import random
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestInstructionGenerator:
    """Generate diverse test instructions for evaluation"""
    
    def __init__(self, seed=54321):  # Different seed from training
        random.seed(seed)
        self.seed = seed
        logger.info(f"🎲 Initialized with seed {seed} (different from training)")
    
    def generate_qa_instructions(self, count=125):
        """Generate Q&A style instructions"""
        
        topics = [
            # Science & Nature (different from training set)
            ("biology", ["How do plants absorb nutrients?", "What causes allergies?", "How do vaccines work?", "Why do leaves change color?", "What is the function of the liver?"]),
            ("physics", ["Why does ice float on water?", "How do magnets work?", "What causes gravity?", "Why is the sky blue during sunset?", "How do solar panels work?"]),
            ("chemistry", ["What happens when you mix acids and bases?", "Why does iron rust?", "How does soap clean things?", "What makes diamonds so hard?", "Why do some materials conduct electricity?"]),
            ("astronomy", ["How are stars formed?", "What causes the phases of the moon?", "Why do planets orbit the sun?", "What is a black hole?", "How far away is the nearest star?"]),
            
            # History & Geography (new topics)
            ("history", ["When was the printing press invented?", "What caused World War I?", "Who built the pyramids?", "When did the Roman Empire fall?", "What was the Industrial Revolution?"]),
            ("geography", ["Which is the longest river in the world?", "Where is Mount Everest located?", "What is the capital of Brazil?", "Which continent has the most countries?", "Where is the Sahara Desert?"]),
            
            # Technology & Math (different examples)
            ("technology", ["How does WiFi work?", "What is artificial intelligence?", "How do computers store data?", "What is blockchain?", "How do touchscreens work?"]),
            ("mathematics", ["What is algebra used for?", "How do you calculate compound interest?", "What is a square root?", "How do you find the area of a circle?", "What is calculus used for?"]),
        ]
        
        instructions = []
        for topic, questions in topics:
            for question in questions[:count//len(topics) + 1]:
                instructions.append({
                    'instruction': f"Q: {question} A:",
                    'instruction_type': 'qa',
                    'topic': topic
                })
        
        return instructions[:count]
    
    def generate_completion_instructions(self, count=125):
        """Generate completion-style instructions"""
        
        completions = [
            # Science facts
            "Gravity pulls objects toward",
            "The human heart has",
            "Photosynthesis occurs in",
            "Water consists of",
            "The speed of light is",
            
            # Geography
            "The Amazon rainforest is located in",
            "Antarctica is the",
            "The Pacific Ocean is",
            "Mount Kilimanjaro is in",
            "The Nile River flows through",
            
            # History  
            "World War II ended in",
            "The telephone was invented by",
            "The first moon landing happened in",
            "The Eiffel Tower was built in",
            "Democracy originated in ancient",
            
            # Technology
            "The internet was invented in",
            "Smartphones typically run on",
            "Electric cars are powered by",
            "Solar energy comes from",
            "3D printing works by",
            
            # Biology
            "Birds can fly because they have",
            "Fish breathe through",
            "Mammals are characterized by",
            "Trees grow taller by",
            "Bees pollinate flowers to",
            
            # Math & Logic
            "A triangle has",
            "Multiplication is repeated",
            "Fractions represent",
            "Geometry studies",
            "Statistics deals with",
            
            # Literature & Arts
            "Poetry often uses",
            "Paintings can be made with",
            "Music is created by",
            "Novels tell",
            "Theater involves",
            
            # Daily Life
            "Cooking food helps",
            "Exercise benefits",
            "Sleep is important for",
            "Learning new skills",
            "Friendship involves",
        ]
        
        instructions = []
        for completion in completions[:count]:
            instructions.append({
                'instruction': completion,
                'instruction_type': 'completion'
            })
        
        return instructions
    
    def generate_generation_instructions(self, count=125):
        """Generate content generation instructions"""
        
        generation_prompts = [
            # Descriptions (different from training set)
            "Describe how rain forms",
            "Describe the process of cooking pasta", 
            "Describe what happens during an earthquake",
            "Describe how a bicycle works",
            "Describe the surface of Mars",
            
            # Creative writing
            "Write a sentence about mountains",
            "Write a sentence about friendship",
            "Write a sentence about technology", 
            "Write a sentence about music",
            "Write a sentence about learning",
            
            # Explanations
            "Explain how to brush your teeth",
            "Explain what democracy means",
            "Explain how plants grow",
            "Explain why we need sleep",
            "Explain what causes thunder",
            
            # Lists and examples  
            "Name three types of transportation",
            "List four seasons of the year",
            "Give examples of renewable energy",
            "Name five different animals",
            "List three primary colors",
            
            # Comparisons
            "Compare cats and dogs",
            "Compare summer and winter", 
            "Compare books and movies",
            "Compare cities and towns",
            "Compare walking and running",
            
            # Processes
            "Describe how to make a sandwich",
            "Explain how to plant a seed",
            "Describe how to wash hands",
            "Explain how to ride a bicycle",
            "Describe how to use a library",
        ]
        
        instructions = []
        for prompt in generation_prompts[:count]:
            instructions.append({
                'instruction': prompt,
                'instruction_type': 'generation'
            })
        
        return instructions
    
    def generate_response_instructions(self, count=125):
        """Generate response/interaction instructions"""
        
        response_prompts = [
            # Greetings and social
            "Respond to: How are you today?",
            "Reply to: What's your favorite hobby?", 
            "Answer: What did you do this weekend?",
            "Respond to: Nice to meet you!",
            "Reply to: Have a great day!",
            
            # Advice and help
            "Give advice on: How to study effectively",
            "Suggest: Ways to stay healthy",
            "Recommend: Good books to read",
            "Advise: How to make friends",
            "Help with: Planning a birthday party",
            
            # Opinions and preferences
            "Share your thoughts on: The importance of exercise",
            "Give your opinion on: Learning new languages", 
            "Comment on: The role of technology in education",
            "Share views on: Protecting the environment",
            "Discuss: The value of teamwork",
            
            # Problem-solving
            "Solve: What to do if you're lost",
            "Figure out: How to fix a flat tire",
            "Determine: The best way to save money", 
            "Work out: How to organize a messy room",
            "Calculate: How much paint needed for a wall",
        ]
        
        instructions = []
        for prompt in response_prompts[:count]:
            instructions.append({
                'instruction': prompt,
                'instruction_type': 'response'
            })
        
        return instructions
    
    def generate_all_instructions(self, total_count=500):
        """Generate a balanced set of all instruction types"""
        
        count_per_type = total_count // 4
        
        logger.info(f"🏗️ Generating {total_count} new test instructions:")
        logger.info(f"  - QA: {count_per_type}")
        logger.info(f"  - Completion: {count_per_type}")
        logger.info(f"  - Generation: {count_per_type}")
        logger.info(f"  - Response: {count_per_type}")
        
        all_instructions = []
        
        # Generate each type
        all_instructions.extend(self.generate_qa_instructions(count_per_type))
        all_instructions.extend(self.generate_completion_instructions(count_per_type))
        all_instructions.extend(self.generate_generation_instructions(count_per_type))
        all_instructions.extend(self.generate_response_instructions(count_per_type))
        
        # Add IDs and shuffle
        for i, instruction in enumerate(all_instructions):
            instruction['id'] = f"test_{i+1}"
            instruction['generated_for'] = 'held_out_evaluation'
            instruction['seed'] = self.seed
        
        random.shuffle(all_instructions)
        
        logger.info(f"✅ Generated {len(all_instructions)} diverse test instructions")
        return all_instructions
    
    def verify_no_training_overlap(self, test_instructions):
        """Verify no overlap with training data"""
        
        logger.info("🔍 Verifying no overlap with training data...")
        
        # Load training instructions
        training_file = ARTIFACTS_DIR / "logprob_preference_pairs.jsonl"
        training_instructions = set()
        
        if training_file.exists():
            with open(training_file) as f:
                for line in f:
                    data = json.loads(line)
                    training_instructions.add(data['instruction'].strip())
        else:
            logger.warning("⚠️ Training file not found, cannot verify overlap")
            return test_instructions
        
        # Check for overlaps
        test_instruction_texts = {inst['instruction'].strip() for inst in test_instructions}
        overlaps = test_instruction_texts & training_instructions
        
        if overlaps:
            logger.error(f"🚨 Found {len(overlaps)} overlapping instructions!")
            for overlap in list(overlaps)[:5]:  # Show first 5
                logger.error(f"  - '{overlap}'")
            raise ValueError(f"Data leakage detected: {len(overlaps)} instructions overlap with training set")
        
        logger.info(f"✅ No overlap found! {len(test_instruction_texts)} test instructions are unique")
        logger.info(f"📊 Training set: {len(training_instructions)} instructions")
        logger.info(f"📊 Test set: {len(test_instruction_texts)} instructions")
        
        return test_instructions

def main():
    """Generate held-out test instructions"""
    
    import argparse
    parser = argparse.ArgumentParser(description="Generate held-out test instructions")
    parser.add_argument("--count", type=int, default=500, help="Number of instructions to generate")
    parser.add_argument("--seed", type=int, default=54321, help="Random seed")
    args = parser.parse_args()
    
    try:
        # Create output directory
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate instructions
        generator = TestInstructionGenerator(seed=args.seed)
        test_instructions = generator.generate_all_instructions(args.count)
        
        # Verify no overlap with training data
        test_instructions = generator.verify_no_training_overlap(test_instructions)
        
        # Save instructions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = ARTIFACTS_DIR / f"held_out_test_instructions_{timestamp}.jsonl"
        
        with open(output_file, 'w') as f:
            for instruction in test_instructions:
                json.dump(instruction, f)
                f.write('\n')
        
        # Create summary
        by_type = {}
        for instruction in test_instructions:
            inst_type = instruction['instruction_type']
            by_type[inst_type] = by_type.get(inst_type, 0) + 1
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_instructions': len(test_instructions),
            'seed_used': args.seed,
            'distribution_by_type': by_type,
            'sample_instructions': test_instructions[:10],
            'output_file': str(output_file)
        }
        
        summary_file = ARTIFACTS_DIR / f"test_instructions_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("\\n" + "="*60)
        print("🎉 HELD-OUT TEST INSTRUCTIONS GENERATED")
        print("="*60)
        print(f"Total instructions: {len(test_instructions)}")
        print(f"Distribution by type:")
        for inst_type, count in by_type.items():
            print(f"  {inst_type}: {count}")
        print(f"\\nFiles created:")
        print(f"  - Instructions: {output_file}")
        print(f"  - Summary: {summary_file}")
        print("\\n✅ Ready for evaluation!")
        
        return test_instructions
        
    except Exception as e:
        logger.error(f"❌ Test instruction generation failed: {e}")
        raise

if __name__ == "__main__":
    main()