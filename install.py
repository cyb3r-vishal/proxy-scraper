#!/usr/bin/env python
"""Install script for ProxyMaster

This script installs the required dependencies and sets up the ProxyMaster tool.

Created by: cyb3r_vishal (community DevKitX)
"""

"""Install script for ProxyMaster

This script installs the required dependencies and sets up the ProxyMaster tool.

Created by: cyb3r_vishal (community DevKitX)
"""

import os
import sys
import subprocess
from pathlib import Path

def print_step(step, message):
    """Print a step in the installation process"""
    print(f"\n[{step}] {message}")
    print("=" * 50)

def main():
    """Main installation function"""    
    print("\n=================================================")
    print("       ProxyMaster - Installation Script         ")
    print("       Created by: cyb3r_vishal                 ")
    print("       community DevKitX                      ")
    print("=================================================\n")
    
    # Get script directory
    script_dir = Path(__file__).parent.absolute()
    
    # Step 1: Create output directory
    print_step(1, "Creating output directory")
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)
    print(f"✓ Created directory: {output_dir}")
    
    # Step 2: Install dependencies
    print_step(2, "Installing dependencies")
    requirements_file = script_dir / "requirements.txt"
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("✗ Error installing dependencies")
        print("  Try running: pip install -r requirements.txt")
    
    # Step 2.5: Install GUI dependencies
    print_step(3, "Installing GUI dependencies")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter", "ttkthemes"])
        print("✓ GUI dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("✗ Error installing GUI dependencies")
        print("  Try running: pip install customtkinter ttkthemes")
    
    # Step 3: Make scripts executable (for Unix systems)
    if os.name != "nt":  # Skip on Windows
        print_step(4, "Making scripts executable")
        try:
            scripts = [
                script_dir / "proxymaster.py",
                script_dir / "proxy_monitor.py",
                script_dir / "proxy_geo.py",
                script_dir / "proxy_rotator.py",
                script_dir / "gui" / "proxymaster_gui.py",
                script_dir / "run-proxy.sh"
            ]
            for script in scripts:
                if script.exists():
                    os.chmod(script, 0o755)
                    print(f"✓ Made executable: {script}")
        except Exception as e:
            print(f"✗ Error making scripts executable: {e}")
    
    # Step 4: Verify installation
    print_step(4, "Verifying installation")
    try:
        # Import a key dependency as a test
        import rich
        print("✓ Verification successful")
    except ImportError:
        print("✗ Verification failed: 'rich' module not found")
        print("  Please try running the installer again or install manually")
    
    # Finished
    print("\n=================================================")
    print("           Installation Complete!                 ")
    print("=================================================\n")
    print("To use ProxyMaster, run:")
    if os.name == "nt":  # Windows
        print("  > .\\run-proxy.ps1 help")
    else:  # Unix
        print("  $ ./run-proxy.sh help")
    print("\n")

if __name__ == "__main__":
    main()
