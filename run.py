#!/usr/bin/env python
"""
progTek-pwm-client launcher

This script launches the progTek Password Manager client application.
"""
import os
import sys
import subprocess
import platform

def main():
    """Main entry point for the application launcher."""
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the main.py file
    main_script = os.path.join(script_dir, "src", "main.py")
    
    if not os.path.exists(main_script):
        print(f"Error: Could not find {main_script}")
        return 1
    
    # Check if running in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if not in_venv:
        venv_dir = os.path.join(script_dir, "venv")
        venv_bin_dir = os.path.join(venv_dir, "Scripts" if platform.system() == "Windows" else "bin")
        venv_python = os.path.join(venv_bin_dir, "python" + (".exe" if platform.system() == "Windows" else ""))
        
        if os.path.exists(venv_python):
            print("Using virtual environment Python interpreter.")
            python_exe = venv_python
        else:
            print("Warning: No virtual environment found. Using system Python interpreter.")
            python_exe = sys.executable
    else:
        # Already in venv, use current interpreter
        python_exe = sys.executable
    
    print(f"Starting progTek Password Manager client...")
    print(f"Python interpreter: {python_exe}")
    print(f"Main script: {main_script}\n")
    
    # Run the main script
    try:
        result = subprocess.run([python_exe, main_script], check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running application: {e}")
        return e.returncode
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
        return 130  # Standard UNIX exit code for SIGINT

if __name__ == "__main__":
    sys.exit(main())