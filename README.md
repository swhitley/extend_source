# Extend Source Utility

This script automates the process of downloading an application from Workday's App Hub and prepares the files for source code management outside of dedicated IDEs.

## Pipeline Operations

1. **Auto-Detection:** Detects the Application Reference ID by parsing the local `/src/appManifest.json` file.
2. **Smart Download & Auth:** Attempts to download the source archive using WDCLI. If the session has expired, it automatically halts, prompts `wdcli auth login` (with a 120-second timeout protection for automated environments), and retries the download.
3. **Directory Cleanup:** Clears the existing `src` directory while safely preserving version control tracking (`.git`).
4. **Extraction:** Unzips the newly downloaded application files into the `src` directory.
5. **Metadata Normalization:** Renames `.amd` and `.smd` files with a static company code placeholder (`xxxxxx`) to ensure clean, consistent Git diffs regardless of the source tenant.
6. **JSON Formatting:** Pretty-prints `.orchestrate`, `.orchestration`, and `.suborchestration` files for improved line-by-line comparison.
7. **Archiving:** Appends a timestamp to the downloaded source ZIP and stores it in the `archive` directory.
8. **Automated Version Control (Optional):** Automatically stages and commits the updated source files to Git if requested.

## Installation

1. Install the Workday CLI (WDCLI) for your operating system: [https://developer.workday.com/downloads](https://developer.workday.com/downloads). Ensure it is added to your system PATH.
2. Ensure Python 3.x is installed on your machine.
3. Save `extend_source.py` to a dedicated central directory (e.g., `C:\extend_utilities`).

## Usage

The script is fully self-contained and relies on standard command-line arguments to dictate behavior. Navigate to your local application directory in your terminal and execute the script using Python.

### Standard Execution (Auto-Detect)

If your application directory already contains a `/src/appManifest.json` file, the script will automatically detect the Application Reference ID and assume the current working directory is the target.

```shell
py "C:\extend_utilities\extend_source.py"

```

### Advanced Execution (Targeted with Git Commit)

You can explicitly define the target directory, override the auto-detected Reference ID, and trigger an automated Git commit upon completion.

```shell
py "C:\extend_utilities\extend_source.py" --app-ref-id "security_analyzer_kkvxdf" --app-dir "C:\Workday_Extend\security_analyzer" --commit

```

### Available Arguments

* `--app-dir`: The target application directory. Defaults to the current working directory.
* `--app-ref-id`: The Application Reference ID. If omitted, the script attempts to parse it from `/src/appManifest.json`.
* `--commit`: An optional flag that executes `git add .` and `git commit -m "Automated app sync"` immediately after the directory processing is complete.
