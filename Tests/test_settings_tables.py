"""Cross-check: the tables in the C# and in `settings_model.py` must be identical.

`test_settings_model.py` reasons about the launcher using the Python copy of its tables. That is only
worth anything if the copy still matches the application, so this script reads the C# sources and
compares the literals. Run it after touching any label list, lookup table or feature gate:

    python Tests/test_settings_tables.py
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import settings_model as m  # noqa: E402

root = pathlib.Path(__file__).resolve().parents[1]
launcher = (root / "AstroHybrid.App/Services/LauncherService.cs").read_text(encoding="utf-8")
graphics_vm = (root / "AstroHybrid.App/ViewModels/GraphicsSettingsViewModel.cs").read_text(encoding="utf-8")
main_vm = (root / "AstroHybrid.App/ViewModels/MainWindowViewModel.cs").read_text(encoding="utf-8")
game_info = (root / "AstroHybrid.App/Models/GameInfo.cs").read_text(encoding="utf-8")

bad = []


def compare(name, csharp, python):
    ok = csharp == python
    print(f"{'OK ' if ok else 'BAD'} {name:22} C#={csharp}" + ("" if ok else f"  py={python}"))
    if not ok:
        bad.append(name)


def strings_of(pattern, source):
    match = re.search(pattern, source, re.S)
    return re.findall(r'"([^"]*)"', match.group(1)) if match else None


def labels_of(name, source):
    match = re.search(rf"public string\[\] {name} => new\[\]\s*\{{(.*?)\}};", source, re.S)
    return re.findall(r'"([^"]*)"', match.group(1)) if match else None


# Value tables the launcher indexes with a dropdown selection.
compare("fpsValues", strings_of(r"fpsValues = new\[\] \{(.*?)\};", launcher), m.FPS_VALUES)
compare("overlayValues", strings_of(r"overlayValues = new\[\] \{(.*?)\};", launcher), m.OVERLAY_VALUES)
compare("padValues", strings_of(r"padValues = new\[\] \{(.*?)\};", launcher), m.PAD_VALUES)
compare("speedValues", strings_of(r"speedValues = new\[\] \{(.*?)\};", launcher), m.SPEED_VALUES)

# ... and the labels the user picks from, which must be the same length and order.
compare("FpsLabels", labels_of("FpsLabels", graphics_vm), m.FPS_LABELS)
compare("OverlayLabels", labels_of("OverlayLabels", graphics_vm), m.OVERLAY_LABELS)

# Two-dimensional tables.
size_match = re.search(r"sizeValues = new\[,\]\s*\{(.*?)\};", launcher, re.S)
compare("sizeValues",
        [(int(a), int(b)) for a, b in re.findall(r"\{\s*(\d+),\s*(\d+)\s*\}", size_match.group(1))],
        m.SIZE_VALUES)

rsr_match = re.search(r"rsrSize = new\[,\]\s*\{(.*?)\};", launcher, re.S)
compare("rsrSize",
        [(int(a), int(b)) for a, b in re.findall(r"\{\s*(\d+),\s*(\d+)\s*\}", rsr_match.group(1))],
        m.RSR_SIZE_VALUES)

target_values = re.search(r"targetValues = new\[\] \{([^}]*)\}", launcher).group(1)
compare("targetValues", [int(x) for x in re.findall(r"\d+", target_values)], m.TARGET_VALUES)

# Feature gates.
compare("RTX gates", [int(x) for x in re.findall(r"pc\.RtxSeries >= (\d+)", main_vm)], [20, 40, 50, 50])
compare("Radeon gates", [int(x) for x in re.findall(r"RadeonSeries >= (\d{4})", game_info)], [6000, 6000])

print()
if bad:
    print(f"{len(bad)} MISMATCH(ES): {bad}")
    print("Update Tests/settings_model.py to match the C#, or fix the C#.")
    sys.exit(1)
print("C# tables and settings_model.py agree")
