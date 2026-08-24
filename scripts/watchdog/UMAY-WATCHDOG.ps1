 = "Continue"

 = "C:\UMAY 9"
 = Join-Path  "scripts\watchdog\watchdog_analyzer.py"

# Load .env variables
 = Join-Path  ".env"
if (Test-Path ) {
    Get-Content  | ForEach-Object {
         = C:\UMAY 9.Trim()
        if ( -and -not .StartsWith("#") -and .Contains("=")) {
             =  -split "=", 2
             = [0].Trim()
             = [1].Trim()
            if ( -and -not [Environment]::GetEnvironmentVariable()) {
                [Environment]::SetEnvironmentVariable(, , "Process")
            }
        }
    }
}

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
:PYTHONIOENCODING = "utf-8"

# Run the Python analyzer
python  2>&1

if ( -ne 0) {
    Write-Warning "Watchdog analyzer exited with code "
}
