#!/bin/bash

echo "=========================================="
echo "RSI Divergence System - Dependency Setup"
echo "=========================================="
echo ""

# Install dependencies
echo "Installing required Python packages..."
pip3 install --user pandas numpy scipy yfinance

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "To run the system:"
echo ""
echo "  # Test with a single ticker"
echo "  python main.py --ticker AAPL --timeframes 1d"
echo ""
echo "  # Scan all Nasdaq 100 stocks (takes several minutes)"
echo "  python main.py"
echo ""
echo "  # View results"
echo "  python main.py --view-signals 20"
echo ""
