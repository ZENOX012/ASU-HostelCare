#!/usr/bin/env bash
echo "==============================================================="
echo "           ASU HostelCare — Starting Server"
echo "==============================================================="
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt
echo ""
echo "Starting server on port ${PORT:-8000}..."
python main.py
