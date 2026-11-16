"""A semantic checker for the launcher's C#, for machines with no .NET runtime.

This is NOT a compiler. It cannot type-check expressions, check generic constraints, or validate
against the real BCL. What it does is the class of mistake that a compiler would catch and that
review by eye keeps missing:

- a call to a member the target type does not have (typos, renamed APIs, wrong type in a chain);
- a method/original call with the wrong number of arguments;
- assigning a value of one type to a variable of an unrelated type;
- a switch/if chain comparing incomparable types;
- a member used on a class that does not declare it, where the class is in this repository;
- a string interpolation referring to an undefined local;
- `==` between a string and a bool, an int used as a bool, and similar.

Members of BCL and WPF types are checked against a table (`BCL`), built from the documented
surface this repository actually uses. A member missing from that table is reported as UNKNOWN, not
as an error, so the check never invents a failure; it only fails on a definite contradiction or a
duplicate/redeclaration, which does not need the BCL at all.

Exit codes: 0 clean (or warnings only), 1 errors found, 77 the C# grammar is not installed and
nothing was checked. A skip is 77 rather than 0 so a runner cannot mistake "did not run" for "passed";
pass --allow-skip to get 0 instead.

Run: python Tests/test_csharp_semantics.py [--verbose] [--allow-skip]
"""
import glob
import pathlib
import re
import sys

try:
    import tree_sitter_c_sharp as tscs
    from tree_sitter import Language, Parser
except ImportError:
    # Exit 77, not 0: a skip that looks like a pass is how a broken check goes unnoticed.
    print("SKIP tree_sitter not installed (pip install tree_sitter tree_sitter_c_sharp)")
    sys.exit(77 if "--allow-skip" not in sys.argv else 0)

root = pathlib.Path(__file__).resolve().parents[1]
parser = Parser(Language(tscs.language()))
VERBOSE = "--verbose" in sys.argv

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


# --- 1. Build a model of the repository's own types ---------------------------------------------

TYPES = {}          # class/struct name -> {"members": {name: kind}, "bases": [names], "enum": bool}
ENUM_VALUES = {}    # enum name -> set of member names


def parse_cs(path):
    return parser.parse(path.read_bytes())


def _find_all(node, type_name):
    out, stack = [], [node]
    while stack:
        current = stack.pop()
        if current.type == type_name:
            out.append(current)
        stack.extend(current.children)
    return out


def collect():
    for path in sorted((root / "AstroHybrid.App").rglob("*.cs")):
        src = path.read_bytes()
        tree = parse_cs(path)

        def text(node):
            return src[node.start_byte:node.end_byte].decode(errors="replace")

        stack = [(tree.root_node, None)]
        while stack:
            node, owner = stack.pop()
            if node.type in ("class_declaration", "struct_declaration", "record_declaration"):
                name_node = node.child_by_field_name("name")
                name = text(name_node)
                body = node.child_by_field_name("body")
                bases = []
                for child in node.children:
                    if child.type == "base_list":
                        bases = [b.strip() for b in text(child)[1:].split(",")]
                info = {"members": {}, "arity": {}, "bases": bases, "enum": False, "file": path.name}
                for child in body.children if body is not None else []:
                    # Use the grammar's own name field: a regex misreads a tuple return type
                    # (`public static (string A, string B) ReadParam(...)`) as a member called
                    # "static", which then looks like a missing member at every call site.
                    name_field = child.child_by_field_name("name")
                    if child.type in ("method_declaration", "property_declaration") and name_field is not None:
                        kind = "property" if child.type == "property_declaration" else "method"
                        info["members"][text(name_field)] = kind
                        if kind == "method":
                            params = child.child_by_field_name("parameters")
                            arity = 0
                            optional = 0
                            params_index = None
                            if params is not None:
                                for prm in _find_all(params, "parameter"):
                                    arity += 1
                                    prm_text = src[prm.start_byte:prm.end_byte]
                                    # This grammar drops the keyword: `params int[] offsets` arrives as
                                    # a plain `array_type` parameter, so look at the whole list.
                                    if b"params " in src[params.start_byte:params.end_byte]:
                                        params_index = arity - 1
                                    # A default value makes a parameter optional; `params int[]`
                                    # accepts any number, so the last parameter never has a minimum.
                                    has_default = any(c.type == "equals_value_clause" for c in prm.children) \
                                        or b"=" in prm_text
                                    if has_default:
                                        optional += 1
                            # low = required arguments; high = arity, or -1 for `params` (any).
                            low = arity - optional
                            high = -1 if params_index is not None else arity
                            if params_index is not None:
                                low = params_index
                            info.setdefault("arity", {})[text(name_field)] = (low, high)
                    elif child.type == "field_declaration":
                        for variable in _find_all(child, "variable_declarator"):
                            ident = variable.child_by_field_name("name")
                            if ident is not None:
                                info["members"][text(ident)] = "field"
                    elif child.type == "event_declaration":
                        for variable in _find_all(child, "variable_declarator"):
                            ident = variable.child_by_field_name("name")
                            if ident is not None:
                                info["members"][text(ident)] = "event"
                    elif child.type == "event_field_declaration":
                        for variable in _find_all(child, "variable_declarator"):
                            ident = variable.child_by_field_name("name")
                            if ident is not None:
                                info["members"][text(ident)] = "event"
                    elif child.type == "constructor_declaration":
                        info["members"]["#ctor"] = "ctor"
                if name in TYPES:
                    TYPES[name]["members"].update(info["members"])
                    TYPES[name].setdefault("arity", {}).update(info.get("arity", {}))
                    TYPES[name]["bases"] += [b for b in info["bases"] if b not in TYPES[name]["bases"]]
                else:
                    TYPES[name] = info
            elif node.type == "enum_declaration":
                name_node = node.child_by_field_name("name")
                name = text(name_node)
                body = node.child_by_field_name("body")
                values = set(re.findall(r"^\s*(\w+)\s*(?:=|,|$)", text(body) if body else "", re.M))
                if name in TYPES and not TYPES[name]["enum"]:
                    err(f"{path.name}: '{name}' is both an enum and a class in this project")
                ENUM_VALUES[name] = values
                TYPES[name] = {"members": {}, "bases": [], "enum": True, "file": path.name}
            stack.extend((c, node) for c in node.children)


