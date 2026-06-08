#!/bin/bash
cd "$(dirname "$0")"
echo "Starting KASIR PRO V3..."
pip install customtkinter pillow matplotlib --quiet 2>/dev/null
python3 run.py
