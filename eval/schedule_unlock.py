import json
import os
import time
from datetime import datetime, timedelta
import schedule


def load_json(file_path):
    """
    Safely read a JSON file.
    
    Parameters:
        file_path (str): Path to the JSON file
        
    Returns:
        dict: Parsed JSON data or None if an error occurs
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def save_json(file_path, data):
    """
    Safely write data to a JSON file.
    
    Parameters:
        file_path (str): Path to save the JSON file
        data (dict): Data to be saved
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return False


def unlock_if_needed(data, timeout_duration):
    """
    Check if a file needs to be unlocked based on its lock time.
    
    Parameters:
        data (dict): Dictionary containing the lock information
        
    Returns:
        tuple: A tuple containing updated data and a boolean indicating whether it was unlocked
    """
    now = datetime.now()
    flag = False
    
    lock_time_str = data.get('lock_time', '')
    annotation_completed = data.get('annotation_completed', '')

    if lock_time_str and annotation_completed == "No":
        try:
            lock_time = datetime.strptime(lock_time_str, '%Y-%m-%d %H:%M:%S')
            if now > lock_time + timeout_duration:
                print(f"Unlocking {data['image_name']}")
                data['lock_time'] = ""
                data['image_status'] = "unlocked"
                flag = True
        except ValueError as e:
            print(f"Invalid date format in {data.get('image_name', 'unknown')}: {lock_time_str}, {e}")

    return data, flag


def unlock_stale_locks(json_folder_path, timeout_duration):
    """
    Scan through all JSON files in the specified folder and automatically unlock files that have been locked for over 15 minutes.
    
    Parameters:
        json_folder_path (str): The path to the folder containing JSON files
    """
    if not os.path.exists(json_folder_path):
        print(f"Folder does not exist: {json_folder_path}")
        return

    file_names = [f for f in os.listdir(json_folder_path) if f.endswith('.json')]
    if not file_names:
        # print(f"No JSON files found in {json_folder_path}")
        return

    for json_name in file_names:
        json_file_path = os.path.join(json_folder_path, json_name)
        try:
            data = load_json(json_file_path)
            if data is None:
                continue
            
            updated_data, was_unlocked = unlock_if_needed(data, timeout_duration)
            if was_unlocked:
                save_json(json_file_path, updated_data)
                print(f"Updated and saved: {json_name}")
        except Exception as e:
            print(f"Failed to process {json_name}: {e}")


# -----------------------------
# Run as scheduled job
# -----------------------------

def start_unlocker_job(folder_path, timeout_minutes=15, interval_seconds=10):
    """
    Start a scheduled job to periodically check and unlock stale JSON files.
    
    Parameters:
        interval_seconds (int): Interval between checks in seconds
        folder_path (str): Folder path containing JSON files
        timeout_minutes (int): Timeout duration in minutes after which the lock is considered stale
    """
    timeout_duration = timedelta(minutes=timeout_minutes)
    print(f"Starting unlocker job every {interval_seconds} seconds for folder: {folder_path} with timeout: {timeout_minutes} minutes")
    schedule.every(interval_seconds).seconds.do(unlock_stale_locks, json_folder_path=folder_path, timeout_duration=timeout_duration)

    while True:
        schedule.run_pending()
        time.sleep(1)