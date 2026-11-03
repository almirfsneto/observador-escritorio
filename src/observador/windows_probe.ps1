# Original laboratory bridge. Never request Name, ValuePattern, TextPattern,
# window titles, clipboard, or keystrokes. Unknown/access-denied => no event.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
try {
    $allowed = @([Console]::In.ReadToEnd() | ConvertFrom-Json)
    if ($allowed.Count -eq 0) { 'null'; exit 0 }
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class ObservadorForeground {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
'@
    $window = [ObservadorForeground]::GetForegroundWindow()
    if ($window -eq [IntPtr]::Zero) { 'null'; exit 0 }
    [uint32]$foregroundPid = 0
    $null = [ObservadorForeground]::GetWindowThreadProcessId($window, [ref]$foregroundPid)
    $process = Get-Process -Id $foregroundPid
    $path = $process.Path
    $index = -1
    for ($i = 0; $i -lt $allowed.Count; $i++) {
        if ([string]::Equals($path, $allowed[$i], [StringComparison]::OrdinalIgnoreCase)) {
            $index = $i; break
        }
    }
    if ($index -lt 0) { 'null'; exit 0 }
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    $element = [System.Windows.Automation.AutomationElement]::FocusedElement
    if ($null -eq $element) { 'null'; exit 0 }
    $owner = $element.GetCurrentPropertyValue([System.Windows.Automation.AutomationElement]::ProcessIdProperty)
    if ($owner -ne $foregroundPid) { 'null'; exit 0 }
    $password = $element.GetCurrentPropertyValue([System.Windows.Automation.AutomationElement]::IsPasswordProperty)
    if ($password -isnot [bool] -or $password) { 'null'; exit 0 }
    $role = $element.GetCurrentPropertyValue([System.Windows.Automation.AutomationElement]::ControlTypeProperty)
    # Discard a result if focus changed during the query.
    if ([ObservadorForeground]::GetForegroundWindow() -ne $window) { 'null'; exit 0 }
    @{index=$index; role=$role.Id; password=$false} | ConvertTo-Json -Compress
} catch {
    # Never expose native exception text, which may contain user data.
    'null'
    exit 1
}
