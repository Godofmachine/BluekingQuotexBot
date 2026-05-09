# Antigravity Windows Watchdog & Keep-Alive Script (V3 - Single Window)
# ------------------------------------------------------------------

# Prevent the computer from sleeping
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

Write-Host "------------------------------------------" -ForegroundColor Cyan
Write-Host "🚀 Watchdog V3 Active (Single Window Mode)" -ForegroundColor Cyan
Write-Host "------------------------------------------" -ForegroundColor Cyan

$FailCount = 0

while ($true) {
    Write-Host "$(Get-Date): [SYSTEM] Starting Antigravity Trading Engine..." -ForegroundColor Green
    
    # Run the bot directly in THIS window (not a new one)
    python main.py
    
    # When the bot closes or crashes, the script continues here
    Write-Host "$(Get-Date): [SYSTEM] Bot has closed or crashed." -ForegroundColor Yellow
    
    if ($FailCount -lt 5) {
        Write-Host "Restarting in 5 seconds..." -ForegroundColor Cyan
        Start-Sleep -Seconds 5
        $FailCount++
    } else {
        Write-Host "⚠️ Bot has crashed too many times. Waiting 5 minutes to avoid spam." -ForegroundColor Red
        Start-Sleep -Seconds 300
        $FailCount = 0
    }
}
