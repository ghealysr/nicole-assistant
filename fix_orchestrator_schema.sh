#!/bin/bash
set -e

echo "=========================================="
echo "FAZ ORCHESTRATOR SCHEMA FIX"
echo "=========================================="

cd /opt/nicole

echo "✓ Fixing orchestrator to use allowed database values..."

# Replace "user_testing" activity type with "route" (allowed)
sed -i 's/"orchestrator", "user_testing",/"orchestrator", "route",/g' backend/app/services/faz_orchestrator.py

# Replace "awaiting_user_testing" status with "awaiting_qa_approval" (allowed)
sed -i 's/"awaiting_user_testing"/"awaiting_qa_approval"/g' backend/app/services/faz_orchestrator.py
sed -i "s/'awaiting_user_testing'/'awaiting_qa_approval'/g" backend/app/services/faz_orchestrator.py

# Update log messages to be more accurate
sed -i 's/Entering user testing phase/Moving to review phase for user testing/g' backend/app/services/faz_orchestrator.py
sed -i 's/Ready for user testing/Moving to review for user testing/g' backend/app/services/faz_orchestrator.py

echo "✓ Changes applied"
echo ""
echo "Verifying changes..."
grep -n "route.*user testing" backend/app/services/faz_orchestrator.py | head -2
grep -n "awaiting_qa_approval" backend/app/services/faz_orchestrator.py | head -2

echo ""
echo "=========================================="
echo "RESTARTING SERVICES"
echo "=========================================="
supervisorctl restart nicole-api nicole-worker

echo ""
echo "✓ Fix applied successfully!"
echo ""
echo "Next steps:"
echo "1. Test the pipeline by clicking 'Run Pipeline' on project 26 in the UI"
echo "2. The pipeline should now complete to awaiting_qa_approval status instead of crashing"

