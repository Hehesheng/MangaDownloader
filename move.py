import os
import shutil
import glob


def move_zip_files_to_folders():
    zip_files = glob.glob('*.zip')

    for zip_file in zip_files:
        # Remove .zip extension to get directory name
        directory = os.path.splitext(zip_file)[0]
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        # Move the zip file into the new directory
        shutil.move(zip_file, directory)


move_zip_files_to_folders()
