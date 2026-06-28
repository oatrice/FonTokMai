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
    
    # Bring the test script from the target branch (since it might not exist in older commits)
    # Also bring any test-related utility files if needed, here we bring the mock script
    git checkout $TARGET_BRANCH -- backend/tests/scratch_render_rain.py
    
    # Run the script (Assuming it outputs images to the current directory or a specific folder)
    # You might need to adjust the command depending on how your script is executed
    export PYTHONPATH=$(pwd)/backend:$PYTHONPATH
    cd backend
    if [ -f ".venv/bin/python" ]; then
        .venv/bin/python -m tests.scratch_render_rain
    elif [ -f "venv/bin/python" ]; then
        venv/bin/python -m tests.scratch_render_rain
    else
        python3 -m tests.scratch_render_rain
    fi
    cd ..
    
    # Create a directory for this commit's output
    mkdir -p comparison_output/$COMMIT
    
    # Move the generated images to the commit's folder
    # Assuming the script generates .png files in the backend folder or root
    # Adjust this path based on where scratch_render_rain.py saves its output!
    mv backend/*.png comparison_output/$COMMIT/ 2>/dev/null || true
    mv *.png comparison_output/$COMMIT/ 2>/dev/null || true
    
    # Clean up the checked out test file so git checkout can proceed to the next
    git checkout -- backend/tests/scratch_render_rain.py
done

# Restore original branch
git checkout $CURRENT_BRANCH
echo "=========================================="
echo "Comparison complete! Check the 'comparison_output' folder."