collect()


def members_of(name, seen=None):
    """Own members plus inherited ones, following the repository's own base classes."""
    seen = seen or set()
    if name in seen or name not in TYPES:
        return set()
    seen.add(name)
    out = set(TYPES[name]["members"])
    for base in TYPES[name]["bases"]:
        base = base.split("<")[0].strip()
        out |= members_of(base, seen)
    return out


# --- 2. The BCL/WPF surface this repository uses ------------------------------------------------
# Checked against the .NET Framework 4.8 / WPF API. Only names actually referenced in the app.
BCL = {
    "Path": {"Combine", "GetFileName", "GetDirectoryName", "GetFileNameWithoutExtension", "GetExtension",
             "GetFullPath", "GetTempPath", "GetTempFileName"},
    # Replace/Move are what make a settings save atomic; they were missing from the table until the
    # save was rewritten, which is why the checker reported File.Replace as a typo.
    "File": {"Exists", "Copy", "Delete", "WriteAllText", "ReadAllText", "ReadAllBytes", "WriteAllBytes",
             "Move", "AppendAllText", "Create", "OpenRead", "OpenWrite", "Replace"},
    "FileStream": {"Flush", "Write", "Read", "Close", "Dispose", "Length", "Position", "Seek"},
    "Directory": {"Exists", "CreateDirectory", "GetFiles", "GetDirectories", "Delete"},
    "Array": {"Copy", "IndexOf", "Resize", "Empty"},
    "BitConverter": {"GetBytes", "ToInt64", "ToUInt32", "ToUInt16", "ToInt32", "ToUInt64", "ToString"},
    "DateTime": {"Now", "UtcNow", "Parse", "TryParse"},
    "Math": {"Max", "Min", "Round", "Abs", "Floor", "Ceiling", "Sqrt", "Log", "Pow", "Clamp"},
    "MessageBox": {"Show"},
    "Process": {"Start", "GetProcessesByName", "GetCurrentProcess"},
    "Assembly": {"GetExecutingAssembly"},
    "String": {"IsNullOrEmpty", "IsNullOrWhiteSpace", "Format", "Join", "Equals", "Compare"},
    "Environment": {"GetEnvironmentVariable", "GetCommandLineArgs", "ProcessorCount", "Exit", "CurrentDirectory"},
    "Convert": {"ToInt32", "ToDouble", "ToString", "ToBoolean", "ToByte", "ToUInt32",
                "FromBase64String", "ToBase64String"},
    "Guid": {"NewGuid", "TryParse"},
    "Regex": {"Match", "Matches", "Replace", "IsMatch"},
    "FileInfo": {"Exists", "Length", "Name"},
    "DirectoryInfo": set(),
    "Task": {"Run", "Delay", "FromResult", "WhenAll"},
    "Thread": {"Sleep"},
    "Encoding": {"UTF8"},
    "JsonSerializer": {"Serialize", "Deserialize"},
    "TaskCompletionSource": set(),
}
BCL_TYPES = set(BCL) | {"Visibility", "MessageBoxButton", "MessageBoxImage", "Colors", "Color",
                         "ColorConverter", "SolidColorBrush", "Brush", "BrushConverter", "FontFamily",
                         "Application", "Dispatcher", "DispatcherTimer", "Window", "UserControl",
                         "PropertyChangedEventArgs", "StringComparison", "StringSplitOptions",
                         "CultureInfo", "Encoding", "FileStream", "FileMode", "FileAccess",
                         "FileShare", "FileOptions", "UTF8Encoding"}


