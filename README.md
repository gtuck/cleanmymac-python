# CleanMyMac Python

A Python-based Mac cleaner and maintenance tool with features similar to CleanMyMac. This utility provides system junk cleanup, trash management, large file finder, and system optimization utilities.

## Features

✨ **System Cleanup**
- Clean system and user cache files
- Empty trash bin
- Clean log files

🔍 **File Management**
- Find large files (customizable size threshold)
- Find old files (customizable age threshold)

⚡ **System Optimization**
- Free up RAM (purge command)
- Flush DNS cache
- Display disk usage statistics

## Requirements

- macOS (tested on macOS 10.15+)
- Python 3.6 or higher
- No external dependencies (uses only Python standard library)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/gtuck/cleanmymac-python.git
cd cleanmymac-python
```

2. Make the script executable:
```bash
chmod +x cleanmymac.py
```

3. Run the script:
```bash
python3 cleanmymac.py
```

## Usage

Simply run the script and follow the interactive menu:

```bash
python3 cleanmymac.py
```

Or install/run as a console script (via `pyproject.toml`):

```
cleanmymac
```

### Non-interactive CLI

All actions are available as flags suitable for automation:

```
cleanmymac --clean-caches --clean-trash --clean-logs --yes
cleanmymac --all --yes
cleanmymac --find-large --min-size 500 --paths ~/Downloads ~/Documents --limit 50
cleanmymac --find-old --days 365
cleanmymac --disk-usage
cleanmymac --free-ram
sudo cleanmymac --flush-dns
```

Useful flags:
- `--dry-run` show what would be deleted, without deleting
- `--yes` non-interactive confirmation for delete operations
- `--log FILE` append a logfile of actions
- `--paths` target directories for finders (defaults to `$HOME`)
- `--limit` cap number of results for `--find-large` (default 20)

### Menu Options

1. **Clean system caches** - Removes cached files from ~/Library/Caches
2. **Empty trash** - Empties the trash bin (~/.Trash)
3. **Clean log files** - Removes .log and .txt files from ~/Library/Logs
4. **Find large files** - Searches for files larger than specified size (default 100MB)
5. **Find old files** - Searches for files older than specified days (default 180 days)
6. **Free up RAM** - Runs the macOS `purge` command to free inactive memory
7. **Flush DNS cache** - Clears the DNS cache
8. **Show disk usage** - Displays current disk space usage
9. **Run all cleaners** - Executes cache cleaning, trash emptying, and log cleaning together
10. **Empty per-volume trashes** - Empties `.Trashes/<uid>` or `.Trash` on mounted volumes under `/Volumes/*`
0. **Exit** - Quit the application

## Safety Features

- Uses only Python standard library (no external dependencies)
- Error handling for permission denied scenarios
- Skips system-critical directories (System, Library)
- Warns users before deleting files
- Shows size of files being cleaned

## ⚠️ Warning

This tool **DELETES FILES**. Always backup important data before running cleanup operations. Use at your own risk.

## Permissions & Full Disk Access

macOS privacy (TCC) can block Terminal from accessing some folders (Trash, external volumes). If you see "Permission denied" or "Operation not permitted":

- Grant your terminal app Full Disk Access:
  - System Settings → Privacy & Security → Full Disk Access → add Terminal/iTerm and enable it.
- The tool now uses the invoking user's home when run with sudo (via `SUDO_USER`), so Trash and user-level actions still target your account.
- When Trash access is blocked, the tool also tries an AppleScript fallback: `osascript -e 'tell application "Finder" to empty trash'`.
 - DNS flushing is attempted only when already running as root; otherwise an informative message is shown.

Notes:
- Flushing DNS cache requires `sudo`.
- For user-level tasks (Trash, caches, logs), prefer running without `sudo`.

## Example Output

```
==================================================
  CleanMyMac Python - Mac Cleaner & Maintenance
==================================================

1.  Clean system caches
2.  Empty trash
3.  Clean log files
4.  Find large files (>100MB)
5.  Find old files (>180 days)
6.  Free up RAM
7.  Flush DNS cache
8.  Show disk usage
9.  Run all cleaners
0.  Exit

==================================================

Select an option: 1

[*] Cleaning system caches...
  Cleaned: 245.67 MB from /Users/username/Library/Caches
[✓] Total cache cleaned: 245.67 MB
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This software is provided "as is", without warranty of any kind. The authors are not responsible for any data loss or system damage that may occur from using this tool.

## Acknowledgments

Inspired by CleanMyMac by MacPaw - https://macpaw.com/cleanmymac
