# Antigravity Windows Watchdog & Keep-Alive Script (V2 - Anti-Spam)
# ------------------------------------------------------------------

$BotScript = "main.py"
$CheckInterval = 30 
$FailCount = 0

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class SleepUtil {
    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
    public const uint ES_CONTINUOUS = 0x80000000;
    public const uint ES_SYSTEM_REQUIRED = 0x00000001;
}
"@
[SleepUtil]::SetThreadExecutionState([SleepUtil]::ES_CONTINUOUS -bor [SleepUtil]::ES_SYSTEM_REQUIRED)

Write-Host "🚀 Watchdog V2 Active" -ForegroundColor Cyan

while ($true) {
    $process = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*$BotScript*" }

    if (-not $process) {
        if ($FailCount -lt 5) {
            Write-Host "$(Get-Date): Bot closed. Restarting..." -ForegroundColor Yellow
            Start-Process python -ArgumentList "main.py" -WorkingDirectory $PSScriptRoot
            $FailCount++
        } else {
            Write-Host "⚠️ Bot has crashed too many times. Waiting 5 minutes before trying again to avoid spam." -ForegroundColor Red
            Start-Sleep -Seconds 300
            $FailCount = 0
        }
    } else {
        $FailCount = 0 # Reset counter if bot is running successfully
    }

    Start-Sleep -Seconds $CheckInterval
}
