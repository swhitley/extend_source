import os
import shutil
import json
import logging
import glob
import zipfile
import datetime
import sys
import re
import stat
 
# --- Constants ---
ZIP_EXTENSION = "*.zip"
AMD_SMD_EXTENSIONS = ("./presentation/*.amd", "./presentation/*.smd")
# Expanded to catch .orchestrate, .orchestration, and .suborchestration based on your notes
ORCHESTRATE_EXTENSIONS = ("./orchestration/*.orchestrate", "./orchestration/*.orchestration", "./orchestration/*.suborchestration")
ARCHIVE_DIRECTORY = "archive"
SRC_DIRECTORY = "src"
 
# --- Helper Functions ---
 
def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
 
def validate_directory(directory, error_message):
    if not os.path.exists(directory):
        raise FileNotFoundError(error_message)
    if not os.path.isdir(directory):
        raise NotADirectoryError(error_message)
 
def get_latest_unprocessed_zip(directory):
    """Finds the most recent zip file that doesn't have a processing timestamp."""
    search_pattern = os.path.join(directory, ZIP_EXTENSION)
    matching_files = glob.glob(search_pattern)
   
    valid_files = []
    # Regex to identify files already renamed with _YYYYMMDD_HHMMSS
    archive_pattern = re.compile(r"_\d{8}_\d{6}\.zip$")
   
    for file in matching_files:
        if not archive_pattern.search(file):
            valid_files.append(file)
           
    if not valid_files:
        return None
       
    return max(valid_files, key=os.path.getmtime)
 
def handle_remove_readonly(func, path, exc_info):
    """Error handler for shutil.rmtree to remove read-only attributes."""
    os.chmod(path, stat.S_IWRITE)
    func(path)
 
def delete_directory_contents(directory):
    """Deletes all files and folders within a directory, but not the directory itself or .git."""
    validate_directory(directory, f"App directory '{directory}' not found.")
    try:
        for filename in os.listdir(directory):
            if filename == ".git":
                continue
            filepath = os.path.join(directory, filename)
            try:
                if os.path.isfile(filepath) or os.path.islink(filepath):
                    try:
                        os.unlink(filepath)
                    except PermissionError:
                        # If read-only, change permission and try again
                        os.chmod(filepath, stat.S_IWRITE)
                        os.unlink(filepath)
                elif os.path.isdir(filepath):
                    # Pass the error handler to rmtree
                    shutil.rmtree(filepath, onerror=handle_remove_readonly)
            except (OSError, PermissionError) as e:
                logging.error(f"Failed to delete {filepath}. Reason: {e}")
        logging.info(f"Contents of {directory} deleted successfully.")
    except Exception as e:
        logging.error(f"An error occurred during deletion: {e}")
        raise
 
def extract_zip(zip_filepath, extract_directory):
    """Extracts a zip file to a specified directory."""
    validate_directory(extract_directory, f"Extraction directory '{extract_directory}' not found.")
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(extract_directory)
        logging.info(f"Successfully extracted '{zip_filepath}' to '{extract_directory}'")
    except zipfile.BadZipFile:
        raise Exception(f"'{zip_filepath}' is not a valid zip file.")
    except Exception as e:
        raise Exception(f"An error occurred during zip extraction: {e}")
 
def rename_file(filepath, new_filepath):
    """Renames a file, handling potential errors."""
    try:
        os.rename(filepath, new_filepath)
        logging.info(f"Renamed '{filepath}' to '{new_filepath}'.")
    except FileExistsError:
        raise Exception(f"File already exists: {new_filepath}")
    except FileNotFoundError:
        raise Exception(f"File not found: {filepath}")
    except Exception as e:
        raise Exception(f"Failed to rename '{filepath}': {e}")
 
