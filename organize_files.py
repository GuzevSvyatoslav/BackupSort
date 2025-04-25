import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep
from typing import Generator, Optional


def validate_input_path(path: str) -> Path:
    """Validate input path and return Path object if valid."""
    path_obj = Path(path)
    if not path_obj.is_dir():
        print(f"Error: Path '{path}' does not exist or is not a directory.")
        sys.exit(1)
    return path_obj


def find_all_files(dir_path: Path) -> Generator[Path, None, None]:
    """Find all files recursively in directory excluding target folders."""
    exclude_folders = {'Yearly', 'Monthly', 'Weekly', 'Daily', '_FutureFiles'}
    for item in dir_path.rglob('*'):
        if item.is_file():
            if not any(parent.name in exclude_folders for parent in item.parents):
                yield item
        elif item.is_dir() and item.name in exclude_folders:
            yield from find_all_files(item)


def get_target_folder(file_date: datetime, current_date: datetime, base_path: Path) -> Optional[Path]:
    # Используем UTC для времени, чтобы избежать проблем с часовыми поясами
    file_date = file_date.astimezone(timezone.utc)
    current_date = current_date.astimezone(timezone.utc)
    # 1. Будущие даты
    if file_date > current_date:
        return base_path / "_FutureFiles"
    # 2. Годовые файлы (31 декабря)
    if file_date.month == 12 and file_date.day == 31:
        return base_path / "Yearly"
    # 3. Ежемесячные файлы (25-е число)
    if file_date.day == 25:
        return base_path / "Monthly"
    # 4. Ежедневные файлы (сегодня)
    if file_date.date() == current_date.date():
        return base_path / "Daily"
    # 5. Еженедельные файлы (последние 7 дней, исключая сегодня)
    if (current_date - file_date) <= timedelta(days=7) and file_date.date() != current_date.date():
        return base_path / "Weekly"
    # 6. Файлы старше 7 дней - удалить
    return None


def move_with_retries(src: Path, dst: Path, retries: int = 3, delay: float = 1.0) -> bool:
    """Attempt to move file with retries on failure."""
    for attempt in range(retries):
        try:
            shutil.move(str(src), str(dst))
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1} failed to move file '{src}' to '{dst}': {str(e)}")
            if attempt < retries - 1:
                sleep(delay)
    return False


def recheck_folders(base_path: Path, current_date: datetime):
    """Recheck Daily and Weekly folders and move files back to the main directory if necessary."""
    for folder_name in ['Daily', 'Weekly']:
        folder_path = base_path / folder_name
        if folder_path.exists():
            for file in folder_path.rglob('*'):
                if file.is_file():
                    mod_time = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
                    target_folder = get_target_folder(mod_time, current_date, base_path)
                    if target_folder != folder_path:
                        if target_folder is None:
                            print(f"Deleting file: {file}")
                            file.unlink()
                        else:
                            target_folder.mkdir(parents=True, exist_ok=True)
                            dest_path = target_folder / file.name
                            if dest_path.exists():
                                existing_mod_time = datetime.fromtimestamp(dest_path.stat().st_mtime, tz=timezone.utc)
                                if mod_time > existing_mod_time:
                                    dest_path.unlink()
                                    success = move_with_retries(file, dest_path)
                                    if success:
                                        print(f"Replaced '{file.name}' in '{target_folder}' with newer version")
                                    else:
                                        print(f"Failed to replace '{file.name}' in '{target_folder}'")
                                elif mod_time == existing_mod_time:
                                    new_name = f"{file.stem}_duplicate{file.suffix}"
                                    dest_path = target_folder / new_name
                                    success = move_with_retries(file, dest_path)
                                    if success:
                                        print(f"Moved duplicate '{file.name}' to '{dest_path}'")
                                    else:
                                        print(f"Failed to move duplicate '{file.name}' to '{dest_path}'")
                                else:
                                    file.unlink()
                                    print(f"Removed older version of '{file.name}' in '{target_folder}'")
                            else:
                                success = move_with_retries(file, dest_path)
                                if success:
                                    print(f"Moved '{file.name}' to '{target_folder}'")
                                else:
                                    print(f"Failed to move '{file.name}' to '{target_folder}'")


def organize_files(source_dir: Path) -> None:
    """Organize files in source directory by date, keeping only latest versions."""
    current_date = datetime.now(timezone.utc)
    recheck_folders(source_dir, current_date)
    for file in find_all_files(source_dir):
        try:
            mod_time = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
            target_folder = get_target_folder(mod_time, current_date, source_dir)
            if target_folder is None:
                print(f"Deleting file: {file}")
                file.unlink()
                continue
            target_folder.mkdir(parents=True, exist_ok=True)
            dest_path = target_folder / file.name
            # Обработка дубликатов
            if dest_path.exists():
                existing_mod_time = datetime.fromtimestamp(dest_path.stat().st_mtime, tz=timezone.utc)
                if mod_time > existing_mod_time:
                    # Заменяем старую версию
                    dest_path.unlink()
                    success = move_with_retries(file, dest_path)
                    if success:
                        print(f"Replaced '{file.name}' in '{target_folder}' with newer version")
                    else:
                        print(f"Failed to replace '{file.name}' in '{target_folder}'")
                elif mod_time == existing_mod_time:
                    # Если время модификации совпадает, добавляем уникальный суффикс
                    new_name = f"{file.stem}_duplicate{file.suffix}"
                    dest_path = target_folder / new_name
                    success = move_with_retries(file, dest_path)
                    if success:
                        print(f"Moved duplicate '{file.name}' to '{dest_path}'")
                    else:
                        print(f"Failed to move duplicate '{file.name}' to '{dest_path}'")
                else:
                    # Удаляем текущий файл (версия старше)
                    file.unlink()
                    print(f"Removed older version of '{file.name}' in '{target_folder}'")
            else:
                # Нет дубликата - просто перемещаем
                success = move_with_retries(file, dest_path)
                if success:
                    print(f"Moved '{file.name}' to '{target_folder}'")
                else:
                    print(f"Failed to move '{file.name}' to '{target_folder}'")
        except PermissionError as e:
            print(f"Permission denied processing file {file}: {str(e)}")
        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python organize_files.py <directory_path>")
        sys.exit(1)
    start_path = validate_input_path(sys.argv[1])
    organize_files(start_path)