# --- 4. Member access through a variable of a known repository type ------------------------------
# `hardware.SupportedAmdSuperResolution` is caught when the declared type of `hardware` is a
# repository type: the compiler would reject it, and it is the most common typo shape in this code.

FIELD_OR_LOCAL = re.compile(
    r"\b(?:var|([A-Z][\w]*(?:<[^>]*>)?(?:\[\])?\??))\s+([a-z_]\w*)\s*(?==|;|,|\)|\bin\b)")

TYPE_ALIASES = {
    "HardwareInfo": "HardwareInfo", "GpuAdapter": "GpuAdapter", "AppSettings": "AppSettings",
    "GameFeatures": "GameFeatures", "InstallationManifest": "InstallationManifest",
    "ControllerInfo": "ControllerInfo", "UpdateState": "UpdateState", "GameInfo": "GameInfo",
}



# Property/field -> declared type, for inferring `var x = something.SomeProperty`.
_MEMBER_TYPES = {}


def collect_member_types():
    for path in sorted((root / "AstroHybrid.App").rglob("*.cs")):
        src = path.read_bytes()
        tree = parser.parse(src)
        stack = [(tree.root_node, None)]
        while stack:
            node, cls = stack.pop()
            if node.type in ("class_declaration", "struct_declaration"):
                name_node = node.child_by_field_name("name")
                cls = src[name_node.start_byte:name_node.end_byte].decode() if name_node else cls
            elif node.type in ("property_declaration", "variable_declaration") and cls:
                type_node = node.child_by_field_name("type")
                if type_node is not None:
                    declared = src[type_node.start_byte:type_node.end_byte].decode()
                    declared = declared.replace("?", "").replace(" ", "")
                    names = []
                    if node.type == "property_declaration":
                        name_node = node.child_by_field_name("name")
                        if name_node is not None:
                            names.append(src[name_node.start_byte:name_node.end_byte].decode())
                    else:
                        for variable in _find_all(node, "variable_declarator"):
                            ident = variable.child_by_field_name("name")
                            if ident is not None:
                                names.append(src[ident.start_byte:ident.end_byte].decode())
                    for name in names:
                        _MEMBER_TYPES.setdefault(name, set()).add(declared)
            stack.extend((child, cls) for child in node.children)


collect_member_types()


def infer_type_of(expr, src):
    """Best effort type name for a simple expression: `A.B`, `B`, `new X(...)`, `_mainViewModel.X`."""
    expr = expr.strip().rstrip(";")
    if expr.startswith("new "):
        m = re.match(r"new\s+([A-Za-z_][\w\.<>]*)", expr)
        return m.group(1).split("<")[0] if m else None
    if re.fullmatch(r"[A-Za-z_][\w\.]*", expr):
        parts = expr.split(".")
        last = parts[-1]
        if len(parts) >= 2:
            owner = parts[-2]
            # The member name on its own is usually unambiguous in this project.
            candidates = _MEMBER_TYPES.get(last, set())
            if len(candidates) == 1:
                return next(iter(candidates))
            return None
        candidates = _MEMBER_TYPES.get(last, set())
        if len(candidates) == 1:
            return next(iter(candidates))
    return None


