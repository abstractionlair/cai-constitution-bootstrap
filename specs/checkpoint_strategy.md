# Checkpoint Strategy for Progressive Bootstrapping

## Recommendation: Save LoRA Adapters + Merge for Generation

### What We'll Save After Each Stage

```python
stage_1_outputs/
├── lora_adapters/
│   ├── adapter_config.json      # LoRA configuration
│   └── adapter_model.bin        # ~200-500MB (small!)
├── training_logs/
│   └── metrics.json             # Performance metrics
└── test_results/
    └── evaluation.json          # Success rates
```

### Why LoRA Adapters?

1. **Storage Efficient**: 
   - LoRA adapters: ~200-500MB per stage
   - Full weights: ~65GB per stage (32B model × 2 bytes)
   - 6 stages of LoRA: ~3GB total
   - 6 stages of full weights: ~390GB total!

2. **Transfer Friendly**:
   - Easy to download from RunPod
   - Quick to version control
   - Can email them if needed!

3. **Composable**:
   - Can apply Stage 1 LoRA to base
   - Then Stage 2 LoRA on top
   - Experimental flexibility

### The Workflow

```python
# Stage 1 Training
base_model = load_qwen_32b_base()
lora_model = add_lora_adapters(base_model)
train_stage_1(lora_model)
save_lora_adapters("stage_1_lora/")

# Stage 2 Preparation
# Option A: Stack LoRAs (experimental)
base_model = load_qwen_32b_base()
stage1_model = apply_lora(base_model, "stage_1_lora/")
stage2_lora = add_new_lora_adapters(stage1_model)

# Option B: Merge and continue (recommended)
base_model = load_qwen_32b_base()
stage1_model = merge_lora(base_model, "stage_1_lora/")
# Now stage1_model is the full model with Stage 1 training
# Add new LoRA for Stage 2
stage2_lora = add_lora_adapters(stage1_model)
```

### For Generation Between Stages

When we need Stage N model to generate data for Stage N+1:

```python
# Merge for quality generation
base_model = load_qwen_32b_base()
merged_model = merge_lora(base_model, f"stage_{n}_lora/")

# Use higher precision for generation
merged_model = merged_model.to(torch.float16)  # or bfloat16

# Generate high-quality training data for next stage
data = generate_training_data(merged_model)
```

### Critical Decision Points

#### Save LoRA: YES ✓
- Always save LoRA adapters after training
- Small, efficient, transferable

#### Merge for Generation: YES ✓  
- Merge LoRA into base for data generation
- Use higher precision (8-bit or 16-bit)
- Better quality for bootstrapping

#### Save Merged Weights: OPTIONAL
- Only if we have space and bandwidth
- Can always recreate by merging LoRA + base
- Maybe save final Stage 6 merged model

### Storage Requirements

```
Minimal (LoRA only):
- 6 stages × 500MB = 3GB
- Plus base model (downloaded once) = 65GB
- Total: ~70GB

Full (if saving merged):
- LoRA adapters: 3GB
- Base model: 65GB
- Final merged model: 65GB
- Total: ~135GB

Maximal (all merged):
- All LoRAs: 3GB
- All merged models: 6 × 65GB = 390GB
- Total: ~395GB (not recommended!)
```

### Recommended Approach

1. **Always save**: LoRA adapters (small, critical)
2. **Merge temporarily**: For generation between stages
3. **Save final**: Stage 6 merged model for publication
4. **Document**: Exact base model version and merge process

### Code Example

```python
from peft import PeftModel, get_peft_model, LoraConfig

# Training Stage N
def train_stage(n, base_model_path, previous_lora_path=None):
    # Load base or previous stage
    if previous_lora_path:
        model = AutoModelForCausalLM.from_pretrained(base_model_path)
        model = PeftModel.from_pretrained(model, previous_lora_path)
        model = model.merge_and_unload()  # Merge previous stage
    else:
        model = AutoModelForCausalLM.from_pretrained(base_model_path)
    
    # Add new LoRA for this stage
    lora_config = LoraConfig(
        r=32,
        lora_alpha=64,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
    )
    model = get_peft_model(model, lora_config)
    
    # Train...
    train(model)
    
    # Save LoRA only
    model.save_pretrained(f"stage_{n}_lora/")
    
    return model

# Generation Between Stages
def generate_for_next_stage(n, base_model_path, lora_path):
    # Load and merge for quality
    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.float16,  # Higher precision for generation
        device_map="auto"
    )
    model = PeftModel.from_pretrained(model, lora_path)
    model = model.merge_and_unload()
    
    # Generate high-quality data
    return generate_training_data(model)
```

## Summary

- **Save**: LoRA adapters after each stage (MUST DO)
- **Merge**: For generation between stages (QUALITY)
- **Final**: Save merged Stage 6 for publication
- **Total Storage**: ~70GB minimum, ~135GB comfortable
