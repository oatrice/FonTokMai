#!/bin/bash

# Target branch with the latest tests
TARGET_BRANCH="feat/121-feature-parametric-mock-scenar_"
START_COMMIT="813eb40"

# Create output directory
mkdir -p comparison_output

# Get list of commits from START_COMMIT to TARGET_BRANCH
COMMITS=$(git log --oneline ${START_COMMIT}^..${TARGET_BRANCH} --reverse | awk '{print $1}')

# Save current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

for COMMIT in $COMMITS; do
    echo "=========================================="
    echo "Testing commit: $COMMIT"
    
    # Checkout the commit
    git checkout $COMMIT
    # Run the script
    export PYTHONPATH=$(pwd)/backend:$PYTHONPATH
    if [ -f "backend/.venv/bin/python" ]; then
        PYTHON_CMD="backend/.venv/bin/python"
    elif [ -f "backend/venv/bin/python" ]; then
        PYTHON_CMD="backend/venv/bin/python"
    else
        PYTHON_CMD="python3"
    fi
    
    $PYTHON_CMD compare_scenario.py
    
    # Create a directory for this commit's output
    mkdir -p comparison_output/$COMMIT
    
    # Move the generated images to the commit's folder
    mv tracking_skn240_test.png comparison_output/$COMMIT/ 2>/dev/null || true
done

# Restore original branch
git checkout $CURRENT_BRANCH
echo "=========================================="
echo "Comparison complete! Check the 'comparison_output' folder."
