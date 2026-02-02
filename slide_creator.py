#!/usr/bin/env python3
"""
Slide Creator - Entry point for executable.
This is the main entry point used by PyInstaller to create the .exe file.
"""
import sys
import os

# Ensure the app directory is in the path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = os.path.dirname(sys.executable)
else:
    # Running as script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Add to path
sys.path.insert(0, application_path)

# Set working directory
os.chdir(application_path)

# Create necessary directories if they don't exist
for directory in ['output', 'sessions', 'logs']:
    dir_path = os.path.join(application_path, directory)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# Import and run
from app.main import main

if __name__ == "__main__":
    main()
