import os
import sys
import time
import subprocess
import datetime

def log(message):
    """Append a message with a timestamp to the updater log file located in the same folder as the executable."""
    exe_dir = os.path.dirname(sys.executable)
    log_file = os.path.join(exe_dir, "updater_log.txt")
    timestamp = datetime.datetime.now().isoformat()
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} - {message}\n")
    except Exception as e:
        print(f"Failed to write to log file: {e}")
    print(message)

def main():
    # Expect two arguments:
    # 1. The path to the current (old) executable.
    # 2. The path to the new executable (downloaded update).
    if len(sys.argv) < 3:
        log("Usage: updater.exe <current_exe_path> <new_exe_path>")
        sys.exit(1)
        
    current_exe = sys.argv[1]
    new_exe = sys.argv[2]

    log("Updater started.")
    log(f"Current executable: {current_exe}")
    log(f"New executable: {new_exe}")

    log("Waiting for the main application to exit...")
    time.sleep(5)  # Wait to ensure the main app has fully closed

    # Create a temporary batch file to perform the update.
    exe_dir = os.path.dirname(sys.executable)
    bat_file = os.path.join(exe_dir, "update.bat")
    try:
        with open(bat_file, "w", encoding="utf-8") as f:
            f.write(f"""@echo off
REM Wait for a few seconds to ensure the old process is completely closed.
ping 127.0.0.1 -n 5 > nul
REM Copy the new executable over the current one.
copy /Y "{new_exe}" "{current_exe}"
IF ERRORLEVEL 1 (
    echo Update failed during file copy.
    exit /b 1
)
REM Launch the updated executable.
start "" "{current_exe}"
REM Delete this batch file.
del "%~f0"
""")
        log(f"Batch file created at: {bat_file}")
    except Exception as e:
        log(f"Error writing batch file: {e}")
        sys.exit(1)

    # Launch the batch file.
    try:
        log("Launching updater batch file...")
        subprocess.Popen(["cmd", "/c", bat_file], shell=True)
        log("Updater batch file launched successfully. New version should now be starting.")
    except Exception as e:
        log(f"Failed to launch updater batch file: {e}")
        sys.exit(1)

    log("Updater is exiting.")
    sys.exit(0)

if __name__ == "__main__":
    main()
