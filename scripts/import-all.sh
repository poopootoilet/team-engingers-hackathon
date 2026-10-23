#!/usr/bin/env bash
# import-all.sh — Deploy the Engingers GPA Calculator agent and all its tools.
# Run from the workspace root: bash scripts/import-all.sh

set -e

# Activate virtual environment (check project root first, then parent)
if [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f "../venv/Scripts/activate" ]; then
  source ../venv/Scripts/activate
elif [ -f "../venv/bin/activate" ]; then
  source ../venv/bin/activate
else
  echo "ERROR: Could not find venv. Please create one and install ibm-watsonx-orchestrate."
  exit 1
fi

echo "=== Engingers GPA Calculator — Import All ==="
echo ""

echo "[1/2] Importing tools..."
orchestrate tools import -k python -f tools/Engingers_gpa_tools.py
echo "      ✓ Engingers_gpa_tools imported"

echo ""
echo "[2/2] Importing agent..."
orchestrate agents import -f agents/Engingers_gpa_calculator_agent.yaml
echo "      ✓ Engingers_gpa_calculator_agent imported"

echo ""
echo "=== Import complete! ==="
echo ""
echo "To test in the UI: open watsonx Orchestrate and chat with 'Engingers GPA Calculator'."
echo "To test via CLI:   orchestrate chat ask -n Engingers_gpa_calculator_agent \"I want to calculate my GPA\" -r"