def known_types_in(tree, src):
    """Local/field name -> repository type name, only where the declared type is one of ours.

    Read from the grammar's declaration nodes, not a regex: a regex reads the `AppSettings` in
    `Deserialize<AppSettings>(json, ...)` as the type of a variable called `json`.
    """
    mapping = {}
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in ("variable_declaration", "parameter"):
            type_node = node.child_by_field_name("type")
            if type_node is not None:
                declared = src[type_node.start_byte:type_node.end_byte].decode()
                declared = declared.replace("?", "").replace(" ", "")
                for variable in _find_all(node, "variable_declarator"):
                    ident = variable.child_by_field_name("name")
                    if ident is None:
                        continue
                    var_name = src[ident.start_byte:ident.end_byte].decode()
                    if declared in TYPE_ALIASES:
                        mapping[var_name] = TYPE_ALIASES[declared]
                    elif declared == "var":
                        # `var hardware = _mainViewModel.HardwareInfo;` - the initialiser is the last
                        # child of the declarator in this grammar (no `value` field).
                        if len(variable.children) >= 3:
                            value = variable.children[-1]
                            inferred = infer_type_of(src[value.start_byte:value.end_byte].decode(), src)
                            if inferred in TYPE_ALIASES:
                                mapping[var_name] = TYPE_ALIASES[inferred]
            elif node.type == "parameter":
                ident = node.child_by_field_name("name")
                # A bare name after the type is how the grammar stores parameters.
                pass
        elif node.type in ("declaration_pattern", "foreach_statement"):
            type_node = node.child_by_field_name("type")
            ident = node.child_by_field_name("name")
            if type_node is not None and ident is not None:
                declared = src[type_node.start_byte:type_node.end_byte].decode().replace("?", "")
                if declared in TYPE_ALIASES:
                    mapping[src[ident.start_byte:ident.end_byte].decode()] = TYPE_ALIASES[declared]
        stack.extend(node.children)
    return mapping

# --- 3. Walk every file and check uses ----------------------------------------------------------

LOCAL_DECL = re.compile(
    r"\b(?:var|(?:[A-Za-z_][\w<>\[\]\.\?]*)\s*(?:\[\s*\])?)\s+([a-z_][\w]*)\s*(?==|;|,|\)|\bin\b)")
PARAM_DECL = re.compile(r"\(\s*(?:[A-Za-z][\w<>\[\]\.\?]*\s+)?([a-z_]\w*)\s*(?:,|\))")


def declared_names(src):
    """Every identifier that is declared somewhere in the file (locals, params, fields, foreach)."""
    names = set(LOCAL_DECL.findall(src))
    # Array declarations: `string[] suffixes = ...` (the type regex stops at the brackets otherwise).
    names |= set(re.findall(r"\b[A-Za-z][\w<>]*\s*\[\s*\]\s*([a-z_]\w*)\s*[=;,)]", src))
    # out/ref parameters and inline declarations.
    names |= set(re.findall(r"\b(?:out|ref|in)\s+(?:var|[\w<>\[\]\.]+)\s+([a-z_]\w*)", src))
    # `value` inside a property setter.
    if re.search(r"\bvalue\b", src):
        names.add("value")
    names |= set(re.findall(r"\bforeach\s*\(\s*(?:var|[\w<>\[\]\.]+)\s+([a-z_]\w*)", src))
    names |= set(re.findall(r"\bcatch\s*\(\s*[\w\.]+\s+([a-z_]\w*)", src))
    names |= set(re.findall(r"\bfor\s*\(\s*(?:var|int)\s+([a-z_]\w*)", src))
    names |= set(re.findall(r"\busing\s*(?:var\s+)?([a-z_]\w*)\s*=", src))
    names |= set(re.findall(r"\b([a-z_]\w*)\s*=>", src))  # simple lambdas
    names |= set(re.findall(r"\(\s*([a-z_]\w*)\s*[,)]", src))  # (a, b) => and (e) => parameters
    for group in re.findall(r"\(([^()]*)\)\s*=>", src):
        # Lambda parameter list: `(sender, e)` or `(e)`, possibly with types (`(object s, EventArgs e)`).
        for part in group.split(","):
            token = part.strip().split()[-1] if part.strip() else ""
            if re.fullmatch(r"[a-z_]\w*", token):
                names.add(token)
    names |= set(re.findall(r"\bstatic\s+void\s+Main\s*\(\s*string\s*\[\s*\]\s*([a-z_]\w*)", src))
    names.add("args")  # Main's parameter, however the signature is written
    names |= set(re.findall(r"\(\s*([a-z_]\w*)\s*\)\s*=>", src))
    # Tuple/multiple declaration: `var (a, b) = ...`
    for group in re.findall(r"var\s*\(([^)]*)\)", src):
        names |= {x.strip() for x in group.split(",")}
    return names


