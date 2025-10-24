#!/usr/bin/env python3
import os
import shutil
from pathlib import Path

# Common macOS directories where apps store leftover files
SEARCH_PATHS = [
    "~/Library/Application Support",
    "~/Library/Caches",
    "~/Library/Preferences",
    "~/Library/LaunchAgents",
    "~/Library/Containers",
    "~/Library/Saved Application State",
    "/Library/Application Support",
    "/Library/LaunchDaemons",
    "/Library/Preferences"
]

def find_leftovers(app_name: str):
    leftovers = []
    for base_path in SEARCH_PATHS:
        path = Path(os.path.expanduser(base_path))
        if not path.exists():
            continue
        for root, dirs, files in os.walk(path):
            for name in dirs + files:
                if app_name.lower() in name.lower():
                    leftovers.append(Path(root) / name)
    return leftovers

def delete_leftovers(leftovers):
    for item in leftovers:
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
            print(f"Deleted: {item}")
        except Exception as e:
            print(f"Error deleting {item}: {e}")

def main():
    app_name = input("Enter the app name to clean leftovers for: ").strip()
    if not app_name:
        print("No app name entered. Exiting.")
        return

    print("\nScanning for leftover files...")
    leftovers = find_leftovers(app_name)

    if not leftovers:
        print("No leftover files found.")
        return

    print(f"\nFound {len(leftovers)} leftover items:")
    for item in leftovers:
        print(f"  - {item}")

    confirm = input("\nDelete all these files? (y/N): ").lower()
    if confirm == 'y':
        delete_leftovers(leftovers)
    else:
        print("Aborted cleanup.")

if __name__ == "__main__":
    main()
