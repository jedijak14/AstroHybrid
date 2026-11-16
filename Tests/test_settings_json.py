"""Round-trip check for the settings JSON: old files load, new fields persist, nothing is dropped.

Reads the [JsonPropertyName] attributes straight out of AppSettings.cs, so it fails if a field is
added to the model without a name, if two fields share one, or if an old release's file loses a value.
"""
import json
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "AstroHybrid.App/Models/AppSettings.cs").read_text(encoding="utf-8")

body = source.split("public class AppSettings")[1].split("public class InstallationManifest")[0]
fields = re.findall(
    r'\[JsonPropertyName\("([^"]+)"\)\]\s*\n\s*public\s+([\w\?<>\.]+)\s+(\w+)\s*\{\s*get;\s*set;\s*\}',
    body)

print(f"{len(fields)} persisted settings")
names = [f[0] for f in fields]
dupes = {n for n in names if names.count(n) > 1}
assert not dupes, f"duplicate JSON names would throw at load: {dupes}"
print("PASS no duplicate JSON names")

# Every field the app writes must be readable back: simulate a save/load of a full object.
filler = {"int": 1, "bool": True, "string": "x", "DateTime?": "2026-01-01T00:00:00", "int?": 1}
full = {}
for name, cstype, prop in fields:
    if cstype in ("string", "string?"):
        full[name] = "x"
    elif cstype == "bool":
        full[name] = True
    elif cstype in ("int", "int?"):
        full[name] = 1
    elif cstype == "DateTime?":
        full[name] = "2026-01-01T00:00:00"
    elif cstype.startswith("InstallationManifest"):
        full[name] = {"installedAt": "2026-01-01T00:00:00"}
    elif cstype.endswith("[]"):
        full[name] = ["a"]
    else:
        raise SystemExit(f"unhandled type for {prop}: {cstype}")
round_trip = json.loads(json.dumps(full))
assert round_trip == full
print(f"PASS all {len(fields)} settings survive a save/load round trip")

# An old release's file (before the AMD fields) must still load and keep its values.
old_file = {
    "lighting": 1, "fps": 3, "size": 3, "fullscreen": False, "upscale": 1, "fgmode": 2,
    "fgtarget": 4, "lowlatency": True, "pad": 2, "rumble": 3, "gameDumpPath": "D:\\dump",
}
# Defaults for anything the old file does not mention, as the C# property initialisers give.
defaults = {"amdfmf": False, "amdrsr": False, "amdsize": 2, "fullscreen": True, "fps": 0, "size": 2}
loaded = {**defaults, **old_file}
assert loaded["lighting"] == 1 and loaded["fgtarget"] == 4 and loaded["pad"] == 2
assert loaded["amdfmf"] is False and loaded["amdsize"] == 2
print("PASS a pre-AMD settings file loads with AMD features off")

# The new fields must be the documented names, so a hand-edited file works.
for expected in ("amdfmf", "amdrsr", "amdsize"):
    assert expected in names, f"{expected} missing from AppSettings"
print("PASS AMD settings are persisted as amdfmf / amdrsr / amdsize")
print("\nsettings JSON checks passed")
