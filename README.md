# WCP Pipeline Script
This script is designed to automate the process of downloading an application from Workday's App Hub.  It facilitates source code management when not using an IDE such as Intellij.

## Steps Performed by the Script
1. Authenticate to App Hub using `auth:login` with WDCLI.
3. Lookup the Application Id for an application using the Application's Reference Id.
4. Download the application's source archive (ZIP file) using the Application Id.
5. Rename the source archive by date/time and place the file in an archive directory.
6. Delete any old files in the src directory.
7. Extract the downloaded files to the src directory.
8. Rename the application metadata file and site metadata file (.amd and .smd) for convenient comparison to versions of the application that may have a different reference id.
9. Convert .orchestration and .suborchestration files using pretty-print for improved line comparisons.

It is recommended for the src directory to be used for source code management.  The process has been tested with GitHub where the src directory is the location of the local repository.

## Script Installation
1. Install WDCLI using the standard installation for your os.  Note that this script has been primarily tested on Windows.  
[https://developer.workday.com/downloads](https://developer.workday.com/downloads)
2. Place the file, wdcli_pipeline.py, in a dedicated application directory (e.g. `C:\wdcli_pipeline`).
3. Follow the steps below for any application that uses this script.

## New Application Installation
1. Create an application directory that will hold your src and archive directories.
2. For Windows users, place the file, wdcli_pipeline.cmd, in your application directory.
3. Update wdcli_pipeline.cmd and enter the Application's Reference Id in APP_REFERENCE_ID.
4. If you are not using Windows, you can create a similar command script or enter the commands on the command line.
5. Windows users can double-click the file, wcp_app_script.cmd, to execute the commands.
6. You can also run the script from the command line:

`"{wdcli pipeline directory}\wdcli_pipeline.py" "{application reference id}" "{current application directory}"`

Example:  `"C:\Program Files\Workday\wdcli_pipeline\wdcli_pipeline.py" "positionmanagement_xzkyht" "C:\Workday_Extend\positionmanagement_xzkyht"`

   
