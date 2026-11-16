"""The settings file must survive an interrupted save, and say so when it does not.

`SettingsManager.Save` used to call `File.WriteAllText` on the live settings file: that truncates it
and then streams the new bytes in, so being killed, a full disk or a power cut in that window leaves
truncated JSON. `Load` caught the parse failure and returned `new AppSettings()`, i.e. all defaults,
with no message and no log line - then the next save wrote those defaults over the real file. The
player's install path, GPU choice and controls were gone.

There is no .NET runtime on the machine that runs this test, so this does not execute the C#. It does
two things a regex-only check cannot:

- reads `SettingsManager.cs` and `AstroBotLauncher.cs` (which writes the same file) and asserts the
  *shape* of the fix is still there (the write goes to a temp path, the swap is
  `File.Replace`/`File.Move`, the backup is read before giving up);
- models the save/load state machine in Python and runs it through the failure cases - interrupted
  before the swap, damaged live file, missing live file, first ever save - comparing against what the
  old code did, so the failure is demonstrated and not just asserted.

Run: python Tests/test_settings_recovery.py
Exit codes: 0 the behaviour holds, 1 it does not, 77 not checked (source missing).
"""
import json
import os
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[1]
source_path = root / "AstroHybrid.App/Services/SettingsManager.cs"
if not source_path.exists():
    print("SKIP SettingsManager.cs not found; nothing was checked")
    sys.exit(77)

source = source_path.read_text(encoding="utf-8")
failures = []


def check(condition, description):
    if condition:
        print(f"PASS {description}")
    else:
        print(f"FAIL {description}")
        failures.append(description)


# --- 1. The fix is present in the C#, in the shape it needs to be. -----------------------------
print("source shape")

save_body = source.split("public void Save(AppSettings settings)")[1]
save_body = save_body.split("/// <summary>")[0]

check("File.WriteAllText(_settingsPath" not in save_body,
      "Save does not write into the live settings file")
check("FileStream(_tempPath" in save_body,
      "Save writes the new copy to the temp path")
check("Flush(true)" in save_body,
      "the temp copy is flushed to disk before the swap")
check("File.Replace(_tempPath, _settingsPath, _backupPath" in save_body,
      "the live file is replaced atomically, keeping a .bak")
check("File.Move(_tempPath, _settingsPath)" in save_body,
      "the first save (no file to replace) moves instead")

load_body = source.split("public AppSettings Load()")[1].split("public void Save")[0]
check(load_body.index("_settingsPath") < load_body.index("_backupPath"),
      "Load tries the live file before the backup")
check("RecoveryNotice" in load_body,
      "Load reports a recovery instead of silently returning defaults")
check("return new AppSettings()" not in load_body.replace("new AppSettings();", "", 0) or
      "RecoveryNotice" in load_body,
      "falling back to defaults is not silent")

# The old code's failure, quoted so the test documents what changed.
check("catch\n                {\n                    _cachedSettings = new AppSettings();" not in source,
      "the blanket catch that hid a damaged file is gone")


# --- 1b. The classic launcher shares this file and must not undo the fix. ----------------------
print()
print("classic launcher (Tools/hybrid/launcher/AstroBotLauncher.cs)")
launcher_path = root / "Tools/hybrid/launcher/AstroBotLauncher.cs"
if not launcher_path.exists():
    check(False, "the classic launcher is still present")
else:
    launcher = launcher_path.read_text(encoding="utf-8")
    check("File.WriteAllText(settingsPath" not in launcher,
          "it does not write into the live settings file")
    check("WriteSettingsAtomically(settingsPath" in launcher,
          "it swaps the file in atomically, like the app")
    check("ReadSettingsFile(settingsPath)" in launcher,
          "it reads the .bak when the live file is damaged")
    # Replace does NOT put C# named args in front of you: the parameter is ignoreMetadataErrors, and
    # it is positional. This is the one call in the fix the checker's table cannot validate.
    check("ignoreMetadataErrors:" not in launcher and "ignoreMetadataErrors:" not in source,
          "no named argument is passed to File.Replace")
    check("catch { }\n            form.DialogResult = DialogResult.OK;" not in launcher,
          "a failed save no longer closes the window as if it succeeded")

# The PowerShell launcher writes the same file as well.
ps1_path = root / "Tools/hybrid/launcher.ps1"
if not ps1_path.exists():
    check(False, "the PowerShell launcher is still present")
else:
    ps1 = ps1_path.read_text(encoding="utf-8")
    check("WriteAllText($settingsPath" not in ps1,
          "the PowerShell launcher does not write into the live settings file")
    check("[IO.File]::Replace($tempPath, $settingsPath" in ps1,
          "the PowerShell launcher swaps the file in atomically")


# --- 2. Model the state machine and run the failure cases. -------------------------------------
class FakeDisk:
    """A filesystem where a save can be interrupted at any step, and names are per-directory."""

    def __init__(self):
        self.files = {}

    def write(self, path, text):
        self.files[path] = text

    def read(self, path):
        return self.files.get(path)


