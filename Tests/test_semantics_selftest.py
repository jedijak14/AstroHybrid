"""Prove the semantic checker still catches what it claims to catch.

`test_csharp_semantics.py` reporting "no errors" only means something if it can detect an error. This
script injects a known fault of each kind into a copy of the sources, runs the checker, and requires a
failure. If someone loosens a check, this test fails instead of the checker quietly passing everything.

Every fault is applied to a temporary copy of the tree; the repository is never modified.

A skip is contagious: if the checker cannot run because the C# grammar is missing, this exits 77
too, rather than reporting faults "not caught".

Exit codes: 0 every fault was caught, 1 a fault went unnoticed, 77 nothing was verified.
Run: python Tests/test_semantics_selftest.py
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]

FAULTS = [
    ("enum value typo", "AstroHybrid.App/ViewModels/HomeViewModel.cs",
     r"LauncherPage\.GraphicsSettings", "LauncherPage.GraphicsSetting"),
    ("member typo through a typed variable",
     "AstroHybrid.App/ViewModels/GraphicsSettingsViewModel.cs",
     r"hardware\.SupportsAmdSuperResolution", "hardware.SupportsAmdSuperResolutio"),
    ("extra argument to a repository method", "AstroHybrid.App/Services/LauncherService.cs",
     r"GpuMatchToken\(gpu\.Name\)", "GpuMatchToken(gpu.Name, 1)"),
    ("missing argument to a repository method", "AstroHybrid.App/Services/LauncherService.cs",
     r"GpuMatchToken\(gpu\.Name\)", "GpuMatchToken()"),
    ("string assigned to a bool", "AstroHybrid.App/Models/AppSettings.cs",
     r"(public void Sanitize\(HardwareInfo\? hardware\)\s*\{)",
     lambda m: m.group(1) + ' bool bad = "t";'),
    ("BCL member typo (Path.Combine)", "AstroHybrid.App/Services/LauncherService.cs",
     r"Path\.Combine\(", "Path.Combin("),
    ("BCL member typo (Math.Max)", "AstroHybrid.App/Services/LauncherService.cs",
     r"Math\.Max\(", "Math.Mxa("),
    ("BCL member typo (File.Exists)", "AstroHybrid.App/Services/LauncherService.cs",
     r"File\.Exists\(", "File.Existz("),
]

with tempfile.TemporaryDirectory() as tmp:
    work = pathlib.Path(tmp) / "repo"
    # Only what the checker reads.
    shutil.copytree(root / "AstroHybrid.App", work / "AstroHybrid.App")
    (work / "Tests").mkdir()
    for name in ("test_csharp_semantics.py",):
        shutil.copy2(root / "Tests" / name, work / "Tests" / name)

    def run_checker():
        result = subprocess.run([sys.executable, "Tests/test_csharp_semantics.py"],
                                cwd=work, capture_output=True, text=True)
        if result.returncode == 77:
            print("SKIP the semantic checker needs tree_sitter; nothing was verified")
            sys.exit(77)
        return result.returncode, result.stdout

    code, out = run_checker()
    if code != 0:
        print("baseline is not clean, cannot self-test:")
        print(out[-2000:])
        sys.exit(1)
    print("PASS baseline: no semantic errors")

    failures = 0
    for name, rel, pattern, replacement in FAULTS:
        path = work / rel
        original = path.read_text(encoding="utf-8")
        changed = re.sub(pattern, replacement, original, count=1)
        if changed == original:
            print(f"FAIL {name}: fault pattern no longer matches (update this test)")
            failures += 1
            continue
        path.write_text(changed, encoding="utf-8")
        try:
            code, out = run_checker()
        finally:
            path.write_text(original, encoding="utf-8")
        if code == 0:
            print(f"FAIL {name}: the checker did not notice")
            failures += 1
        else:
            print(f"PASS {name}: caught")

print()
if failures:
    print(f"{failures} fault(s) not caught - the semantic checker has a hole")
    sys.exit(1)
print("all injected faults caught")
