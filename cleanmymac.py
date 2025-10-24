#!/usr/bin/env python3
"""
CleanMyMac Python - Mac cleaning and maintenance utility (CLI)
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from cleanmymac_core import CleanMyMac


def print_menu():
    """Display main menu"""
    print("\n" + "="*50)
    print("  CleanMyMac Python - Mac Cleaner & Maintenance")
    print("="*50)
    print("\n1.  Clean system caches")
    print("2.  Empty trash")
    print("3.  Clean log files")
    print("4.  Find large files (>100MB)")
    print("5.  Find old files (>180 days)")
    print("6.  Free up RAM")
    print("7.  Flush DNS cache")
    print("8.  Show disk usage")
    print("9.  Run all cleaners")
    print("10. Empty per-volume trashes (/Volumes/*)")
    print("0.  Exit")
    print("\n" + "="*50)


def main():
    """CLI entrypoint: parse args or run interactive menu"""
    parser = argparse.ArgumentParser(description="CleanMyMac Python")
    # actions
    parser.add_argument("--clean-caches", action="store_true", help="Clean ~/Library/Caches")
    parser.add_argument("--clean-trash", action="store_true", help="Empty ~/.Trash")
    parser.add_argument("--clean-logs", action="store_true", help="Clean ~/Library/Logs (*.log, *.txt)")
    parser.add_argument("--per-volume-trash", action="store_true", help="Empty /Volumes/*/.Trashes/<uid> and .Trash")
    parser.add_argument("--find-large", action="store_true", help="Find large files")
    parser.add_argument("--min-size", type=int, default=100, help="Minimum size in MB for --find-large (default 100)")
    parser.add_argument("--find-old", action="store_true", help="Find old files")
    parser.add_argument("--days", type=int, default=180, help="Age in days for --find-old (default 180)")
    parser.add_argument("--disk-usage", action="store_true", help="Show disk usage")
    parser.add_argument("--free-ram", action="store_true", help="Free inactive memory using purge")
    parser.add_argument("--flush-dns", action="store_true", help="Flush DNS cache (requires sudo)")
    parser.add_argument("--all", action="store_true", help="Run all cleaners (caches, trash, logs)")
    # behavior
    parser.add_argument("--dry-run", action="store_true", help="Do not delete anything; show what would be done")
    parser.add_argument("--yes", action="store_true", help="Assume yes for non-interactive deletions")
    parser.add_argument("--log", type=Path, help="Log actions to this file")
    parser.add_argument("--limit", type=int, default=20, help="Limit count for large-file listing (default 20)")
    parser.add_argument("--paths", type=Path, nargs="*", help="Optional paths for find operations (default $HOME)")

    args = parser.parse_args()

    # If no action args given, run interactive menu
    any_action = any([
        args.clean_caches, args.clean_trash, args.clean_logs, args.per_volume_trash, args.find_large,
        args.find_old, args.disk_usage, args.free_ram, args.flush_dns, args.all
    ])

    log_handle = None
    try:
        if args.log:
            log_handle = args.log.open("a", encoding="utf-8")
    except Exception:
        log_handle = None

    cleaner = CleanMyMac(dry_run=args.dry_run, logger=log_handle)

    if not any_action:
        print("\n⚠️  WARNING: This tool will delete files. Use at your own risk!")
        print("    Always backup important data before cleaning.\n")
        if os.geteuid() == 0:
            sudo_user = os.environ.get("SUDO_USER")
            target_user = sudo_user or "root"
            print(f"Note: Running under sudo; targeting {target_user}'s home for user-level actions.")
        print("Tip: For Trash/caches, grant Terminal Full Disk Access (Settings → Privacy & Security).\n")

        while True:
            print_menu()
            choice = input("\nSelect an option: ").strip()

            if choice == '1':
                stats = cleaner.clean_system_caches()
                print(f"[✓] Total cache cleaned: {cleaner.format_size(stats.bytes_freed)}")

            elif choice == '2':
                stats = cleaner.clean_trash()
                print(f"[✓] Trash emptied: {cleaner.format_size(stats.bytes_freed)}")

            elif choice == '3':
                stats = cleaner.clean_logs()
                print(f"[✓] Total logs cleaned: {cleaner.format_size(stats.bytes_freed)}")

            elif choice == '4':
                size_input = input("Enter minimum file size in MB (default 100): ").strip()
                min_size = int(size_input) if size_input.isdigit() else 100
                print(f"\n[*] Searching for files larger than {min_size}MB in {cleaner.home}...")
                files = cleaner.find_large_files(min_size_mb=min_size)
                if files:
                    print(f"Found {len(files)} large files:\n")
                    for i, (p, s) in enumerate(files, 1):
                        print(f"  {i}. {p}")
                        print(f"     Size: {cleaner.format_size(s)}\n")
                else:
                    print(f"[✓] No files larger than {min_size}MB found")

            elif choice == '5':
                days_input = input("Enter days old (default 180): ").strip()
                days = int(days_input) if days_input.isdigit() else 180
                print(f"\n[*] Searching for files older than {days} days...")
                files = cleaner.find_old_files(days_old=days)
                if files:
                    total = sum(s for _, s, _ in files)
                    print(f"[✓] Found {len(files)} old files (Total: {cleaner.format_size(total)})")
                else:
                    print(f"[✓] No files older than {days} days found")

            elif choice == '6':
                print("\n[*] Freeing up RAM...")
                ok = cleaner.free_memory()
                print("[✓] Memory freed successfully" if ok else "[!] Failed to free memory")

            elif choice == '7':
                print("\n[*] Flushing DNS cache...")
                ok = cleaner.flush_dns_cache()
                if ok:
                    print("[✓] DNS cache flushed successfully")
                else:
                    need_sudo = " (requires sudo)" if os.geteuid() != 0 else ""
                    print(f"[!] Failed to flush DNS cache{need_sudo}")

            elif choice == '8':
                total, used, free = cleaner.get_disk_usage()
                percent = (used / total) * 100 if total else 0
                print("\n[*] Disk Usage:")
                print(f"  Total: {cleaner.format_size(total)}")
                print(f"  Used: {cleaner.format_size(used)} ({percent:.1f}%)")
                print(f"  Free: {cleaner.format_size(free)}")

            elif choice == '9':
                print("\n[*] Running all cleaners...")
                s1 = cleaner.clean_system_caches()
                s2 = cleaner.clean_trash()
                s3 = cleaner.clean_logs()
                total_bytes = s1.bytes_freed + s2.bytes_freed + s3.bytes_freed
                print(f"\n[✓] Total space cleaned: {cleaner.format_size(total_bytes)}")

            elif choice == '10':
                stats = cleaner.clean_per_volume_trash()
                print(f"[✓] Total per-volume trash cleaned: {cleaner.format_size(stats.bytes_freed)}")

            elif choice == '0':
                print("\n[✓] Exiting CleanMyMac Python. Stay clean!\n")
                sys.exit(0)

            else:
                print("\n[!] Invalid option. Please try again.")

            input("\nPress Enter to continue...")
        # end interactive loop

    # Non-interactive path
    def confirm_or_exit():
        if args.yes:
            return
        print("This action will delete files. Re-run with --yes to proceed or use --dry-run.")
        sys.exit(2)

    exit_code = 0
    if args.all or args.clean_caches or args.clean_logs or args.clean_trash or args.per_volume_trash:
        confirm_or_exit()

    if args.all or args.clean_caches:
        stats = cleaner.clean_system_caches()
        print(f"[✓] Cache cleaned: {cleaner.format_size(stats.bytes_freed)}")

    if args.all or args.clean_trash:
        stats = cleaner.clean_trash()
        print(f"[✓] Trash cleaned: {cleaner.format_size(stats.bytes_freed)}")

    if args.all or args.clean_logs:
        stats = cleaner.clean_logs()
        print(f"[✓] Logs cleaned: {cleaner.format_size(stats.bytes_freed)}")

    if args.per_volume_trash:
        stats = cleaner.clean_per_volume_trash()
        print(f"[✓] Per-volume trash cleaned: {cleaner.format_size(stats.bytes_freed)}")

    if args.find_large:
        roots = args.paths or [cleaner.home]
        for root in roots:
            print(f"\n[*] Searching for files larger than {args.min_size}MB in {root}...")
            files = cleaner.find_large_files(directory=Path(root), min_size_mb=args.min_size, limit=args.limit)
            if files:
                print(f"Found {len(files)} large files:\n")
                for i, (p, s) in enumerate(files, 1):
                    print(f"  {i}. {p}")
                    print(f"     Size: {cleaner.format_size(s)}\n")
            else:
                print(f"[✓] No files larger than {args.min_size}MB found in {root}")

    if args.find_old:
        roots = args.paths or [cleaner.home]
        for root in roots:
            print(f"\n[*] Searching for files older than {args.days} days in {root}...")
            files = cleaner.find_old_files(directory=Path(root), days_old=args.days)
            if files:
                total = sum(s for _, s, _ in files)
                print(f"[✓] Found {len(files)} old files (Total: {cleaner.format_size(total)})")
            else:
                print(f"[✓] No files older than {args.days} days found in {root}")

    if args.disk_usage:
        total, used, free = cleaner.get_disk_usage()
        percent = (used / total) * 100 if total else 0
        print("\n[*] Disk Usage:")
        print(f"  Total: {cleaner.format_size(total)}")
        print(f"  Used: {cleaner.format_size(used)} ({percent:.1f}%)")
        print(f"  Free: {cleaner.format_size(free)}")

    if args.free_ram:
        ok = cleaner.free_memory()
        print("[✓] Memory freed successfully" if ok else "[!] Failed to free memory")
        if not ok:
            exit_code = max(exit_code, 1)

    if args.flush_dns:
        ok = cleaner.flush_dns_cache()
        if ok:
            print("[✓] DNS cache flushed successfully")
        else:
            need_sudo = " (requires sudo)" if os.geteuid() != 0 else ""
            print(f"[!] Failed to flush DNS cache{need_sudo}")
            exit_code = max(exit_code, 1)

    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[✓] Interrupted by user. Exiting...\n")
        sys.exit(0)
