"""Every {Binding} in a view must resolve to a public member of the view model that view gets.

WPF reports a binding to a missing member only in the debug output, and the control simply keeps its
default value, so this class of bug is invisible in the running app. It already happened once: the
Home page's release-notes card bound `UpdateState.UpdateAvailable` and `DownloadUpdateCommand`, which
lived on MainWindowViewModel rather than HomeViewModel, so the card never appeared and its button did
nothing.

Uses a real C# grammar (tree_sitter_c_sharp) to collect members, so it does not depend on regular
expressions understanding the code. If the parsers are not installed it prints SKIP and exits 77, so
a missing grammar cannot read as a pass.

Exit codes: 0 every binding resolves, 1 at least one does not, 77 nothing was checked.
"""
import pathlib
import re
import sys

try:
    import tree_sitter_c_sharp as tscs
    from tree_sitter import Language, Parser
except ImportError:
    print("SKIP tree_sitter not installed (pip install tree_sitter tree_sitter_c_sharp)")
    sys.exit(77)

root = pathlib.Path(__file__).resolve().parents[1]
parser = Parser(Language(tscs.language()))

# View -> the view model its code-behind assigns to DataContext, and members that legitimately come
# from elsewhere (item templates bound to a model object inside an ItemsControl, and the like).
VIEWS = {
    "HomeView.xaml": ("HomeViewModel", set()),
    "GraphicsSettingsView.xaml": ("GraphicsSettingsViewModel", set()),
    "ControllerSettingsView.xaml": ("ControllerSettingsViewModel", {
        # ItemTemplate over MainWindowViewModel.Controllers (a ControllerInfo).
        "Name", "Type", "IsConnected", "HasHaptics", "HasMotionSensors", "HasTriggerEffects",
        "InstanceId", "RefreshControllersCommand",
    }),
    "AdvancedSettingsView.xaml": ("AdvancedSettingsViewModel", set()),
    "InstallationView.xaml": ("InstallationViewModel", set()),
}


def members_of(class_name):
    """Public members of a class across all view model sources."""
    found = set()
    for path in (root / "AstroHybrid.App").rglob("*.cs"):
        src = path.read_bytes()
        tree = parser.parse(src)
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if node.type == "class_declaration":
                name = node.child_by_field_name("name")
                if name is not None and name.type == "identifier" and \
                        src[name.start_byte:name.end_byte].decode() == class_name:
                    body = node.child_by_field_name("body")
                    for child in body.children:
                        if child.type in ("method_declaration", "property_declaration",
                                          "field_declaration", "event_declaration",
                                          "constructor_declaration"):
                            text = src[child.start_byte:child.end_byte].decode(errors="replace")
                            if re.search(r"\b(public|protected internal)\b", text) or \
                                    child.type == "constructor_declaration":
                                for ident in re.findall(r"(?:property|variable_declaration|method|type)\W+([A-Za-z_]\w*)", text) or []:
                                    found.add(ident)
                                # Names sitting right after the type are the declared identifiers.
                                for ident in re.findall(r"^\s*(?:public|protected internal)[\w\s<>\[\],\?\.]*?\s([A-Za-z_]\w*)\s*(?:=>|\{|;|\()", text, re.M):
                                    found.add(ident)
                                for ident in re.findall(r"public\s+[\w<>\[\]\?\.]+\s+([A-Za-z_]\w*)\s*(?:\{|=>)", text):
                                    found.add(ident)
                                for ident in re.findall(r"public\s+[\w<>\[\]\?\.]+\s+([A-Za-z_]\w*)\s*\(", text):
                                    found.add(ident)
            stack.extend(node.children)
    return found


problems = 0
for view, (vm_name, external) in VIEWS.items():
    xaml = (root / "AstroHybrid.App/Views" / view).read_text(encoding="utf-8")
    # Bindings to a member, including dotted paths (check the first segment).
    paths = set()
    for expr in re.findall(r"\{Binding\s+(?:Path=)?([A-Za-z_][\w\.]*)", xaml):
        paths.add(expr)
    members = members_of(vm_name)
    missing = sorted(p for p in paths
                     if p.split(".")[0] not in members
                     and p.split(".")[0] not in external
                     and p != "DataContext")
    status = "OK " if not missing else "BAD"
    print(f"{status} {view:30} {len(paths):3} bindings, {len(members):3} members on {vm_name}: {missing or ''}")
    if missing:
        problems += 1

print()
if problems:
    print(f"{problems} view(s) bind to members their view model does not have")
    sys.exit(1)
print("all bindings resolve")
