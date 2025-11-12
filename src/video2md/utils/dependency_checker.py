#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dependency Checker
Validates that required external dependencies (ffmpeg, node.js) are installed
"""

import subprocess
import sys
import platform
from pathlib import Path
from typing import List, Tuple, Optional


class DependencyChecker:
    """Check for required external dependencies"""

    @staticmethod
    def check_command(command: str, version_args: List[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Check if a command is available in the system PATH.
        
        Args:
            command: Command name to check (e.g., 'ffmpeg', 'node')
            version_args: Arguments to get version (default: ['--version'])
            
        Returns:
            Tuple of (is_available, version_string)
        """
        if version_args is None:
            version_args = ['--version']
        
        try:
            result = subprocess.run(
                [command] + version_args,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract first line of output as version info
                version = result.stdout.strip().split('\n')[0] if result.stdout else "installed"
                return True, version
            return False, None
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False, None

    @staticmethod
    def get_install_instructions(command: str) -> str:
        """Get installation instructions for a command based on the OS"""
        os_name = platform.system()
        
        instructions = {
            'ffmpeg': {
                'Windows': 'Install ffmpeg:\n'
                          '  1. Download from https://ffmpeg.org/download.html\n'
                          '  2. Or use package manager:\n'
                          '     - Chocolatey: choco install ffmpeg\n'
                          '     - Scoop: scoop install ffmpeg\n'
                          '     - Winget: winget install ffmpeg',
                'Darwin': 'Install ffmpeg:\n'
                         '  brew install ffmpeg',
                'Linux': 'Install ffmpeg:\n'
                        '  - Ubuntu/Debian: sudo apt-get install ffmpeg\n'
                        '  - Fedora: sudo dnf install ffmpeg\n'
                        '  - Arch: sudo pacman -S ffmpeg'
            },
            'node': {
                'Windows': 'Install Node.js:\n'
                          '  1. Download from https://nodejs.org/\n'
                          '  2. Or use package manager:\n'
                          '     - Chocolatey: choco install nodejs\n'
                          '     - Scoop: scoop install nodejs\n'
                          '     - Winget: winget install OpenJS.NodeJS',
                'Darwin': 'Install Node.js:\n'
                         '  brew install node',
                'Linux': 'Install Node.js:\n'
                        '  - Ubuntu/Debian: sudo apt-get install nodejs npm\n'
                        '  - Fedora: sudo dnf install nodejs\n'
                        '  - Arch: sudo pacman -S nodejs npm'
            }
        }
        
        cmd_instructions = instructions.get(command, {})
        return cmd_instructions.get(os_name, f'Please install {command} for your operating system')

    @staticmethod
    def check_ffmpeg() -> Tuple[bool, str]:
        """
        Check if ffmpeg is installed.
        
        Returns:
            Tuple of (is_available, message)
        """
        is_available, version = DependencyChecker.check_command('ffmpeg', ['-version'])
        
        if is_available:
            return True, f"[OK] FFmpeg is available: {version}"
        else:
            instructions = DependencyChecker.get_install_instructions('ffmpeg')
            return False, f"[MISSING] FFmpeg is not installed or not in PATH.\n\n{instructions}"

    @staticmethod
    def check_node() -> Tuple[bool, str]:
        """
        Check if Node.js is installed.
        
        Returns:
            Tuple of (is_available, message)
        """
        is_available, version = DependencyChecker.check_command('node', ['--version'])
        
        if is_available:
            return True, f"[OK] Node.js is available: {version}"
        else:
            instructions = DependencyChecker.get_install_instructions('node')
            return False, f"[MISSING] Node.js is not installed or not in PATH.\n\n{instructions}"

    @staticmethod
    def check_all_dependencies(require_ffmpeg: bool = True, require_node: bool = True) -> Tuple[bool, List[str]]:
        """
        Check all required dependencies.
        
        Args:
            require_ffmpeg: Whether ffmpeg is required
            require_node: Whether Node.js is required
            
        Returns:
            Tuple of (all_available, list_of_messages)
        """
        messages = []
        all_ok = True
        
        if require_ffmpeg:
            ffmpeg_ok, ffmpeg_msg = DependencyChecker.check_ffmpeg()
            messages.append(ffmpeg_msg)
            all_ok = all_ok and ffmpeg_ok
        
        if require_node:
            node_ok, node_msg = DependencyChecker.check_node()
            messages.append(node_msg)
            all_ok = all_ok and node_ok
        
        return all_ok, messages

    @staticmethod
    def validate_or_exit(require_ffmpeg: bool = True, require_node: bool = True, exit_on_failure: bool = True):
        """
        Validate dependencies and optionally exit if any are missing.
        
        Args:
            require_ffmpeg: Whether ffmpeg is required
            require_node: Whether Node.js is required
            exit_on_failure: Whether to exit the program if dependencies are missing
        """
        all_ok, messages = DependencyChecker.check_all_dependencies(require_ffmpeg, require_node)
        
        # Print all messages with safe encoding
        print("\n" + "="*60)
        print("Dependency Check")
        print("="*60)
        for msg in messages:
            # Use safe print for Windows compatibility
            try:
                print(msg)
            except UnicodeEncodeError:
                # Fallback to ASCII-safe version
                print(msg.encode('ascii', 'replace').decode('ascii'))
        print("="*60 + "\n")
        
        if not all_ok:
            if exit_on_failure:
                print("ERROR: Missing required dependencies. Please install them and try again.\n")
                sys.exit(1)
            else:
                raise RuntimeError("Missing required dependencies: " + "\n".join(messages))


def check_dependencies(require_ffmpeg: bool = True, require_node: bool = True):
    """
    Convenience function to check dependencies.
    
    Args:
        require_ffmpeg: Whether ffmpeg is required
        require_node: Whether Node.js is required
        
    Returns:
        Tuple of (all_available, list_of_messages)
    """
    return DependencyChecker.check_all_dependencies(require_ffmpeg, require_node)


if __name__ == "__main__":
    # Self-test
    DependencyChecker.validate_or_exit()
