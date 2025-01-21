import os,shutil, sys
from datetime import datetime
from pathlib import Path

startpath = sys.argv[1]
if not (os.path.isdir(startpath)):
   print("start path NOT EXISTS")
   exit()

def find_all_files_with_pathlib(dir_path):
    return [str(file) for file in Path(dir_path).rglob('*') if file.is_file()]

def create_dest_path(date):
    dt_now = datetime.now()
    base_path = Path(startpath)
    if date.month == 12 and date.day == 31: #Year
        return base_path / "Year"
    elif date.day == 25 and date.month == dt_now.month: #Month
        return base_path / "Month"
    elif ((dt_now.timestamp()-date.timestamp()) >=86400) & ((dt_now.timestamp()-date.timestamp()) <= 604800): #Week
        return base_path / "Week"
    elif date.day == dt_now.day and date.month == dt_now.month and date.year == dt_now.year: #DAY
        return base_path / "Day"
    else:
        return "DELETE"

def sort_files_by_date(source_dir):
    if not source_dir.exists():
        print(f"Source directory '{source_dir}' does not exist.")
        return
    all_files = find_all_files_with_pathlib(source_dir)
    for file in all_files:
        file = Path(file)
        if file.is_file():
            mod_time = datetime.fromtimestamp(file.stat().st_mtime)
            target_folder = create_dest_path(mod_time)
            if target_folder == "DELETE":
                os.remove(file)
                return
            target_folder.mkdir(parents=True, exist_ok=True)

            shutil.move(str(file), target_folder / file.name)
            print(f"Moved '{file.name}' to '{target_folder}'.")

if __name__ == "__main__":
    sort_files_by_date(Path(startpath))