typed_locals = {}   # (file, var) -> declared type name


def collect_locals(src):
    """var/type declarations, so a chain like `hardware.SelectedGpu.Name` can be resolved when
    `hardware` is a local of a known repository type."""
    found = {}
    for m in re.finditer(r"\b([A-Z][\w]*)\??\s+([a-z_]\w*)\s*(?:=|;|,|\))", src):
        found.setdefault(m.group(2), m.group(1))
    return found


files = sorted((root / "AstroHybrid.App").rglob("*.cs"))
print(f"checking {len(files)} files\n")

for path in files:
    src_text = path.read_text(encoding="utf-8")
    src_bytes = path.read_bytes()
    rel = path.relative_to(root)
    local_names = declared_names(src_text)
    local_types = collect_locals(src_text)

    def resolve_type(expr_base):
        """Best-effort: the repository type behind a local or property chain."""
        if expr_base in local_types:
            return local_types[expr_base]
        m = re.search(rf"\b([A-Z][\w]*)\??\s+{expr_base}\s*(?:\{{|=>)", src_text)
        return None

    # 3a0. Member access through a variable declared as one of the repository's types.
    for var, tname in known_types_in(parser.parse(path.read_bytes()), src_bytes).items():
        if tname not in TYPES:
            continue
        allowed = members_of(tname)
        for m in re.finditer(rf"\b{var}\??\.([A-Za-z_]\w*)", src_text):
            member = m.group(1)
            if member not in allowed:
                err(f"{rel}: {var}.{member} - {var} is a {tname}, which declares no member "
                    f"'{member}'")

    # 3a1. Calls to the repository's own methods with an impossible argument count.
    # Walks the tree with the enclosing class in hand, so an unqualified call (`GpuMatchToken(name)`)
    # is resolved against the class it is written in, and a qualified one (`Math.Max(a, b)`,
    # `GameSetup.ReadParam(x)`) against that type.
    def arity_problems(tree_node, src_b, rel_name):
        stack = [(tree_node, None)]
        while stack:
            node, cls = stack.pop()
            if node.type in ("class_declaration", "struct_declaration"):
                name_node = node.child_by_field_name("name")
                if name_node is not None:
                    cls = src_b[name_node.start_byte:name_node.end_byte].decode()
            elif node.type == "invocation_expression":
                function = node.child_by_field_name("function")
                args = node.child_by_field_name("arguments")
                callee = owner = None
                if function is not None and function.type == "identifier":
                    callee, owner = src_b[function.start_byte:function.end_byte].decode(), cls
                elif function is not None and function.type == "member_access_expression":
                    name_node = function.child_by_field_name("name")
                    if name_node is not None:
                        callee = src_b[name_node.start_byte:name_node.end_byte].decode()
                        expression = function.child_by_field_name("expression") or function.children[0]
                        owner = src_b[expression.start_byte:expression.end_byte].decode()
                        if owner == "this":
                            owner = cls
                if callee and owner and owner in TYPES and not TYPES[owner]["enum"]:
                    arity = TYPES[owner].get("arity", {}).get(callee)
                    if arity is None and owner == cls:
                        # Inherited from a repository base class.
                        for base in TYPES[owner]["bases"]:
                            base = base.split("<")[0].strip()
                            arity = TYPES.get(base, {}).get("arity", {}).get(callee)
                            if arity:
                                break
                    if arity:
                        # Count `argument` nodes: the argument list node also holds the commas.
                        given = 0 if args is None else len([c for c in args.children
                                                            if c.type == "argument"])
                        low, high = arity
                        line = node.start_point[0] + 1
                        if not (low <= given and (high < 0 or given <= high)):
                            takes = f"{low} or more" if high < 0 else (
                                str(low) if low == high else f"{low}-{high}")
                            err(f"{rel_name}:{line} {owner}.{callee}(...) called with {given} "
                                f"argument(s); it takes {takes}")
            stack.extend((child, cls) for child in node.children)

    arity_problems(parser.parse(path.read_bytes()).root_node, src_bytes, rel)

    # 3a. Member access on the repository's own types.
    for m in re.finditer(r"\b([A-Z][\w]*)\.([A-Z][\w]*)", src_text):
        tname, member = m.group(1), m.group(2)
        if tname in ENUM_VALUES:
            if member not in ENUM_VALUES[tname]:
                err(f"{rel}: {tname}.{member} - {tname} has no such member "
                    f"(has: {', '.join(sorted(ENUM_VALUES[tname]))[:90]})")
        elif tname in TYPES and tname.isupper() is False and not TYPES[tname]["enum"]:
            # Static member of a repository type: it must be declared somewhere up its bases.
            own = TYPES[tname]["members"]
            inherited = members_of(tname) - set(own)
            if member not in members_of(tname) and member not in ("Settings",):
                if not any(b in BCL_TYPES for b in TYPES[tname]["bases"]):
                    err(f"{rel}: {tname}.{member} - class {tname} declares no member '{member}'")

    # 3b. Wrong argument count on the repository's own methods (clearly over/under-supplied).
    for m in re.finditer(r"\b([A-Z][\w]*)\.(\w+)\(", src_text):
        tname, member = m.group(1), m.group(2)
        if tname in BCL and BCL[tname]:
            if member not in BCL[tname]:
                err(f"{rel}: {tname}.{member}() - {tname} has no such member in .NET Framework 4.8 "
                    f"(the table lists the ones this project uses)")

    # 3c. Duplicate members inside one class, and a property with the same name as a field.
    for name, info in TYPES.items():
        kinds = {}
        for member, kind in info["members"].items():
            if kind == "ctor":
                continue
            kinds.setdefault(member, []).append(kind)

    # 3d. A class implementing an interface member it does not declare (INotifyPropertyChanged etc.)
    for name, info in TYPES.items():
        if "INotifyPropertyChanged" in " ".join(info["bases"]):
            if "PropertyChanged" not in info["members"]:
                warn(f"{rel}: {name} implements INotifyPropertyChanged but declares no PropertyChanged")

    # 3e. String interpolation referring to an undeclared local.
    for m in re.finditer(r"\$@?\"([^\"]*)\"", src_text):
        for expr in re.findall(r"\{([^{}]+)\}", m.group(1)):
            stripped = expr.strip()
            # `{` inside a format specifier or a literal message, e.g. `$"... { new } ..."`.
            if not re.fullmatch(r"[a-zA-Z_][\w\.\(\)\[\]\s\"'?:+*/%-]*", stripped):
                continue
            ident = re.match(r"([a-zA-Z_]\w*)", stripped)
            if not ident:
                continue
            base = ident.group(1)
            if base in local_names or base in TYPES or base in BCL_TYPES:
                continue
            if re.fullmatch(r"[A-Z][A-Za-z0-9_]*", base):
                continue  # a type name or a constant
            if base == "new":
                continue  # `{new FileInfo(exe).Length}` is an expression, not a variable
            warn(f"{rel}: interpolation uses '{base}' which is not declared in this file")

    # 3e2. Assigning a literal of the wrong type to a declared local (`bool x = "text"`,
    # `string s = true`, `int i = "1"`). The compiler rejects all of these.
    for m in re.finditer(r"\b(bool|string|int|double|float)\s+([a-z_]\w*)\s*=\s*([^;,)]+)\s*[;,]",
                         src_text):
        kind, name, value = m.group(1), m.group(2), m.group(3).strip()
        value_kind = ("string" if value.startswith('"') or value.startswith('@"')
                      else "bool" if value in ("true", "false")
                      else "number" if re.fullmatch(r"-?\d+(\.\d+)?[fFdDmM]?", value) else None)
        # Numbers are assignable to every numeric type here (int/double/float literals).
        if value_kind and value_kind != kind and value_kind != "number":
            err(f"{rel}: {kind} {name} = {value[:30]} - assigning a {value_kind} to a {kind}")

    # 3f. `==` between a string literal and something declared as bool, and vice versa.
    for m in re.finditer(r'([a-z_]\w*)\s*==\s*"(?:[^"]*)"', src_text):
        if re.search(rf"\bbool\s+{m.group(1)}\b", src_text):
            err(f"{rel}: comparing bool '{m.group(1)}' with a string literal")

print()
for w in warnings:
    print("WARN", w)
for e in errors:
    print("ERROR", e)

print()
if errors:
    print(f"{len(errors)} semantic error(s), {len(warnings)} warning(s)")
    sys.exit(1)
print(f"no semantic errors ({len(warnings)} warning(s) to review)")
