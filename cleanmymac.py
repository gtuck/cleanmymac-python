#!/usr/bin/env python3
"""
CleanMyMac Python - A Mac cleaning and maintenance utility
Similar to CleanMyMac with features for system cleanup and optimization
"""

import os
import pwd
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta


class CleanMyMac:
    """Main class for Mac cleaning and maintenance operations"""
    
    def __init__(self):
        # Prefer the invoking user's home when running under sudo
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user and os.geteuid() == 0:
            try:
                self.home = pwd.getpwnam(sudo_user).pw_dir
            except KeyError:
                self.home = str(Path.home())
        else:
            self.home = str(Path.home())
        self.cleaned_size = 0
        
    def get_dir_size(self, path):
        """Calculate directory size in bytes"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        continue
        except (PermissionError, FileNotFoundError):
            pass
        return total_size
    
    def format_size(self, bytes_size):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"
    
    def clean_system_caches(self):
        """Clean system and user cache files"""
        print("\n[*] Cleaning system caches...")
        cache_dirs = [
            f"{self.home}/Library/Caches",
        ]
        
        total_cleaned = 0
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                size_before = self.get_dir_size(cache_dir)
                try:
                    for item in os.listdir(cache_dir):
                        item_path = os.path.join(cache_dir, item)
                        try:
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                        except (PermissionError, OSError) as e:
                            continue
                    
                    size_after = self.get_dir_size(cache_dir)
                    cleaned = size_before - size_after
                    total_cleaned += cleaned
                    print(f"  Cleaned: {self.format_size(cleaned)} from {cache_dir}")
                except PermissionError:
                    print(f"  Permission denied: {cache_dir}")
        
        self.cleaned_size += total_cleaned
        print(f"[✓] Total cache cleaned: {self.format_size(total_cleaned)}")
        return total_cleaned
    
    def clean_trash(self):
        """Empty trash bin"""
        print("\n[*] Emptying trash...")
        trash_path = f"{self.home}/.Trash"
        
        if os.path.exists(trash_path):
            size_before = self.get_dir_size(trash_path)
            try:
                for item in os.listdir(trash_path):
                    item_path = os.path.join(trash_path, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        else:
                            shutil.rmtree(item_path)
                    except (PermissionError, OSError):
                        continue
                
                self.cleaned_size += size_before
                print(f"[✓] Trash emptied: {self.format_size(size_before)}")
                return size_before
            except PermissionError:
                # Fallback 1: ask Finder (via AppleScript) to empty the trash to bypass TCC restrictions
                try:
                    result = subprocess.run(
                        [
                            "osascript",
                            "-e",
                            'tell application "Finder" to empty trash',
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    self.cleaned_size += size_before
                    print(f"[✓] Trash emptied via Finder")
                    return size_before
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback 2: when running under sudo, try as the invoking user
                    sudo_user = os.environ.get("SUDO_USER") if os.geteuid() == 0 else None
                    if sudo_user:
                        try:
                            subprocess.run(
                                [
                                    "sudo",
                                    "-u",
                                    sudo_user,
                                    "bash",
                                    "-lc",
                                    'find ~/.Trash -mindepth 1 -maxdepth 1 -exec rm -rf {} +',
                                ],
                                check=True,
                            )
                            self.cleaned_size += size_before
                            print(f"[✓] Trash emptied via user context: {self.format_size(size_before)}")
                            return size_before
                        except subprocess.CalledProcessError:
                            print(f"[!] Permission denied accessing trash at: {trash_path}")
                    else:
                        print(f"[!] Permission denied accessing trash at: {trash_path}")
        else:
            print("[✓] Trash is already empty")
        return 0
    
    def find_large_files(self, directory=None, min_size_mb=100):
        """Find files larger than specified size"""
        if directory is None:
            directory = self.home
        
        print(f"\n[*] Searching for files larger than {min_size_mb}MB in {directory}...")
        print("    This may take a while...\n")
        
        large_files = []
        min_size_bytes = min_size_mb * 1024 * 1024
        
        try:
            for root, dirs, files in os.walk(directory):
                # Skip system directories
                dirs[:] = [d for d in dirs if d not in ['Library', 'System', '.Trash']]
                
                for file in files:
                    try:
                        filepath = os.path.join(root, file)
                        size = os.path.getsize(filepath)
                        if size > min_size_bytes:
                            large_files.append((filepath, size))
                    except (OSError, FileNotFoundError, PermissionError):
                        continue
        except (PermissionError, FileNotFoundError):
            pass
        
        # Sort by size descending
        large_files.sort(key=lambda x: x[1], reverse=True)
        
        if large_files:
            print(f"Found {len(large_files)} large files:\n")
            for i, (filepath, size) in enumerate(large_files[:20], 1):  # Show top 20
                print(f"  {i}. {filepath}")
                print(f"     Size: {self.format_size(size)}\n")
        else:
            print(f"[✓] No files larger than {min_size_mb}MB found")
        
        return large_files
    
    def find_old_files(self, directory=None, days_old=180):
        """Find files older than specified days"""
        if directory is None:
            directory = self.home
        
        print(f"\n[*] Searching for files older than {days_old} days...")
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        old_files = []
        
        try:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if d not in ['Library', 'System', '.Trash']]
                
                for file in files:
                    try:
                        filepath = os.path.join(root, file)
                        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if mtime < cutoff_date:
                            size = os.path.getsize(filepath)
                            old_files.append((filepath, size, mtime))
                    except (OSError, FileNotFoundError, PermissionError):
                        continue
        except (PermissionError, FileNotFoundError):
            pass
        
        if old_files:
            total_size = sum(f[1] for f in old_files)
            print(f"[✓] Found {len(old_files)} old files (Total: {self.format_size(total_size)})")
        else:
            print(f"[✓] No files older than {days_old} days found")
        
        return old_files
    
    def clean_logs(self):
        """Clean system and application logs"""
        print("\n[*] Cleaning log files...")
        log_dirs = [
            f"{self.home}/Library/Logs",
        ]
        
        total_cleaned = 0
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                size_before = self.get_dir_size(log_dir)
                try:
                    for root, dirs, files in os.walk(log_dir):
                        for file in files:
                            if file.endswith('.log') or file.endswith('.txt'):
                                filepath = os.path.join(root, file)
                                try:
                                    size = os.path.getsize(filepath)
                                    os.remove(filepath)
                                    total_cleaned += size
                                except (PermissionError, OSError):
                                    continue
                    print(f"  Cleaned: {self.format_size(total_cleaned)} from {log_dir}")
                except PermissionError:
                    print(f"  Permission denied: {log_dir}")
        
        self.cleaned_size += total_cleaned
        print(f"[✓] Total logs cleaned: {self.format_size(total_cleaned)}")
        return total_cleaned
    
    def free_memory(self):
        """Free up RAM (macOS purge command)"""
        print("\n[*] Freeing up RAM...")
        try:
            result = subprocess.run(['purge'], capture_output=True, text=True)
            if result.returncode == 0:
                print("[✓] Memory freed successfully")
                return True
            else:
                print("[!] Failed to free memory")
                return False
        except FileNotFoundError:
            print("[!] 'purge' command not found (macOS only)")
            return False
        except PermissionError:
            print("[!] Permission denied. Try running with sudo")
            return False
    
    def flush_dns_cache(self):
        """Flush DNS cache"""
        print("\n[*] Flushing DNS cache...")
        try:
            subprocess.run(['dscacheutil', '-flushcache'], check=True)
            subprocess.run(['sudo', 'killall', '-HUP', 'mDNSResponder'], check=True)
            print("[✓] DNS cache flushed successfully")
            return True
        except subprocess.CalledProcessError:
            print("[!] Failed to flush DNS cache")
            return False
        except FileNotFoundError:
            print("[!] Command not found (macOS only)")
            return False
    
    def get_disk_usage(self):
        """Get disk usage information"""
        print("\n[*] Disk Usage:")
        try:
            stat = shutil.disk_usage(self.home)
            total = self.format_size(stat.total)
            used = self.format_size(stat.used)
            free = self.format_size(stat.free)
            percent = (stat.used / stat.total) * 100
            
            print(f"  Total: {total}")
            print(f"  Used: {used} ({percent:.1f}%)")
            print(f"  Free: {free}")
        except Exception as e:
            print(f"[!] Error getting disk usage: {e}")


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
    print("0.  Exit")
    print("\n" + "="*50)


def main():
    """Main application loop"""
    cleaner = CleanMyMac()
    
    print("\n⚠️  WARNING: This tool will delete files. Use at your own risk!")
    print("    Always backup important data before cleaning.\n")
    
    while True:
        print_menu()
        choice = input("\nSelect an option: ").strip()
        
        if choice == '1':
            cleaner.clean_system_caches()
        
        elif choice == '2':
            cleaner.clean_trash()
        
        elif choice == '3':
            cleaner.clean_logs()
        
        elif choice == '4':
            size_input = input("Enter minimum file size in MB (default 100): ").strip()
            min_size = int(size_input) if size_input.isdigit() else 100
            cleaner.find_large_files(min_size_mb=min_size)
        
        elif choice == '5':
            days_input = input("Enter days old (default 180): ").strip()
            days = int(days_input) if days_input.isdigit() else 180
            cleaner.find_old_files(days_old=days)
        
        elif choice == '6':
            cleaner.free_memory()
        
        elif choice == '7':
            cleaner.flush_dns_cache()
        
        elif choice == '8':
            cleaner.get_disk_usage()
        
        elif choice == '9':
            print("\n[*] Running all cleaners...")
            cleaner.clean_system_caches()
            cleaner.clean_trash()
            cleaner.clean_logs()
            cleaner.get_disk_usage()
            print(f"\n[✓] Total space cleaned: {cleaner.format_size(cleaner.cleaned_size)}")
        
        elif choice == '0':
            print("\n[✓] Exiting CleanMyMac Python. Stay clean!\n")
            sys.exit(0)
        
        else:
            print("\n[!] Invalid option. Please try again.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[✓] Interrupted by user. Exiting...\n")
        sys.exit(0)