class Manager:
    """A transcription of SettingsManager's save/load order, with the same steps."""

    def __init__(self, disk, path, interrupt_after=None):
        self.disk = disk
        self.path = path
        self.backup = path + ".bak"
        self.temp = path + ".tmp"
        self.cached = None
        self.notice = None
        self.interrupt_after = interrupt_after

    def _read(self, path):
        text = self.disk.read(path)
        if text is None or text == "":
            return None
        try:
            return json.loads(text)
        except ValueError:
            return None

    def load(self):
        if self.cached is not None:
            return self.cached
        settings = self._read(self.path)
        if settings is not None:
            self.cached = settings
            return settings
        had_file = self.disk.read(self.path) is not None
        recovered = self._read(self.backup)
        if recovered is not None:
            self.cached = recovered
            self.notice = "backup used"
            return recovered
        self.cached = {}
        if had_file:
            self.notice = "defaults after damage"
        return self.cached

    def save(self, settings):
        self.cached = settings
        staged = json.dumps(settings)
        # 1. the temp copy, flushed ------------------------------------------------------------
        self.disk.write(self.temp, staged)
        if self.interrupt_after == 1:
            return  # killed here: temp file exists, live file untouched
        # 2. the atomic swap -------------------------------------------------------------------
        if self.disk.read(self.path) is not None:
            if self.interrupt_after == 2:
                # File.Replace is atomic, so an interruption lands before or after it, never in it.
                return
            self.disk.files[self.backup] = self.disk.files[self.path]
            self.disk.files[self.path] = self.disk.files.pop(self.temp)
        else:
            self.disk.files[self.path] = self.disk.files.pop(self.temp)


def old_save(disk, path, settings):
    """What the code did before: truncate the live file, then write into it."""
    disk.write(path, "")          # File.WriteAllText truncates...
    disk.write(path, json.dumps(settings)[:10])   # ...then the machine dies mid-write


print()
print("interrupted save")
GOOD = {"installPath": "E:\\AstroHybrid", "gpu": 1, "fps": 3}

# (a) A good file exists, a save is interrupted before the swap: the good file survives.
disk = FakeDisk()
disk.write("settings.json", json.dumps(GOOD))
m = Manager(disk, "settings.json", interrupt_after=1)
m.save({"installPath": "F:\\new", "gpu": 0, "fps": 1})
check(json.loads(disk.read("settings.json")) == GOOD,
      "a save killed before the swap leaves the previous settings intact")

# (b) ... and loading afterwards still finds them, without a recovery notice.
m2 = Manager(disk, "settings.json")
check(m2.load() == GOOD, "the surviving settings load normally")
check(m2.notice is None, "no recovery notice is raised when nothing was damaged")

# (c) The live file is damaged (the old code's failure): the backup is used.
disk = FakeDisk()
disk.write("settings.json", '{"installPath": "E:\\\\Astro')
disk.write("settings.json.bak", json.dumps(GOOD))
m = Manager(disk, "settings.json")
check(m.load() == GOOD, "a damaged live file falls back to the .bak, not to defaults")
check(m.notice == "backup used", "the recovery from backup is reported")

# (d) Live file and backup both damaged: defaults, but with a notice (never silent).
disk = FakeDisk()
disk.write("settings.json", "{trunc")
disk.write("settings.json.bak", "{also trunc")
m = Manager(disk, "settings.json")
check(m.load() == {} and m.notice == "defaults after damage",
      "total damage still reports, rather than silently starting over")

# (e) No file at all (first launch): defaults and no notice - that is not a failure.
disk = FakeDisk()
m = Manager(disk, "settings.json")
check(m.load() == {} and m.notice is None, "a missing file is first launch, not a recovery")

# (f) First ever save: there is nothing to replace, so the move has to work.
disk = FakeDisk()
m = Manager(disk, "settings.json")
m.save(GOOD)
check(json.loads(disk.read("settings.json")) == GOOD, "the first save creates the settings file")
check(disk.read("settings.json.tmp") is None, "no temp file is left behind")

# (g) The old behaviour, for contrast. Note there is no .bak here: the old code never wrote one, so
# an interrupted save had nothing to fall back to. That is the whole bug.
disk = FakeDisk()
disk.write("settings.json", json.dumps(GOOD))
old_save(disk, "settings.json", {"installPath": "F:\\new"})
check(disk.read("settings.json.bak") is None, "control: the old code left no backup behind")
check(Manager(disk, "settings.json").load() == {},
      "control: the old in-place write lost the settings and loaded defaults "
      "(this is the bug being fixed)")

# (i) The launcher's read path: damaged live file, good backup -> the backup is used.
def launcher_read(disk, path):
    """ReadSettingsFile: complete JSON from the live file, else from .bak."""
    def complete(text):
        if text is None:
            return False
        t = text.strip()
        return t.startswith("{") and t.endswith("}")
    text = disk.read(path)
    if complete(text):
        return json.loads(text)
    backup = disk.read(path + ".bak")
    if complete(backup):
        return json.loads(backup)
    return None


disk = FakeDisk()
disk.write("settings.json", '{"lighting": 1, "fp')
disk.write("settings.json.bak", json.dumps(GOOD))
check(launcher_read(disk, "settings.json") == GOOD,
      "the launcher falls back to the .bak instead of showing defaults")

disk = FakeDisk()
disk.write("settings.json", json.dumps({**GOOD, "oldFile": True}))
check(launcher_read(disk, "settings.json")["oldFile"] is True,
      "the launcher still reads an older file it does not have every key for")


# (h) A second save keeps exactly one generation of backup, not a growing pile.
disk = FakeDisk()
m = Manager(disk, "settings.json")
m.save({"v": 1})
m.save({"v": 2})
m.save({"v": 3})
check(json.loads(disk.read("settings.json")) == {"v": 3}, "the live file holds the newest save")
check(json.loads(disk.read("settings.json.bak")) == {"v": 2}, "the .bak holds the save before it")

print()
if failures:
    print(f"{len(failures)} settings-recovery check(s) failed")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("settings survive an interrupted save, and a recovery is never silent")
