using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Windows.Automation;

namespace WindowsObserver;

// Laboratory-only UIA provider. No name, text, value, key or clipboard APIs.
internal sealed class Observer : IDisposable
{
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
    private readonly Process target;
    private readonly DateTime expires;
    private readonly Stopwatch lifetime = Stopwatch.StartNew();
    private readonly TimeSpan budget;
    private readonly object gate = new();
    private readonly byte[] salt = RandomNumberGenerator.GetBytes(32);
    private readonly BlockingCollection<object> output = new(512);
    private readonly AutomationFocusChangedEventHandler focusHandler;
    private readonly AutomationEventHandler invokeHandler;
    private readonly AutomationPropertyChangedEventHandler toggleHandler;
    private AutomationElement? root;
    private bool enabled;
    private long generation, sequence, dropped;
    private long focusSeen, invokeSeen, toggleSeen, excluded, errors;
    private readonly bool synthetic;

    internal Observer(Process target, DateTime expires, bool synthetic = false)
    {
        this.target = target;
        this.expires = expires;
        budget = expires - DateTime.UtcNow;
        this.synthetic = synthetic;
        focusHandler = (sender, _) => Capture(sender, "focus");
        invokeHandler = (sender, _) => Capture(sender, "invoke");
        toggleHandler = (sender, _) => Capture(sender, "toggle");
    }

    internal void Subscribe()
    {
        if (!target.WaitForInputIdle(3000)) throw new InvalidOperationException();
        target.Refresh();
        root = AutomationElement.FromHandle(target.MainWindowHandle);
        if (root is null) throw new InvalidOperationException();
        Automation.AddAutomationFocusChangedEventHandler(focusHandler);
        Automation.AddAutomationEventHandler(InvokePattern.InvokedEvent, root, TreeScope.Subtree, invokeHandler);
        Automation.AddAutomationPropertyChangedEventHandler(root, TreeScope.Subtree, toggleHandler,
            TogglePattern.ToggleStateProperty);
    }

    private bool Alive() => !target.HasExited && DateTime.UtcNow < expires && lifetime.Elapsed < budget;
    private void Send(object value) { if (!output.TryAdd(value)) Interlocked.Increment(ref dropped); }
    internal void Writer() { foreach (var item in output.GetConsumingEnumerable()) Console.WriteLine(JsonSerializer.Serialize(item)); }
    internal void Ready() => Console.WriteLine(JsonSerializer.Serialize(new {
        kind = "ready", pid = target.Id, start_ticks = target.StartTime.ToUniversalTime().Ticks }));
    internal void Health() => Send(new { kind = "health", dropped = Interlocked.Read(ref dropped), generation,
        callbacks = new { focus = Interlocked.Read(ref focusSeen), invoke = Interlocked.Read(ref invokeSeen),
            toggle = Interlocked.Read(ref toggleSeen), excluded = Interlocked.Read(ref excluded), errors = Interlocked.Read(ref errors) } });
    internal bool IsAlive() => Alive();

    internal bool Command(string line)
    {
        using var json = JsonDocument.Parse(line);
        var command = json.RootElement.GetProperty("command").GetString();
        if (command == "stop") return false;
        var token = json.RootElement.GetProperty("generation").GetInt64();
        lock (gate)
        {
            if (token <= generation || !Alive()) return false;
            enabled = false;
            generation = token;
            // A generation boundary invalidates anything still queued in either process.
            while (output.TryTake(out _)) { }
            enabled = command == "start";
            if (command != "start" && command != "pause") return false;
            Send(new { kind = "ack", generation, active = enabled });
        }
        return true;
    }

    private void Capture(object sender, string action)
    {
        try
        {
            long token;
            lock (gate) { if (!enabled || !Alive()) return; token = generation; }
            if (action == "focus") Interlocked.Increment(ref focusSeen);
            else if (action == "invoke") Interlocked.Increment(ref invokeSeen);
            else Interlocked.Increment(ref toggleSeen);
            if (sender is not AutomationElement element) return;
            // Filter the process before requesting any control properties.
            if ((int)element.GetCurrentPropertyValue(AutomationElement.ProcessIdProperty) != target.Id) {
                Interlocked.Increment(ref excluded); return;
            }
            GetWindowThreadProcessId(GetForegroundWindow(), out uint foreground);
            if (foreground != target.Id) { Interlocked.Increment(ref excluded); return; }
            var password = element.GetCurrentPropertyValue(AutomationElement.IsPasswordProperty);
            if (password is not bool secret || secret) { Interlocked.Increment(ref excluded); return; }
            var type = element.GetCurrentPropertyValue(AutomationElement.ControlTypeProperty) as ControlType;
            if (type is null) return;
            // Runtime IDs contain provider integers, not control text. Salt prevents cross-session linkage.
            var runtime = Encoding.UTF8.GetBytes(string.Join(",", element.GetRuntimeId()));
            var id = Convert.ToHexString(SHA256.HashData(salt.Concat(runtime).ToArray()))[..16].ToLowerInvariant();
            lock (gate)
            {
                if (!enabled || generation != token || !Alive()) return;
                SendEvent(action, type.Id, id);
            }
        }
        catch { Interlocked.Increment(ref errors); Interlocked.Increment(ref dropped); } // No native exception data.
    }

