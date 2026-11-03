using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

namespace WindowsObserver;

// Opt-in diagnostic only. Process-scoped accessibility notifications, never a
// mouse/keyboard hook and never a fallback that invents UIA Invoke events.
internal static class WinEventCoverage
{
    private delegate void Callback(IntPtr hook, uint kind, IntPtr window, int objectId, int child, uint thread, uint time);
    [DllImport("user32.dll")] private static extern IntPtr SetWinEventHook(uint min, uint max, IntPtr module, Callback callback, uint pid, uint thread, uint flags);
    [DllImport("user32.dll")] private static extern bool UnhookWinEvent(IntPtr hook);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetClassName(IntPtr window, StringBuilder value, int count);
    [StructLayout(LayoutKind.Sequential)] private struct Point { public int x, y; }
    [StructLayout(LayoutKind.Sequential)] private struct Message { public IntPtr hwnd; public uint message; public UIntPtr wparam; public IntPtr lparam; public uint time; public Point point; public uint extra; }
    [DllImport("user32.dll")] private static extern bool PeekMessage(out Message message, IntPtr window, uint min, uint max, uint remove);
    [DllImport("user32.dll")] private static extern bool TranslateMessage(ref Message message);
    [DllImport("user32.dll")] private static extern IntPtr DispatchMessage(ref Message message);

    internal static int Run(Process target, DateTime expires)
    {
        int stop = 0, invoked = 0, stateChanges = 0, excluded = 0, dropped = 0;
        uint deliveryPeak = 0;
        var controls = new HashSet<IntPtr>(); // Only aggregate cardinality leaves this process.
        var elapsed = Stopwatch.StartNew();
        Callback callback = (_, kind, window, objectId, child, _, time) => {
            if (invoked + stateChanges >= 10000) { dropped++; return; }
            GetWindowThreadProcessId(window, out uint pid);
            GetWindowThreadProcessId(GetForegroundWindow(), out uint foreground);
            if (pid != target.Id || foreground != target.Id || child != 0 || objectId != -4) { excluded++; return; }
            var name = new StringBuilder(128);
            GetClassName(window, name, name.Capacity); // Class only, never caption/control text.
            string type = name.ToString();
            if (type != "Button" && !type.StartsWith("WindowsForms10.BUTTON.", StringComparison.Ordinal)) { excluded++; return; }
            if (!controls.Contains(window) && controls.Count >= 128) { dropped++; return; }
            controls.Add(window);
            deliveryPeak = Math.Max(deliveryPeak, unchecked((uint)Environment.TickCount - time));
            if (kind == 0x8013) invoked++;
            else stateChanges++;
        };
        var action = SetWinEventHook(0x8013, 0x8013, IntPtr.Zero, callback, (uint)target.Id, 0, 2);
        var state = SetWinEventHook(0x800A, 0x800A, IntPtr.Zero, callback, (uint)target.Id, 0, 2);
        if (action == IntPtr.Zero || state == IntPtr.Zero) {
            if (action != IntPtr.Zero) UnhookWinEvent(action);
            if (state != IntPtr.Zero) UnhookWinEvent(state);
            return 3;
        }
        try {
            Console.WriteLine("{\"kind\":\"coverage_ready\"}");
            new Thread(() => { Console.ReadLine(); Interlocked.Exchange(ref stop, 1); }) { IsBackground=true }.Start();
            while (Volatile.Read(ref stop) == 0 && !target.HasExited && DateTime.UtcNow < expires && elapsed.Elapsed < TimeSpan.FromSeconds(20)) {
                while (PeekMessage(out var message, IntPtr.Zero, 0, 0, 1)) {
                    TranslateMessage(ref message);
                    DispatchMessage(ref message);
                }
                Thread.Sleep(5);
            }
        } finally {
            UnhookWinEvent(action);
            UnhookWinEvent(state);
            GC.KeepAlive(callback);
        }
        Console.WriteLine(JsonSerializer.Serialize(new {
            kind="coverage_result", invoked, state_changes=stateChanges, distinct_button_handles=controls.Count,
            excluded, dropped, elapsed_ms=elapsed.ElapsedMilliseconds,
            callback_delivery_peak_ms=deliveryPeak,
            probe_cpu_ms=Process.GetCurrentProcess().TotalProcessorTime.TotalMilliseconds,
            probe_peak_working_set_bytes=Process.GetCurrentProcess().PeakWorkingSet64,
            interpretation="accessibility_notifications_only_not_user_intent"
        }));
        return 0;
    }
}
