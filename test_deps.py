#!/usr/bin/env python3
"""Quick test of dependency checker"""

from src.video2md.utils.dependency_checker import DependencyChecker

print("Testing dependency checker...")
all_ok, messages = DependencyChecker.check_all_dependencies(require_ffmpeg=True, require_node=True)

print("\n" + "="*60)
print("Dependency Check Results")
print("="*60)
for msg in messages:
    print(msg)
print("="*60)

if all_ok:
    print("\n✓ All dependencies are available!")
else:
    print("\n✗ Some dependencies are missing!")

print(f"\nResult: {all_ok}")
