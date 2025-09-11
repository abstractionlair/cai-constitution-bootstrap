#!/bin/bash
# Deploy to RunPod using git tags and proxy SSH

set -e  # Exit on error

# Configuration
LOCAL_REPO="/Users/scottmcguire/MaximalCAI"
GITHUB_REPO="https://github.com/abstractionlair/cai-constitution-bootstrap.git"
SSH_PROXY="tupdqnn4ka2obr-6441138e@ssh.runpod.io"
SSH_KEY="~/.ssh/id_ed25519"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Stage 1 Deployment via Git${NC}"
echo "================================"

# Step 1: Create deployment tag
cd "$LOCAL_REPO"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TAG_NAME="stage1-deploy-${TIMESTAMP}"

echo -e "${YELLOW}Creating deployment tag: ${TAG_NAME}${NC}"
git add -A
git commit -m "Deployment checkpoint ${TIMESTAMP}" || true
git tag -a "$TAG_NAME" -m "Stage 1 deployment ${TIMESTAMP}"
git push origin main
git push origin "$TAG_NAME"

echo -e "${GREEN}✓ Tag created and pushed${NC}"

# Step 2: Create deployment script for RunPod
cat > /tmp/runpod_deploy.sh << 'DEPLOY_SCRIPT'
#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Setting up deployment on RunPod...${NC}"

# Create run directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_DIR="/workspace/runs/stage1_${TIMESTAMP}"
mkdir -p "$RUN_DIR"
cd "$RUN_DIR"

# Clone specific tag
TAG_NAME="$1"
echo -e "${YELLOW}Cloning repository at tag: ${TAG_NAME}${NC}"
git clone --branch "$TAG_NAME" --depth 1 https://github.com/abstractionlair/cai-constitution-bootstrap.git code
cd code

# Setup environment
echo -e "${YELLOW}Setting up Python environment...${NC}"
pip install -q transformers torch datasets trl peft unsloth
pip install -q wandb tqdm pyyaml

# Verify GPU
echo -e "${YELLOW}Verifying GPU...${NC}"
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')"
python -c "import torch; print(f'Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB')"

# Create artifact directories
mkdir -p artifacts logs checkpoints results

echo -e "${GREEN}✓ Deployment ready at: ${RUN_DIR}${NC}"
echo -e "${GREEN}✓ Next: Run python scripts/stage1_incremental.py${NC}"

DEPLOY_SCRIPT

# Step 3: Transfer and execute deployment script
echo -e "${YELLOW}Deploying to RunPod...${NC}"

# Using stdin to pass script content
ssh -i "$SSH_KEY" "$SSH_PROXY" "cat > /tmp/deploy.sh && chmod +x /tmp/deploy.sh && /tmp/deploy.sh $TAG_NAME" < /tmp/runpod_deploy.sh

echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "1. SSH into RunPod: ssh -i $SSH_KEY $SSH_PROXY"
echo "2. Navigate to run: cd /workspace/runs/stage1_*"
echo "3. Run incremental pipeline: python code/scripts/stage1_incremental.py"