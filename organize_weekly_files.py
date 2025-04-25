import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

def validate_input_path(path: str) -> Path:
    """Validate input path and return Path object if valid."""
    path_obj = Path(path)
    if not path_obj.is_dir():
        print(f"Error: Path '{path}' does not exist or is not a directory.")
        sys.exit(1)
    return path_obj

def get_file_modification_date(file_path: Path) -> datetime:
    """Get the modification date of a file."""
    mod_time = file_path.stat().st_mtime
    return datetime.fromtimestamp(mod_time, tz=timezone.utc).date()

def organize_weekly_files(weekly_dir: Path) -> None:
    """Organize files in the Weekly directory to keep only the last file for each day."""
    if not weekly_dir.exists():
        print(f"Directory '{weekly_dir}' does not exist.")
        return

    # Dictionary to store the latest file for each day
    latest_files: Dict[datetime, Path] = {}

    # Iterate over all files in the Weekly directory
    for file in weekly_dir.rglob('*'):
        if file.is_file():
            file_date = get_file_modification_date(file)
            if file_date not in latest_files:
                latest_files[file_date] = file
            else:
                current_latest = latest_files[file_date]
                current_latest_mod_time = current_latest.stat().st_mtime
                file_mod_time = file.stat().st_mtime
                if file_mod_time > current_latest_mod_time:
                    # Newer file found, delete the old one and update the latest file
                    current_latest.unlink()
                    latest_files[file_date] = file
                else:
                    # Delete the newer file if it's a duplicate
                    file.unlink()
                    print(f"Deleted duplicate file: {file}")

    # Print the latest files kept
    for date, file in latest_files.items():
        print(f"Kept latest file for {date}: {file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python organize_weekly_files.py <weekly_directory_path>")
        sys.exit(1)
    
    weekly_path = validate_input_path(sys.argv[1])
    organize_weekly_files(weekly_path)
