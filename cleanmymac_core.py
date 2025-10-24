#!/usr/bin/env python3
from __future__ import annotations

"""
Core logic for CleanMyMac Python.

This module holds the non-UI logic so it can be reused by a CLI or other tools.
"""

import os
import pwd
import shutil
import stat
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def is_within(base: Path, target: Path) -> bool:
    try:
        base_r = base.resolve()
        target_r = target.resolve()
    except FileNotFoundError:
        # If target disappeared, it's not within; treat as safe noop
        return False
    try:
        target_r.relative_to(base_r)
        return True
    except ValueError:
        return False


def iter_entries(path: Path) -> Iterable[os.DirEntry]:
    try:
        with os.scandir(path) as it:
            for entry in it:
                yield entry
    except (PermissionError, FileNotFoundError):
        return


@dataclass
class CleanStats:
    bytes_freed: int = 0
    files_deleted: int = 0
    dirs_deleted: int = 0


class CleanMyMac:
    def __init__(self, dry_run: bool = False, logger=None):
        # Prefer the invoking user's home when running under sudo
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user and os.geteuid() == 0:
            try:
                self.home = Path(pwd.getpwnam(sudo_user).pw_dir)
            except KeyError:
                self.home = Path.home()
        else:
            self.home = Path.home()

        self.cleaned_size = 0
        self.stats = CleanStats()
        self.dry_run = dry_run
        self.log = logger

    # ---------- Utilities ----------

    def _log(self, msg: str) -> None:
        if self.log:
            try:
                self.log.write(msg + "\n")
                self.log.flush()
            except Exception:
                pass

    def format_size(self, bytes_size: int) -> str:
        size = float(bytes_size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def get_dir_size(self, path: Path) -> int:
        total = 0
        try:
            for root, dirs, files in os.walk(path, followlinks=False):
                for f in files:
                    fp = Path(root) / f
                    try:
                        st = os.stat(fp, follow_symlinks=False)
                        total += st.st_size
                    except (OSError, FileNotFoundError):
                        continue
        except (PermissionError, FileNotFoundError):
            pass
        return total

    def _safe_delete(self, base: Path, target: Path) -> Tuple[int, int, int]:
        """Delete target safely without following symlinks. Returns (bytes, files, dirs)."""
        bytes_freed = files_deleted = dirs_deleted = 0
        if not is_within(base, target):
            return 0, 0, 0

        try:
            st = os.lstat(target)
        except FileNotFoundError:
            return 0, 0, 0
        except PermissionError:
            return 0, 0, 0

        # Size accounting: for files/symlinks use st_size; for dirs, compute recursively
        if stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode):
            size_before = self.get_dir_size(target)
            if self.dry_run:
                return size_before, 0, 1
            try:
                shutil.rmtree(target)
                return size_before, 0, 1
            except Exception:
                return 0, 0, 0
        else:
            size = st.st_size
            if self.dry_run:
                return size, 1, 0
            try:
                os.unlink(target)
                return size, 1, 0
            except Exception:
                return 0, 0, 0

    # ---------- Cleaners ----------

    def clean_system_caches(self) -> CleanStats:
        cache_dirs: List[Path] = [self.home / "Library" / "Caches"]
        total = CleanStats()
        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue
            base = cache_dir.resolve()
            for entry in iter_entries(base):
                target = base / entry.name
                b, f, d = self._safe_delete(base, target)
                total.bytes_freed += b
                total.files_deleted += f
                total.dirs_deleted += d
        self.cleaned_size += total.bytes_freed
        self.stats.bytes_freed += total.bytes_freed
        self.stats.files_deleted += total.files_deleted
        self.stats.dirs_deleted += total.dirs_deleted
        self._log(f"clean_caches bytes={total.bytes_freed} files={total.files_deleted} dirs={total.dirs_deleted}")
        return total

    def clean_trash(self) -> CleanStats:
        trash = self.home / ".Trash"
        total = CleanStats()
        if not trash.exists():
            return total
        base = trash.resolve()
        try:
            for entry in iter_entries(base):
                target = base / entry.name
                b, f, d = self._safe_delete(base, target)
                total.bytes_freed += b
                total.files_deleted += f
                total.dirs_deleted += d
        except PermissionError:
            # Fallback 1: AppleScript (Finder)
            try:
                subprocess.run([
                    "osascript",
                    "-e",
                    'tell application "Finder" to empty trash',
                ], check=True)
                # We cannot know bytes freed without enumerating; keep zeroed but not an error
                return total
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback 2: try as invoking user without shell
                if os.geteuid() == 0 and (sudo_user := os.environ.get("SUDO_USER")):
                    try:
                        user_home = Path(pwd.getpwnam(sudo_user).pw_dir)
                        user_trash = str((user_home / ".Trash").resolve())
                        find_bin = which("find") or "/usr/bin/find"
                        subprocess.run([
                            "sudo", "-u", sudo_user,
                            find_bin, user_trash, "-mindepth", "1", "-maxdepth", "1", "-delete"
                        ], check=True)
                        return total
                    except (subprocess.CalledProcessError, KeyError, FileNotFoundError):
                        return total
        self.cleaned_size += total.bytes_freed
        self.stats.bytes_freed += total.bytes_freed
        self.stats.files_deleted += total.files_deleted
        self.stats.dirs_deleted += total.dirs_deleted
        self._log(f"clean_trash bytes={total.bytes_freed} files={total.files_deleted} dirs={total.dirs_deleted}")
        return total

    def clean_per_volume_trash(self) -> CleanStats:
        volumes_root = Path("/Volumes")
        total = CleanStats()
        if not volumes_root.is_dir():
            return total
        # Determine target UID
        try:
            if os.geteuid() == 0 and os.environ.get("SUDO_USER"):
                uid = pwd.getpwnam(os.environ["SUDO_USER"]).pw_uid
            else:
                uid = os.getuid()
        except KeyError:
            uid = os.getuid()

        had_perm_issue = False
        for vol in volumes_root.iterdir():
            if not vol.is_dir():
                continue
            candidates = [vol / ".Trashes" / str(uid), vol / ".Trash"]
            for c in candidates:
                if not c.exists():
                    continue
                base = c.resolve()
                try:
                    for entry in iter_entries(base):
                        target = base / entry.name
                        b, f, d = self._safe_delete(base, target)
                        total.bytes_freed += b
                        total.files_deleted += f
                        total.dirs_deleted += d
                except PermissionError:
                    had_perm_issue = True
        if had_perm_issue:
            # Finder fallback empties all trashes
            try:
                subprocess.run([
                    "osascript",
                    "-e",
                    'tell application "Finder" to empty trash',
                ], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        self.cleaned_size += total.bytes_freed
        self.stats.bytes_freed += total.bytes_freed
        self.stats.files_deleted += total.files_deleted
        self.stats.dirs_deleted += total.dirs_deleted
        self._log(f"clean_per_volume_trash bytes={total.bytes_freed} files={total.files_deleted} dirs={total.dirs_deleted}")
        return total

    def clean_logs(self) -> CleanStats:
        log_dir = self.home / "Library" / "Logs"
        total = CleanStats()
        if not log_dir.exists():
            return total
        base = log_dir.resolve()
        for root, dirs, files in os.walk(base):
            for file in files:
                if file.endswith(".log") or file.endswith(".txt"):
                    fp = Path(root) / file
                    b, f, d = self._safe_delete(base, fp)
                    total.bytes_freed += b
                    total.files_deleted += f
                    total.dirs_deleted += d
        self.cleaned_size += total.bytes_freed
        self.stats.bytes_freed += total.bytes_freed
        self.stats.files_deleted += total.files_deleted
        self.stats.dirs_deleted += total.dirs_deleted
        self._log(f"clean_logs bytes={total.bytes_freed} files={total.files_deleted} dirs={total.dirs_deleted}")
        return total

    # ---------- Information ----------

    def find_large_files(self, directory: Optional[Path] = None, min_size_mb: int = 100,
                          limit: int = 20, paths_only: bool = False) -> List[Tuple[Path, int]]:
        if directory is None:
            directory = self.home
        min_size = min_size_mb * 1024 * 1024
        results: List[Tuple[Path, int]] = []
        try:
            for root, dirs, files in os.walk(directory):
                base = Path(root)
                # Skip system directories under home
                dirs[:] = [d for d in dirs if d not in ["Library", "System", ".Trash"]]
                for name in files:
                    fp = base / name
                    try:
                        st = os.stat(fp, follow_symlinks=False)
                        if st.st_size > min_size:
                            results.append((fp, st.st_size))
                    except (OSError, FileNotFoundError, PermissionError):
                        continue
        except (PermissionError, FileNotFoundError):
            pass
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit] if limit else results

    def find_old_files(self, directory: Optional[Path] = None, days_old: int = 180,
                        skip_system: bool = True) -> List[Tuple[Path, int, datetime]]:
        if directory is None:
            directory = self.home
        cutoff = datetime.now() - timedelta(days=days_old)
        results: List[Tuple[Path, int, datetime]] = []
        try:
            for root, dirs, files in os.walk(directory):
                if skip_system:
                    dirs[:] = [d for d in dirs if d not in ["Library", "System", ".Trash"]]
                base = Path(root)
                for name in files:
                    fp = base / name
                    try:
                        st = os.stat(fp, follow_symlinks=False)
                        mtime = datetime.fromtimestamp(st.st_mtime)
                        if mtime < cutoff:
                            results.append((fp, st.st_size, mtime))
                    except (OSError, FileNotFoundError, PermissionError):
                        continue
        except (PermissionError, FileNotFoundError):
            pass
        return results

    def free_memory(self) -> bool:
        purge = which("purge")
        if not purge:
            return False
        try:
            result = subprocess.run([purge], capture_output=True, text=True)
            return result.returncode == 0
        except PermissionError:
            return False

    def flush_dns_cache(self) -> bool:
        # Requires root for killall HUP mDNSResponder
        if os.geteuid() != 0:
            return False
        try:
            subprocess.run(["dscacheutil", "-flushcache"], check=True)
            subprocess.run(["killall", "-HUP", "mDNSResponder"], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_disk_usage(self) -> Tuple[int, int, int]:
        statv = shutil.disk_usage(self.home)
        return statv.total, statv.used, statv.free
