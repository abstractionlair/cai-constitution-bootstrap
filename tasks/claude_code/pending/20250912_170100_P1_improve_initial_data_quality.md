# P1: Improve Initial Data Quality with Base Model Generation
Source: Gemini Review 20250912_165500
Priority: HIGH (P1)
Estimated Time: 45 minutes

## Issue Description
`scripts/generate_stage1_sft_data.py` uses hardcoded placeholder responses for SFT training data. This severely limits the quality of the entire pipeline since all subsequent training depends on this initial data quality.

## Location
File: `scripts/generate_stage1_sft_data.py`
Method: `generate_response_with_base_model()`
Lines: ~200-250 (placeholder response dictionaries)

## Suggested Fix
Replace placeholder responses with actual base model generation:
1. Load the base Qwen model in the data generation script
2. Use completion-style prompts to generate responses
3. Clean and validate the generated responses
4. Keep placeholders as fallback for failure cases

## Implementation Plan
```python
def load_base_model_for_generation(self):
    """Load base model for generating initial responses"""
    # Load quantized base model
    # Use completion-style prompting
    
def generate_response_with_base_model(self, instruction_data: Dict[str, Any]) -> str:
    """Generate response using actual base model instead of placeholders"""
    if not self.model:
        # Fallback to placeholder if model not available
        return self.generate_placeholder_response(instruction_data)
    
    # Use completion-style prompt
    completion_prompt = self.create_completion_prompt(instruction, inst_type)
    
    # Generate with base model
    response = self.model.generate(completion_prompt, max_tokens=150, temperature=0.7)
    
    # Clean and validate response
    return self.clean_response(response)
```

## Success Criteria
- [ ] Base model loaded for data generation
- [ ] Actual model-generated responses instead of placeholders
- [ ] Completion-style prompting for base model
- [ ] Response cleaning and validation
- [ ] Graceful fallback to placeholders if model unavailable
- [ ] Significantly improved initial data quality

## Impact
**HIGH** - Better initial data will dramatically improve the entire pipeline's effectiveness. The current placeholder responses are too simplistic and won't teach meaningful instruction-following behavior.