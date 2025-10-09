# gui/advanced_config_editor/versioning.py
"""
Versioning and backup functionality for the advanced configuration editor.
"""
import os
import shutil
from datetime import datetime

def backup_file(filepath, backup_folder="config/backups"):
    """
    Create a backup of a file before modifying it.
    
    Args:
        filepath (str): Path to the file to backup
        backup_folder (str): Directory to store backups
        
    Returns:
        str: Path to the backup file
    """
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.basename(filepath)
    backup_path = os.path.join(backup_folder, f"{base}.{timestamp}.bak")
    try:
        shutil.copy2(filepath, backup_path)
    except Exception:
        pass
    return backup_path