#!/usr/bin/env bash
# Quickstart launcher for VERIDICT Decision Intelligence Engine

set -e

echo "=========================================================="
echo "⚡ VERIDICT: Regulated Decision Intelligence Engine"
echo "=========================================================="

echo ""
echo "Step 1: Running Automated Pytest Verification Suite..."
pytest -v

echo ""
echo "Step 2: Running Clinical Prior Authorization Case (GLP-1 Approval)..."
python3 -m veridict.cli run case_01_glp1_approve.json

echo ""
echo "Step 3: Running Adversarial Safety Override Case (MTC Boxed Warning)..."
python3 -m veridict.cli run case_02_glp1_deny_contraindication.json

echo ""
echo "Step 4: Running Cryptographic Audit Tampering Verification..."
python3 -m veridict.cli verify-audit case_01_glp1_approve.json

echo ""
echo "=========================================================="
echo "✓ All checks passed! Starting Web Showcase Portal..."
echo "  Open http://127.0.0.1:8000 in your browser"
echo "=========================================================="
python3 -m veridict.cli serve --port 8000
