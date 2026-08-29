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
import subprocess
import argparse

# --- Constants ---
ZIP_EXTENSION = "*.zip"
AMD_SMD_EXTENSIONS = ("./presentation/*.amd", "./presentation/*.smd")
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

def get_app_info(app_dir):
    """Auto-detects the application Reference ID by parsing extend.json or app.json."""
    src_dir = os.path.join(app_dir, SRC_DIRECTORY)
    search_paths = [app_dir, src_dir]
    
    for directory in search_paths:
        if not os.path.exists(directory):
            continue
            
        for filename in ['extend.json', 'app.json']:
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        app_ref_id = data.get('referenceId') or data.get('id')
                        if app_ref_id:
                            logging.info(f"Auto-detected App Reference ID '{app_ref_id}' from {filepath}")
                            return app_ref_id
                except Exception as e:
                    logging.warning(f"Could not parse {filepath}: {e}")
    return None

def get_latest_unprocessed_zip(directory):
    """Finds the most recent zip file that doesn't have a processing timestamp."""
    search_pattern = os.path.join(directory, ZIP_EXTENSION)
    matching_files = glob.glob(search_pattern)
    
    valid_files = []
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
                        os.chmod(filepath, stat.S_IWRITE)
                        os.unlink(filepath)
                elif os.path.isdir(filepath):
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
            
        # Hardcoded to 'xxxxxx' intentionally to normalize git diffs regardless of source tenant code
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
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                try:
                    parsed_json = json.loads(content)
                    pretty_content = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                    
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

def download_app_from_wdcli(app_ref_id, archive_dir):
    """Executes Workday CLI commands to download the app package."""
    cmd = [
        "wdcli", "app", "download", app_ref_id,
        "-d", archive_dir,
        "--latest-version", "--overwrite", "--as-zip"
    ]
    
    use_shell = os.name == 'nt'

    logging.info(f"Downloading app '{app_ref_id}' to '{archive_dir}'...")
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, shell=use_shell)
        logging.info("CLI download successful.")
    except subprocess.CalledProcessError as e:
        logging.warning(f"Download failed. The CLI session may have expired. Output: {e.stderr.strip()}")
        logging.info("Attempting 'wdcli auth login' with 120-second timeout...")
        try:
            # 120-second timeout added for headless CI/CD environment protection
            subprocess.run(["wdcli", "auth", "login"], check=True, shell=use_shell, timeout=120)
            logging.info("Authentication complete. Retrying download...")
            subprocess.run(cmd, check=True, capture_output=True, text=True, shell=use_shell)
            logging.info("CLI download successful on retry.")
        except subprocess.TimeoutExpired:
            raise Exception("Authentication timed out. If running in a headless environment, ensure you are pre-authenticated.")
        except subprocess.CalledProcessError:
            raise Exception("Authentication or retry failed. Check Workday CLI configuration.")
    except FileNotFoundError:
        raise Exception("wdcli executable not found. Ensure it is installed and added to the system PATH.")

def execute_git_commit(app_dir):
    """Executes git add and git commit for automated version control integration."""
    logging.info("Executing Git version control commands...")
    try:
        subprocess.run(["git", "add", "."], cwd=app_dir, check=True, capture_output=True, text=True)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=app_dir, check=True, capture_output=True, text=True)
        
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Automated app sync"], cwd=app_dir, check=True, capture_output=True, text=True)
            logging.info("Git commit successful: 'Automated app sync'")
        else:
            logging.info("Git status is clean. No changes to commit.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed. Output: {e.stderr.strip()}")
    except FileNotFoundError:
        logging.error("Git executable not found. Ensure git is installed and in your PATH.")

def process_app_directory(app_directory, app_ref_id, auto_commit):
    """
    Coordinates the directory preparation, extraction, and formatting.
    """
    setup_logging()

    try:
        if not os.path.exists(app_directory):
            os.makedirs(app_directory, exist_ok=True)
            
        # Target Application Abstraction (Auto-detect if no argument provided)
        if not app_ref_id:
            app_ref_id = get_app_info(app_directory)
            if not app_ref_id:
                raise ValueError("App Reference ID could not be auto-detected from extend.json/app.json and was not provided as an argument.")

        src_directory = os.path.join(app_directory, SRC_DIRECTORY)
        archive_directory = os.path.join(app_directory, ARCHIVE_DIRECTORY)        
        
        os.makedirs(src_directory, exist_ok=True)
        os.makedirs(archive_directory, exist_ok=True)

        # Step 1: Execute Workday CLI Operations
        download_app_from_wdcli(app_ref_id, archive_directory)

        # Step 2: Locate latest zip file in ./archive (ignoring files already timestamped)
        logging.info("Locating the latest unprocessed zip file.")
        latest_zip = get_latest_unprocessed_zip(archive_directory)

        if not latest_zip:
            logging.info("No new zip files found to process.")
            return

        # Step 3: Delete old files in src directory (except .git)
        logging.info(f"Deleting old files in {src_directory}.")
        delete_directory_contents(src_directory)

        # Step 4: Unzip the latest zip file into the ./src folder
        logging.info(f"Unzipping '{latest_zip}' to '{src_directory}'.")
        extract_zip(latest_zip, src_directory)

        # Step 5: Rename and modify the AMD and SMD files
        logging.info("Renaming AMD and SMD files.")
        rename_amd_smd_files(src_directory)
        
        # Step 6: Pretty print and update .orchestrate files in place
        logging.info("Pretty printing orchestration files.")
        pretty_print_orchestrations(src_directory)
        
        # Step 7: Rename the .zip file in ./archive
        logging.info("Archiving the processed zip file.")
        archive_zip_file(latest_zip)
        
        # Step 8: Optional automated git commit loop
        if auto_commit:
            execute_git_commit(app_directory)

        logging.info("Processing complete.")  

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Workday App CLI Pipeline")
    parser.add_argument("--app-dir", default=os.getcwd(), help="Application directory (defaults to current working directory)")
    parser.add_argument("--app-ref-id", default=None, help="Application Reference ID. If omitted, the script will attempt to auto-detect it from extend.json or app.json.")
    parser.add_argument("--commit", action="store_true", help="Automatically execute 'git add .' and 'git commit' after processing.")
    args = parser.parse_args()

    try:
        process_app_directory(args.app_dir, args.app_ref_id, args.commit)
    finally:
        input("\nPress Enter to continue...")
