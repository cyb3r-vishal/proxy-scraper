#!/usr/bin/env python3
"""
GitHub Cleanup Script - Clean up unnecessary files before pushing to GitHub
This script removes temporary files, cache files, and compiled Python files
before pushing your code to GitHub.
"""

import os
import shutil
import glob
import sys
from pathlib import Path

# Root directory of the project
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Files that should be removed before pushing to GitHub
FILES_TO_REMOVE = [
    # Temporary files
    "*.tmp",
    "temp_*",
    "*.temp",
    
    # Generated proxy lists
    "proxies.txt",
    "http_proxies.txt",
    "https_proxies.txt",
    "socks4_proxies.txt",
    "socks5_proxies.txt",
    "test_proxies.txt",
    "fast_proxies.txt",
    "ultra_fast_proxies.txt",
    "*.proxies",
    "fresh_http_proxies.txt",
    
    # Logs
    "*.log",
    
    # Compiled Python
    "*.pyc",
    
    # Cache files
    "*.cache",
    "proxy_cache.json",
    "proxy_cache.json.tmp",
    
    # Unnecessary files for GitHub
    "NEW_README.md",
    "ENHANCEMENTS.md",
    "FAST_PROXY.md",
    
    # Database files (optionally back these up first)
    # "data/proxy_metrics.db",
]

# Directories to remove
DIRS_TO_REMOVE = [
    "__pycache__",
    "*.egg-info",
    "build",
    "dist",
    ".pytest_cache",
    "output",  # Contains only generated proxy lists
    "gui/output",  # Contains only generated proxy files
]

# Files to keep even if they match patterns above
FILES_TO_KEEP = [
    "requirements.txt",
    "user_agents.txt",
]

def clean_directory(directory):
    """Clean up a directory based on the defined patterns"""
    print(f"Cleaning directory: {directory}")
    
    # Remove files matching patterns
    for pattern in FILES_TO_REMOVE:
        for file_path in glob.glob(os.path.join(directory, pattern)):
            if os.path.isfile(file_path):
                # Check if file should be kept
                if any(os.path.basename(file_path) == keep_file for keep_file in FILES_TO_KEEP):
                    continue
                    
                print(f"Removing file: {file_path}")
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")
    
    # Handle directory removal
    for pattern in DIRS_TO_REMOVE:
        for dir_path in glob.glob(os.path.join(directory, pattern)):
            if os.path.isdir(dir_path):
                print(f"Removing directory: {dir_path}")
                try:
                    shutil.rmtree(dir_path)
                except Exception as e:
                    print(f"Error removing directory {dir_path}: {e}")
    
    # Clean subdirectories
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path) and item not in [d.rstrip("/") for d in DIRS_TO_REMOVE]:
            # Skip directories that have already been removed
            if os.path.exists(item_path):  
                clean_directory(item_path)

def main():
    """Main function to clean up the project"""
    print("Starting GitHub cleanup process...")
    
    # Create .gitignore if it doesn't exist
    gitignore_path = os.path.join(ROOT_DIR, ".gitignore")
    if not os.path.exists(gitignore_path):
        print("Creating .gitignore file...")
        with open(gitignore_path, "w") as f:
            f.write("# Python bytecode\n")
            f.write("__pycache__/\n")
            f.write("*.py[cod]\n")
            f.write("*$py.class\n\n")
            
            f.write("# Distribution / packaging\n")
            f.write("build/\n")
            f.write("dist/\n")
            f.write("*.egg-info/\n\n")
            
            f.write("# Local proxy files\n")
            f.write("proxies.txt\n")
            f.write("http_proxies.txt\n")
            f.write("https_proxies.txt\n")
            f.write("socks4_proxies.txt\n")
            f.write("socks5_proxies.txt\n")
            f.write("test_proxies.txt\n")
            f.write("fast_proxies.txt\n")
            f.write("ultra_fast_proxies.txt\n\n")
            
            f.write("# Cache files\n")
            f.write("*.cache\n")
            f.write("proxy_cache.json\n\n")
            
            f.write("# Logs\n")
            f.write("*.log\n\n")
            
            f.write("# Temporary files\n")
            f.write("*.tmp\n")
            f.write("temp_*\n\n")
    
    # Clean up the project directory
    clean_directory(ROOT_DIR)
    
    print("Cleanup completed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCleanup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during cleanup: {e}")
        sys.exit(1)