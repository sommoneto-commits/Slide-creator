#!/bin/bash
# Build script for Linux/Mac - Creates SlideCreator executable
# Run this script from the project root directory

echo "========================================"
echo "  Slide Creator - Build Script"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is not installed"
    echo "Please install Python 3.10+ and try again"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists, if not copy from example
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Please edit .env and add your OPENAI_API_KEY before running!"
    echo ""
fi

# Build executable
echo ""
echo "Building executable..."
echo "This may take a few minutes..."
echo ""

pyinstaller slide_creator.spec --clean --noconfirm

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Build failed!"
    exit 1
fi

# Copy necessary files to dist folder
echo ""
echo "Copying configuration files..."
if [ ! -f "dist/.env" ]; then
    cp .env.example dist/.env.example
fi
mkdir -p dist/output
mkdir -p dist/sessions
mkdir -p dist/logs

# Make executable
chmod +x dist/SlideCreator

echo ""
echo "========================================"
echo "  Build completed successfully!"
echo "========================================"
echo ""
echo "The executable is located at:"
echo "  dist/SlideCreator"
echo ""
echo "Before running, make sure to:"
echo "  1. Copy .env.example to .env in the dist folder"
echo "  2. Edit .env and add your OPENAI_API_KEY"
echo ""
echo "To run: ./dist/SlideCreator"
echo ""
