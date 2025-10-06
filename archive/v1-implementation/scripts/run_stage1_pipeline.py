#!/usr/bin/env python3
"""
Complete Stage 1 Pipeline: Baseline → Data Generation → Training → Evaluation
Orchestrates the full Stage 1 workflow
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import subprocess
import os

# Configure base directory for RunPod deployment
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/cai-constitution-bootstrap'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Stage1Pipeline:
    """Complete Stage 1 pipeline orchestrator"""
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-32B"):
        self.model_name = model_name
        self.scripts_dir = BASE_DIR / "scripts"
        self.project_dir = BASE_DIR
        self.results_dir = self.project_dir / "results"
        self.logs_dir = self.project_dir / "logs"
        
        # Create directories
        self.results_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Pipeline status
        self.pipeline_start = datetime.now()
        self.pipeline_log = self.logs_dir / f"stage1_pipeline_{self.pipeline_start.strftime('%Y%m%d_%H%M%S')}.log"
        
        logger.info(f"🚀 Stage 1 pipeline initialized for: {model_name}")
        logger.info(f"📋 Pipeline log: {self.pipeline_log}")
    
    def log_step(self, step: str, status: str, details: Dict[str, Any] = None):
        """Log pipeline step"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'step': step,
            'status': status,
            'details': details or {}
        }
        
        # Write to log file
        with open(self.pipeline_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Print to console
        status_emoji = {
            'start': '🚀',
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        emoji = status_emoji.get(status, '📝')
        logger.info(f"{emoji} {step}: {status.upper()}")
    
    def run_python_script(self, script_name: str, args: list = None, step_name: str = None) -> bool:
        """Run a Python script and return success status"""
        script_path = self.scripts_dir / script_name

        # Verify script exists before running (fail fast)
        if not script_path.exists():
            logger.error(f"❌ Script not found: {script_path}")
            logger.error(f"   This may indicate the script was deprecated or renamed.")
            logger.error(f"   Check docs/IMPLEMENTATION_REGISTRY.md for current scripts.")
            return False

        cmd = [sys.executable, str(script_path)]

        if args:
            cmd.extend(args)

        logger.info(f"🏃 Running: {' '.join(cmd)}")
        
        # Different timeouts for different steps
        timeouts = {
            'baseline': 3600,    # 1 hour
            'generate': 7200,    # 2 hours  
            'train': 10800,      # 3 hours
            'evaluate': 3600     # 1 hour
        }
        
        timeout = timeouts.get(step_name, 3600)  # Default 1 hour
        logger.info(f"⏰ Using {timeout/3600:.1f}h timeout for {step_name or script_name}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=self.project_dir,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {script_name} completed successfully")
                return True
            else:
                logger.error(f"❌ {script_name} failed with code {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {script_name} timed out after 1 hour")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to run {script_name}: {e}")
            return False
    
    def check_baseline_exists(self) -> bool:
        """Check if baseline assessment already exists"""
        baseline_file = self.results_dir / "baseline_assessment.json"
        return baseline_file.exists()
    
    def check_training_data_exists(self) -> bool:
        """Check if Stage 1 training data already exists"""
        data_file = self.project_dir / "data" / "stage1" / "train_preference_pairs.jsonl"
        return data_file.exists()
    
    def find_latest_checkpoint(self) -> Optional[str]:
        """Find the latest Stage 1 checkpoint"""
        checkpoint_dir = self.project_dir / "checkpoints" / "stage1"
        
        if not checkpoint_dir.exists():
            return None
        
        # Look for training success markers (more robust)
        success_markers = []
        for path in checkpoint_dir.rglob("TRAINING_SUCCESS"):
            if path.is_file():
                success_markers.append(path)
        
        if success_markers:
            # Return adapter path from the most recent successful training
            latest_marker = max(success_markers, key=lambda p: p.stat().st_mtime)
            try:
                with open(latest_marker, 'r') as f:
                    marker_data = json.load(f)
                adapter_path = marker_data.get('adapter_path')
                if adapter_path and Path(adapter_path).exists():
                    return adapter_path
            except Exception as e:
                logger.warning(f"⚠️  Could not read success marker: {e}")
        
        # Fallback to old method
        adapter_dirs = []
        for path in checkpoint_dir.rglob("final_lora_adapters"):
            if path.is_dir():
                adapter_dirs.append(path)
        
        if not adapter_dirs:
            return None
        
        # Return the most recent one
        latest = max(adapter_dirs, key=lambda p: p.stat().st_mtime)
        return str(latest)
    
    def step1_baseline_assessment(self, force: bool = False) -> bool:
        """Step 1: Run baseline assessment"""
        step_name = "Baseline Assessment"
        self.log_step(step_name, "start")
        
        if not force and self.check_baseline_exists():
            logger.info("⏭️  Baseline assessment already exists, skipping...")
            self.log_step(step_name, "info", {"skipped": "already_exists"})
            return True
        
        success = self.run_python_script("baseline_assessment.py", step_name="baseline")
        
        if success:
            # Load and log key results
            baseline_file = self.results_dir / "baseline_assessment.json"
            if baseline_file.exists():
                with open(baseline_file, 'r') as f:
                    baseline_results = json.load(f)
                
                details = {
                    "overall_success_rate": baseline_results.get("overall_success_rate", 0),
                    "categories": {k: v.get("success_rate", 0) for k, v in baseline_results.get("categories", {}).items()}
                }
                self.log_step(step_name, "success", details)
        else:
            self.log_step(step_name, "error")
        
        return success
    
    def step2_data_generation(self, num_instructions: int = 1000, force: bool = False) -> bool:
        """Step 2: Generate training data"""
        step_name = "Data Generation"
        self.log_step(step_name, "start")

        if not force and self.check_training_data_exists():
            logger.info("⏭️  Training data already exists, skipping...")
            self.log_step(step_name, "info", {"skipped": "already_exists"})
            return True

        # Use modern v2 script with model-generated instructions + quality filtering
        args = ["--count", str(num_instructions)]
        success = self.run_python_script("generate_sample_data_v2.py", args, step_name="generate")
        
        if success:
            # Load and log key results
            summary_file = self.project_dir / "data" / "stage1" / "generation_summary.json"
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
                
                details = {
                    "total_instructions": summary.get("total_instructions", 0),
                    "preference_pairs": summary.get("total_preference_pairs", 0),
                    "initial_success_rate": summary.get("initial_success_rate", 0),
                    "improved_success_rate": summary.get("improved_success_rate", 0)
                }
                self.log_step(step_name, "success", details)
        else:
            self.log_step(step_name, "error")
        
        return success
    
    def step3_training(self, num_epochs: int = 3, batch_size: int = 4) -> bool:
        """Step 3: Train the model"""
        step_name = "DPO Training"
        self.log_step(step_name, "start")
        
        args = [
            "--epochs", str(num_epochs),
            "--batch-size", str(batch_size),
            "--run-name", f"pipeline_{self.pipeline_start.strftime('%Y%m%d_%H%M%S')}"
        ]

        # Use improved DPO trainer (uses CleanModelLoader)
        success = self.run_python_script("train_stage1_dpo_improved.py", args, step_name="train")
        
        if success:
            checkpoint_path = self.find_latest_checkpoint()
            details = {
                "epochs": num_epochs,
                "batch_size": batch_size,
                "checkpoint_path": checkpoint_path
            }
            self.log_step(step_name, "success", details)
        else:
            self.log_step(step_name, "error")
        
        return success
    
    def step4_evaluation(self, eval_size: int = 200) -> bool:
        """Step 4: Evaluate the trained model"""
        step_name = "Model Evaluation"
        self.log_step(step_name, "start")
        
        # Find the latest checkpoint
        checkpoint_path = self.find_latest_checkpoint()
        if not checkpoint_path:
            logger.error("❌ No trained model checkpoint found")
            self.log_step(step_name, "error", {"error": "no_checkpoint"})
            return False
        
        args = [
            "--checkpoint", checkpoint_path,
            "--eval-size", str(eval_size)
        ]
        
        success = self.run_python_script("evaluate_stage1.py", args, step_name="evaluate")
        
        if success:
            # CRITICAL: Enforce 95% success gate
            success_rate = self.check_95_percent_gate()
            if success_rate is not None and success_rate < 0.95:
                logger.error(f"🚨 Stage 1 FAILED: Only achieved {success_rate:.1%} (need 95%)")
                self.log_step(step_name, "error", {"success_rate": success_rate, "threshold": 0.95})
                return False
            
            details = {
                "checkpoint": checkpoint_path,
                "eval_size": eval_size,
                "success_rate": success_rate
            }
            self.log_step(step_name, "success", details)
        else:
            self.log_step(step_name, "error")
        
        return success
    
    def check_95_percent_gate(self) -> Optional[float]:
        """Check if the trained model achieved 95% instruction following"""
        # Find the latest evaluation results
        eval_files = list(self.results_dir.glob("stage1_evaluation_*.json"))
        
        if not eval_files:
            logger.warning("⚠️  No evaluation results found - cannot check 95% gate")
            return None
        
        # Get the most recent evaluation
        latest_eval = max(eval_files, key=lambda p: p.stat().st_mtime)
        
        try:
            with open(latest_eval, 'r') as f:
                eval_results = json.load(f)
            
            # Extract success rate from trained model
            trained_success_rate = eval_results.get('models', {}).get('trained', {}).get('success_rate', 0)
            
            logger.info(f"📊 Trained model success rate: {trained_success_rate:.1%}")
            return trained_success_rate
            
        except Exception as e:
            logger.error(f"❌ Failed to read evaluation results: {e}")
            return None
    
    def run_full_pipeline(self, 
                         num_instructions: int = 1000,
                         num_epochs: int = 3, 
                         batch_size: int = 4,
                         eval_size: int = 200,
                         force_baseline: bool = False,
                         force_data: bool = False) -> Dict[str, Any]:
        """Run the complete Stage 1 pipeline"""
        
        logger.info("🚀 Starting complete Stage 1 pipeline...")
        logger.info(f"📊 Configuration:")
        logger.info(f"  Model: {self.model_name}")
        logger.info(f"  Instructions: {num_instructions}")
        logger.info(f"  Training epochs: {num_epochs}")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"  Evaluation size: {eval_size}")
        
        pipeline_results = {
            'start_time': self.pipeline_start.isoformat(),
            'model': self.model_name,
            'config': {
                'num_instructions': num_instructions,
                'num_epochs': num_epochs,
                'batch_size': batch_size,
                'eval_size': eval_size
            },
            'steps': {},
            'success': False
        }
        
        try:
            # Step 1: Baseline Assessment
            if not self.step1_baseline_assessment(force_baseline):
                pipeline_results['steps']['baseline'] = 'failed'
                return pipeline_results
            pipeline_results['steps']['baseline'] = 'success'
            
            # Step 2: Data Generation  
            if not self.step2_data_generation(num_instructions, force_data):
                pipeline_results['steps']['data_generation'] = 'failed'
                return pipeline_results
            pipeline_results['steps']['data_generation'] = 'success'
            
            # Step 3: Training
            if not self.step3_training(num_epochs, batch_size):
                pipeline_results['steps']['training'] = 'failed'
                return pipeline_results
            pipeline_results['steps']['training'] = 'success'
            
            # Step 4: Evaluation
            if not self.step4_evaluation(eval_size):
                pipeline_results['steps']['evaluation'] = 'failed'
                return pipeline_results
            pipeline_results['steps']['evaluation'] = 'success'
            
            # Success!
            pipeline_results['success'] = True
            pipeline_results['end_time'] = datetime.now().isoformat()
            pipeline_results['duration_minutes'] = (datetime.now() - self.pipeline_start).total_seconds() / 60
            
            self.log_step("Complete Pipeline", "success", pipeline_results)
            
            return pipeline_results
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            pipeline_results['error'] = str(e)
            pipeline_results['end_time'] = datetime.now().isoformat()
            self.log_step("Complete Pipeline", "error", {"error": str(e)})
            return pipeline_results
    
    def print_pipeline_summary(self, results: Dict[str, Any]):
        """Print a nice summary of pipeline results"""
        print("\n" + "="*80)
        print("🎉 STAGE 1 PIPELINE COMPLETE!")
        print("="*80)
        
        if results['success']:
            print("✅ Status: SUCCESS")
            print(f"⏱️  Duration: {results.get('duration_minutes', 0):.1f} minutes")
        else:
            print("❌ Status: FAILED")
            if 'error' in results:
                print(f"💥 Error: {results['error']}")
        
        print("\n📋 Steps:")
        for step, status in results['steps'].items():
            emoji = "✅" if status == "success" else "❌"
            print(f"  {emoji} {step.replace('_', ' ').title()}: {status}")
        
        print(f"\n📊 Configuration:")
        config = results['config']
        print(f"  Model: {results['model']}")
        print(f"  Instructions: {config['num_instructions']}")
        print(f"  Training epochs: {config['num_epochs']}")
        print(f"  Batch size: {config['batch_size']}")
        print(f"  Evaluation size: {config['eval_size']}")
        
        print(f"\n📁 Logs: {self.pipeline_log}")
        
        if results['success']:
            print("\n🚀 Ready for Stage 2!")
        else:
            print("\n🔧 Please fix issues and retry")
        
        print("="*80)


def main():
    """Run the Stage 1 pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run complete Stage 1 pipeline")
    parser.add_argument("--model", default="Qwen/Qwen2.5-32B", help="Base model name")
    parser.add_argument("--instructions", type=int, default=1000, help="Number of instructions to generate")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    parser.add_argument("--eval-size", type=int, default=200, help="Evaluation set size")
    parser.add_argument("--force-baseline", action="store_true", help="Force re-run baseline assessment")
    parser.add_argument("--force-data", action="store_true", help="Force re-generate training data")
    parser.add_argument("--quick-test", action="store_true", help="Quick test with minimal settings")
    
    args = parser.parse_args()
    
    if args.quick_test:
        args.instructions = 100
        args.epochs = 1
        args.eval_size = 50
        logger.info("🧪 Running quick test pipeline")
    
    # Create pipeline
    pipeline = Stage1Pipeline(args.model)
    
    # Run pipeline
    results = pipeline.run_full_pipeline(
        num_instructions=args.instructions,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        eval_size=args.eval_size,
        force_baseline=args.force_baseline,
        force_data=args.force_data
    )
    
    # Print summary
    pipeline.print_pipeline_summary(results)
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)


if __name__ == "__main__":
    main()