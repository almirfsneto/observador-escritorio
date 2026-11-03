param([int]$TargetPid, [long]$StartTicks, [string]$TargetPath, [string]$Phase = 'burst')
$ErrorActionPreference = 'Stop'
try {
    $target = Get-Process -Id $TargetPid
    if ($target.StartTime.ToUniversalTime().Ticks -ne $StartTicks -or
        $target.Path -ne $TargetPath -or [IO.Path]::GetFileName($target.Path) -notin @('SyntheticTaskApp.exe', 'SyntheticWpfTaskApp.exe')) {
        throw 'Wrong fixture'
    }
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class FixtureDesktop {
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr handle);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
'@
    $startup = [Diagnostics.Stopwatch]::StartNew()
    do {
        $target.Refresh()
        $handle = $target.MainWindowHandle
        if ($handle -ne [IntPtr]::Zero) { break }
        Start-Sleep -Milliseconds 50
    } while ($startup.ElapsedMilliseconds -lt 8000 -and -not $target.HasExited)
    $null = [FixtureDesktop]::SetForegroundWindow($handle)
    Start-Sleep -Milliseconds 200
    if ($handle -eq [IntPtr]::Zero -or [FixtureDesktop]::GetForegroundWindow() -ne $handle) {
        '{"status":"blocked","reason":"foreground_unavailable"}'
        exit 0
    }
    if ($Phase -eq 'probe') { '{"status":"ok"}'; exit 0 }
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
    $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                        [System.Windows.Automation.Condition]::TrueCondition)
    $buttons = @()
    $password = $null
    foreach ($element in $all) {
        if ($element.Current.IsPassword) { $password = $element; continue }
        # Select only the two known fixture buttons, never caption/minimize/close buttons.
        if ($element.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button -and
            $element.Current.AutomationId -in @('synthetic_save', 'synthetic_review')) {
            $buttons += $element
        }
    }
    if ($Phase -eq 'password') {
        if ($null -eq $password) { throw 'Missing synthetic password control' }
        $password.SetFocus()
    } elseif ($Phase -eq 'burst') {
        if ($buttons.Count -lt 2) { throw 'Missing synthetic buttons' }
        for ($i=0; $i -lt 15; $i++) {
            foreach ($button in $buttons[0..1]) {
                $button.SetFocus()
                $pattern = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
                $pattern.Invoke()
                Start-Sleep -Milliseconds 20
            }
        }
    } else { throw 'Invalid test phase' }
    '{"status":"ok"}'
} catch {
    '{"status":"error","reason":"synthetic_exercise_failed"}'
    exit 1
}