def rename_amd_smd_files(directory, extensions=AMD_SMD_EXTENSIONS):
    """Renames .amd and .smd files in a directory."""
    def generate_new_filename(base_name, file_extension):
        metadata = 'metadata'
        if file_extension == '.amd':
            metadata = 'application_metadata'
        if file_extension == '.smd':
            metadata = 'site_metadata'
        company_code = 'xxxxxx'
        parts = base_name.rsplit('_', 1)
        if len(parts) != 2:
            raise ValueError(f"Filename '{base_name}' does not contain an underscore to split on.")
        return f"{metadata}_{company_code}{file_extension}"
 
    for extension_pattern in extensions:
        pattern = os.path.join(directory, extension_pattern)
        matching_files = glob.glob(pattern)
 
        for filepath in matching_files:
            try:
                directory_path, filename = os.path.split(filepath)
                base_name, file_extension = os.path.splitext(filename)
                new_filename = generate_new_filename(base_name, file_extension)
                new_filepath = os.path.join(directory_path, new_filename)
                rename_file(filepath, new_filepath)
            except Exception as e:
                logging.error(f"Failed to rename '{filepath}': {e}")
 
def pretty_print_orchestrations(directory, extensions=ORCHESTRATE_EXTENSIONS):
    """Pretty Prints Orchestration Files"""
    for extension_pattern in extensions:
        pattern = os.path.join(directory, extension_pattern)
        matching_files = glob.glob(pattern)
 
        for filepath in matching_files:
            try:
                # Read the file content
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
               
                # Try to parse and pretty-print as JSON
                try:
                    parsed_json = json.loads(content)
                    pretty_content = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                   
                    # Write the pretty-printed content back to the same file
                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write(pretty_content)
                   
                    logging.info(f"Pretty-printed orchestration file: {filepath}")
                   
                except json.JSONDecodeError as json_error:
                    logging.warning(f"File '{filepath}' is not valid JSON, skipping pretty-print: {json_error}")
                   
            except Exception as e:
                logging.error(f"Failed to pretty-print '{filepath}': {e}")               
 
def archive_zip_file(filepath):
    """Appends a timestamp to the processed zip file."""
    dt_string = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name, file_extension = os.path.splitext(filepath)
    new_filepath = f"{base_name}_{dt_string}{file_extension}"
 
    rename_file(filepath, new_filepath)
    return new_filepath
 
def process_app_directory(app_directory):
    """
    Coordinates the directory preparation, extraction, and formatting.
    """
    setup_logging()
 
    try:
        validate_directory(app_directory, f"App directory '{app_directory}' not found.")
        src_directory = os.path.join(app_directory, SRC_DIRECTORY)
        archive_directory = os.path.join(app_directory, ARCHIVE_DIRECTORY)       
        
        # Ensure directories exist
        os.makedirs(src_directory, exist_ok=True)
        os.makedirs(archive_directory, exist_ok=True)
 
        # Step 1: Locate latest zip file in ./archive (ignoring files already timestamped)
        logging.info("Locating the latest unprocessed zip file.")
        latest_zip = get_latest_unprocessed_zip(archive_directory)
 
        if not latest_zip:
            logging.info("No new zip files found to process.")
            return
 
        # Step 2: Delete old files in src directory (except .git)
        logging.info(f"Deleting old files in {src_directory}.")
        delete_directory_contents(src_directory)
 
        # Step 3: Unzip the latest zip file into the ./src folder
        logging.info(f"Unzipping '{latest_zip}' to '{src_directory}'.")
        extract_zip(latest_zip, src_directory)
 
        # Step 4: Rename and modify the AMD and SMD files
        logging.info("Renaming AMD and SMD files.")
        rename_amd_smd_files(src_directory)
       
        # Step 5: Pretty print and update .orchestrate files in place
        logging.info("Pretty printing orchestration files.")
        pretty_print_orchestrations(src_directory)
       
        # Step 6: Rename the .zip file in ./archive
        logging.info("Archiving the processed zip file.")
        archive_zip_file(latest_zip)
 
        logging.info("Processing complete.") 
 
    except FileNotFoundError as e:
        logging.error(f"Required tool or directory not found: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
 
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python wdcli_pipeline.py <app_directory>")
        sys.exit(1)
 
    app_dir = sys.argv[1]
    process_app_directory(app_dir)
