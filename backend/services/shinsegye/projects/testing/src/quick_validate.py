#!/usr/bin/env python3
import os
import subprocess
import sys


def main():
    print("Final Project Validation...")

    valid_count = 0
    error_count = 0
    total_count = 0

    # 현재 디렉토리의 모든 .py 파일 검사
    for file in os.listdir('.'):
        if file.endswith('.py') and not file.startswith('.'):
            total_count += 1
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'py_compile', file],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    valid_count += 1
                else:
                    error_count += 1
                    print(f"ERROR: {file}")
            except Exception:
                error_count += 1
                print(f"ERROR: {file}")

    print(f"\nResults Summary:")
    print(f"  Valid files: {valid_count}")
    print(f"  Error files: {error_count}")
    print(f"  Total files: {total_count}")
    print(f"  Success rate: {valid_count / total_count * 100:.1f}%")


if __name__ == "__main__":
    main()