    private void SendEvent(string action, int role, string id) => Send(new {
        kind = "event", generation, sequence = ++sequence,
        timestamp_utc = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture), action, role, control_id = id
    });

    // Deterministic protocol/load test: no UIA registration or desktop observation.
    internal void SyntheticBurst()
    {
        if (!synthetic) throw new InvalidOperationException();
        lock (gate) { for (int i = 0; i < 2000; i++) if (enabled) SendEvent("invoke", 50000, "0000000000000001"); }
    }

    public void Dispose()
    {
        lock (gate) enabled = false;
        // OS can stall during UIA teardown. Parent has a bounded kill fallback.
        if (!synthetic) Automation.RemoveAllEventHandlers();
        output.CompleteAdding();
        target.Dispose();
    }
}

internal static class Program
{
    private static int Main(string[] args)
    {
        string stage = "invalid_config";
        Console.InputEncoding = new UTF8Encoding(false);
        Console.OutputEncoding = new UTF8Encoding(false);
        try
        {
            if (args.Length != 5) return 2;
            bool synthetic = args[0] == "--protocol-test";
            if (!synthetic && args[0] != "--laboratory") return 2;
            int pid = int.Parse(args[1], CultureInfo.InvariantCulture);
            string path = Path.GetFullPath(args[2]);
            long ticks = long.Parse(args[3], CultureInfo.InvariantCulture);
            DateTime expires = DateTime.Parse(args[4], CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind).ToUniversalTime();
            if (expires <= DateTime.UtcNow || expires > DateTime.UtcNow.AddMinutes(15)) return 2;
            var target = Process.GetProcessById(pid);
            _ = target.Handle; // Retain a handle to this process instance, not a future reused PID.
            if (!StringComparer.OrdinalIgnoreCase.Equals(target.MainModule?.FileName, path)
                || target.StartTime.ToUniversalTime().Ticks != ticks) return 2;
            if (!synthetic && Path.GetFileName(path) != "SyntheticTaskApp.exe") return 2;
            using var observer = new Observer(target, expires, synthetic);
            // A separate watchdog also bounds a stuck UIA call or teardown.
            var watchdog = Stopwatch.StartNew();
            var maximum = expires - DateTime.UtcNow;
            new Thread(() => {
                try {
                    while (watchdog.Elapsed < maximum && DateTime.UtcNow < expires && !target.HasExited)
                        Thread.Sleep(100);
                } catch (InvalidOperationException) { return; }
                Environment.Exit(0);
            }) { IsBackground = true }.Start();
            stage = "subscription_failed";
            if (!synthetic) observer.Subscribe();
            observer.Ready();
            new Thread(() => {
                try { observer.Writer(); } catch (IOException) { Environment.Exit(0); }
            }) { IsBackground = true }.Start();
            var input = new BlockingCollection<string>(16);
            new Thread(() => {
                try {
                    string? line;
                    while ((line = Console.ReadLine()) is not null)
                        if (!input.TryAdd(line)) return;
                } catch (IOException) { }
                finally { input.CompleteAdding(); }
            }) { IsBackground = true }.Start();
            stage = "backend_failure";
            var timer = Stopwatch.StartNew();
            while (observer.IsAlive())
            {
                if (input.TryTake(out string? line, 50))
                {
                    if (!observer.Command(line)) break;
                    if (synthetic) observer.SyntheticBurst();
                }
                else if (input.IsCompleted) break;
                if (timer.ElapsedMilliseconds >= 1000) { observer.Health(); timer.Restart(); }
            }
            // Exit also on stdin EOF: a crashed controller must not leave a collector.
            return 0;
        }
        catch {
            Console.WriteLine(JsonSerializer.Serialize(new { kind = "error", code = stage }));
            return 2;
        }
    }
}
