#!/usr/bin/env bash
# delete-all.sh — Remove the Engingers GPA Calculator agent and all its tools.
# Run from the workspace root: bash scripts/delete-all.sh

# Activate virtual environment
if [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f "../venv/Scripts/activate" ]; then
  source ../venv/Scripts/activate
elif [ -f "../venv/bin/activate" ]; then
  source ../venv/bin/activate
fi

echo "=== Engingers GPA Calculator — Delete All ==="
echo ""

echo "[1/2] Removing agent..."
orchestrate agents remove -n Engingers_gpa_calculator_agent --kind native || true

echo "[2/2] Removing tools..."
orchestrate tools remove -n Engingers_validate_subject_weights || true
orchestrate tools remove -n Engingers_calculate_subject_grade || true
orchestrate tools remove -n Engingers_calculate_cumulative_gpa || true
orchestrate tools remove -n Engingers_add_or_update_component || true
orchestrate tools remove -n Engingers_remove_component || true
orchestrate tools remove -n Engingers_review_subject_summary || true

echo ""
echo "=== Cleanup complete! ==="
