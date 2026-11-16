"""The project file must reference every assembly the code uses.

An old-style .NET Framework project file (`<Reference Include=...>`) does not bring framework
assemblies in implicitly: using `System.Net.Http` or `System.IO.Compression` without the matching
reference is CS0246 at build time. That is exactly how `UpdateService.cs` (the launcher's update
system) sat on `main` unable to compile - it uses HttpClient and ZipFile, and the project referenced
neither - and nothing noticed because this machine has no .NET toolchain and the file was never in a
tagged release.

This reads the `using` lines and the qualified names the code actually calls, maps them to the
assembly each one lives in on .NET Framework 4.8, and fails when a reference is missing. It also
checks the reverse direction lightly: a reference nothing uses is reported, not failed, since a
harmless extra reference is not a bug.

Run: python Tests/test_project_references.py
Exit codes: 0 every assembly used is referenced, 1 one is missing, 77 not checked (no csproj).
"""
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[1]
project_dir = root / "AstroHybrid.App"
csproj_path = project_dir / "AstroHybrid.App.csproj"
if not csproj_path.exists():
    print("SKIP AstroHybrid.App.csproj not found; nothing was checked")
    sys.exit(77)

csproj = csproj_path.read_text(encoding="utf-8")
references = set(re.findall(r'<Reference Include="([^"]+)"', csproj))
packages = set(re.findall(r'<PackageReference Include="([^"]+)"', csproj))
compile_items = set(re.findall(r'<Compile Include="([^"]+)"', csproj))

# .NET Framework 4.8: namespace -> the assembly that must be referenced. None means the type lives in
# mscorlib/System/System.Core (always available), or a package reference covers it.
ASSEMBLY_OF = {
    "System": None,
    "System.IO": None,
    "System.Text": None,
    "System.Linq": None,
    "System.Collections": None,
    "System.Collections.Generic": None,
    "System.Collections.ObjectModel": None,
    "System.Threading": None,
    "System.Threading.Tasks": None,
    "System.Globalization": None,
    "System.Diagnostics": None,
    "System.Reflection": None,
    "System.Runtime": None,
    "System.Runtime.CompilerServices": None,
    "System.Runtime.InteropServices": None,
    "System.Security.Cryptography": None,
    "System.ComponentModel": None,
    "System.Text.RegularExpressions": None,
    "System.Text.Json": "System.Text.Json",              # PackageReference
    "System.Text.Json.Serialization": "System.Text.Json",
    "System.Net.Http": "System.Net.Http",
    "System.IO.Compression": "System.IO.Compression",
    "System.IO.Compression.FileSystem": "System.IO.Compression.FileSystem",
    "System.Management": "System.Management",
    "System.Drawing": "System.Drawing",
    "System.Windows.Forms": "System.Windows.Forms",
    "System.Windows": "PresentationFramework",
    "System.Windows.Controls": "PresentationFramework",
    "System.Windows.Data": "PresentationFramework",
    "System.Windows.Input": "PresentationCore",
    "System.Windows.Media": "PresentationCore",
    "System.Windows.Media.Imaging": "PresentationCore",
    "System.Windows.Shapes": "PresentationCore",
    "System.Windows.Threading": "WindowsBase",
    "System.Xaml": "System.Xaml",
    "System.ComponentModel.DataAnnotations": "System.ComponentModel.DataAnnotations",
}

# Types whose namespace is not always the one the using line names, keyed by the name used in code.
TYPE_ASSEMBLY = {
    "ZipFile": "System.IO.Compression.FileSystem",
    "ZipArchive": "System.IO.Compression",
    "ZipArchiveEntry": "System.IO.Compression",
    "CompressionLevel": "System.IO.Compression",
    "HttpClient": "System.Net.Http",
    "HttpRequestMessage": "System.Net.Http",
    "HttpResponseMessage": "System.Net.Http",
    "ManagementObjectSearcher": "System.Management",
}

failures = []
notes = []


def check(condition, description):
    if condition:
        print(f"PASS {description}")
    else:
        print(f"FAIL {description}")
        failures.append(description)


files = sorted(project_dir.rglob("*.cs"))
print(f"{len(files)} C# files, {len(references)} references, {len(packages)} packages")
print()

# --- 1. Every using line maps to a referenced assembly. ---------------------------------------
print("namespaces")
unmapped = set()
needed = {}
for path in files:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for match in re.finditer(r'^using\s+([\w\.]+)\s*;', text, re.M):
        namespace = match.group(1)
        if namespace.startswith("AstroHybrid."):
            continue                      # this project's own namespaces
        if namespace not in ASSEMBLY_OF:
            unmapped.add(namespace)
            continue
        assembly = ASSEMBLY_OF[namespace]
        if assembly:
            needed.setdefault(assembly, set()).add(f"{namespace} (used in {path.name})")

for assembly in sorted(needed):
    sources = sorted(needed[assembly])
    check(assembly in references or assembly in packages,
          f"{assembly} is referenced  <- {sources[0]}")

if unmapped:
    # Not a failure: a new namespace appears as soon as someone adds a using, and failing on it would
    # make this test an obstacle instead of a check. It is printed so the map can be kept current.
    for namespace in sorted(unmapped):
        notes.append(f"namespace not in the map, add it to ASSEMBLY_OF: {namespace}")

# --- 2. Types that need an assembly regardless of the using lines. -----------------------------
print()
print("types")
for type_name, assembly in sorted(TYPE_ASSEMBLY.items()):
    users = [p.name for p in files if re.search(rf'\b{type_name}\b', p.read_text(encoding="utf-8", errors="ignore"))]
    if not users:
        continue
    check(assembly in references or assembly in packages,
          f"{assembly} is referenced for {type_name}  <- {users[0]}")

# --- 3. Every .cs file is in the compile list. ------------------------------------------------
# A file left out of <Compile Include> is silently not built: the code is there in the repository but
# not in the executable, which is a confusing way to lose a feature.
print()
print("compile list")
listed = {item.replace("\\", "/") for item in compile_items}
for path in files:
    relative = path.relative_to(project_dir).as_posix()
    check(relative in listed, f"{relative} is in <Compile Include>")

# --- 4. References nothing in the code uses: reported, not failed. ----------------------------
used_namespaces = set()
for path in files:
    text = path.read_text(encoding="utf-8", errors="ignore")
    used_namespaces.update(re.findall(r'^using\s+([\w\.]+)\s*;', text, re.M))
assemblies_used = {ASSEMBLY_OF[n] for n in used_namespaces if ASSEMBLY_OF.get(n)}
assemblies_used |= {a for t, a in TYPE_ASSEMBLY.items()
                    if any(re.search(rf'\b{t}\b', p.read_text(encoding="utf-8", errors="ignore")) for p in files)}
for reference in sorted(references - assemblies_used):
    notes.append(f"referenced but not used by any using line (fine): {reference}")

print()
for note in notes:
    print("NOTE", note)

print()
if failures:
    print(f"{len(failures)} reference check(s) failed")
    sys.exit(1)
print("every assembly the code uses is referenced by the project")
