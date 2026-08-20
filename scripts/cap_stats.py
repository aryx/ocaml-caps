#!/usr/bin/env python3
"""
cap_stats.py - count capability usage (Cap.xxx) in OCaml code.

This is a *lightweight* text-based scanner, not a real OCaml parser.
It looks for object-type annotations of the form:

    < Cap.open_in; .. >
    < Cap.fork; Cap.exec; Cap.wait; ..>
    < caps; Cap.stdout; Cap.stderr; .. >

These can span multiple lines and may contain comments, e.g.:

    type caps = <
        Cap.stdin; Cap.stdout; Cap.stderr;
        Cap.open_in; (* for 'r' *)
        Cap.open_out; (* for 'w' *)
      >

A bare "caps" (or "xxx_caps") identifier -- with no "Cap." prefix, and
optionally module-qualified like "Shell.caps" or "Efuns.frame_caps" --
is a capability *alias*: a bundle of capabilities defined once via
"type caps = < ... >" and reused across many signatures. Aliases are
resolved across the whole scanned tree (not just the current file), so
"Shell.caps" used in Eval.mli gets expanded using the definition found
in Shell.ml, and a re-export like "type caps = Cmd_.caps" is followed
one hop to Cmd_'s own definition. Each resolved alias use is expanded:
its component capabilities are counted individually, folded into the
same Cap.xxx totals as direct uses. When an alias can't be resolved
anywhere in the tree, the use is tallied under "caps_unresolved"
instead of being silently dropped, so you can see how much of the
total is missing an expansion.

Usage:
    scripts/cap_stats.py [--csv] <root_dir> [<root_dir2> ...]

For each root directory, statistics are grouped by its immediate
subdirectory (e.g. lib_core, assembler, shell, ...), plus a grand
total across all roots.
"""
import argparse
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

CAP_NAME_RE = re.compile(r"Cap\.([A-Za-z_][A-Za-z0-9_']*)")

# A capability-alias identifier: exactly "caps", or any identifier ending
# in "_caps" (e.g. "frame_caps"), optionally module-qualified
# ("Shell.caps", "Efuns.frame_caps"). Matches as a bare word only --
# never as a substring of a longer identifier.
ALIAS_NAME = r"(?:caps|[A-Za-z_][A-Za-z0-9_']*_caps)"
ALIAS_NAME_RE = re.compile(ALIAS_NAME)
ALIAS_TOKEN_RE = re.compile(rf"\b(?:([A-Z][A-Za-z0-9_']*)\.)?({ALIAS_NAME})\b")

# Where a "< ... >" capability annotation can start: right after a type
# annotation ':' (or a ':>' coercion), a function-type arrow '->'
# (curried capability arguments), a type alias '=', an opening '(' or
# tuple '*' (a parenthesized/tupled type component, e.g.
# "(< Cap.a > -> ...)" or "(float * < Cap.a >)"). This is deliberately
# permissive -- false starts just fail to find a "<" immediately after
# and are skipped; ones that do find a "<" but turn out to wrap ordinary
# (non-capability) OCaml object types are filtered out afterwards
# because they contain no Cap.xxx/alias token.
BLOCK_ANCHOR_RE = re.compile(r"(?::>?|->|=|\(|\*)\s*(<)")

# Matches when a "< ... >" block found via BLOCK_ANCHOR_RE is really the
# RHS of "type NAME = < ... >", to register NAME in the alias index.
TYPE_DEF_BEFORE_RE = re.compile(r"\btype\s+([A-Za-z_][A-Za-z0-9_']*)\s*=\s*$")

# A re-export alias definition with no "<" of its own, e.g.
# "type caps = Cmd_.caps" or "type caps = Session.caps". Resolved by
# following into the referenced module's own alias definition.
DEF_REF_RE = re.compile(rf"\btype\s+({ALIAS_NAME})\s*=\s*(?:([A-Z][A-Za-z0-9_']*)\.)?({ALIAS_NAME})\b")

# "open Module" -- a bare (unqualified) alias reference can also resolve
# against an opened module's alias, e.g. "open Efuns" bringing
# "frame_caps" into unqualified scope from Efuns.ml's own definition.
OPEN_RE = re.compile(r"^\s*open\s+([A-Z][A-Za-z0-9_.]*)", re.MULTILINE)

UNRESOLVED_ALIAS = "caps_unresolved"

SOURCE_SUFFIXES = (".ml", ".mli")
EXCLUDED_DIR_NAMES = {"_build", ".git"}

GITMODULES_PATH_RE = re.compile(r"^\s*path\s*=\s*(.+?)\s*$", re.MULTILINE)


def submodule_dirs(root: Path) -> set:
    """Top-level directories declared as git submodules in root/.gitmodules
    (e.g. shared libraries like semgrep-pfff-libs/semgrep-pfff-langs,
    vendored into several sibling projects) -- excluded by default so
    stats reflect a project's own code, not code it merely embeds."""
    gitmodules = root / ".gitmodules"
    if not gitmodules.is_file():
        return set()
    text = gitmodules.read_text(errors="replace")
    return {root / p for p in GITMODULES_PATH_RE.findall(text)}


def strip_noise(text: str) -> str:
    """Blank out comments and string literals (replacing their contents
    with spaces, preserving newlines) so they can never create false
    capability-block matches, e.g. a docstring mentioning "< Cap.foo >"
    as an example, or a string literal like "<initcmd>".

    Handles nested OCaml comments and escaped quotes in strings. This is
    a small lexer-ish pass, not a real OCaml lexer (it doesn't special
    case char literals like '"'), which is fine for the code this tool
    is meant to scan.
    """
    out = []
    i, n = 0, len(text)
    depth = 0  # comment nesting depth
    while i < n:
        if depth == 0 and text[i] == '"':
            out.append(" ")
            i += 1
            while i < n:
                if text[i] == "\\" and i + 1 < n:
                    out.append("  " if text[i + 1] != "\n" else " \n")
                    i += 2
                    continue
                if text[i] == '"':
                    out.append(" ")
                    i += 1
                    break
                out.append("\n" if text[i] == "\n" else " ")
                i += 1
            continue
        if text[i:i + 2] == "(*":
            depth += 1
            out.append("  ")
            i += 2
            continue
        if depth > 0 and text[i:i + 2] == "*)":
            depth -= 1
            out.append("  ")
            i += 2
            continue
        if depth > 0:
            out.append("\n" if text[i] == "\n" else " ")
            i += 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


class FileStats:
    __slots__ = ("loc", "annotations", "unresolved_annotations", "cap_counts", "block_sizes")

    def __init__(self):
        self.loc = 0
        # Total number of "< ... >" capability annotations seen, whether
        # or not every "caps" alias inside them could be resolved -- this
        # is the raw count of capability-related type annotations in
        # function signatures (and alias definitions).
        self.annotations = 0
        # Of those, how many contain at least one "caps" alias use that
        # could NOT be expanded locally (see UNRESOLVED_ALIAS below).
        self.unresolved_annotations = 0
        self.cap_counts = Counter()
        # Number of capability items in each individual "< ... >" block
        # (bare "caps" counts as its expanded size when resolved, else 1),
        # one entry per annotation -- used for min/max/mean/median.
        self.block_sizes = []

    def add(self, other):
        self.loc += other.loc
        self.annotations += other.annotations
        self.unresolved_annotations += other.unresolved_annotations
        self.cap_counts.update(other.cap_counts)
        self.block_sizes.extend(other.block_sizes)


def module_name_of(path: Path) -> str:
    """The OCaml module name a file compiles to: its stem with the first
    letter capitalized (e.g. "cmd_.ml" -> "Cmd_", "Shell.ml" -> "Shell")."""
    stem = path.stem
    return stem[:1].upper() + stem[1:] if stem else stem


def find_annotation_spans(clean: str):
    """Find every "< ... >" span anchored at a type position (after ':',
    '->', or '='), terminated at the first '>' not part of an arrow
    "->". Includes plain OCaml object types that have nothing to do with
    capabilities -- callers filter those out based on content."""
    spans = []
    seen_starts = set()
    n = len(clean)
    for m in BLOCK_ANCHOR_RE.finditer(clean):
        start = m.start(1)
        if start in seen_starts:
            continue
        seen_starts.add(start)
        i = start + 1
        while i < n:
            if clean[i] == ">" and clean[i - 1] != "-":
                spans.append((start, i + 1))
                break
            i += 1
    return spans


def file_alias_defs(clean: str, module: str, spans):
    """Alias definitions found in one file, keyed by (module, name).
    Value is either a component list (direct "type NAME = < ... >") or
    ("ref", other_module_or_None, other_name) for a re-export like
    "type NAME = Other.name"."""
    defs = {}
    for start, end in spans:
        m = TYPE_DEF_BEFORE_RE.search(clean, 0, start)
        if not m or not ALIAS_NAME_RE.fullmatch(m.group(1)):
            continue
        defs.setdefault((module, m.group(1)), [f"Cap.{n}" for n in CAP_NAME_RE.findall(clean[start:end])])
    for m in DEF_REF_RE.finditer(clean):
        key = (module, m.group(1))
        if key not in defs:
            defs[key] = ("ref", m.group(2), m.group(3))
    return defs


def resolve_alias_index(raw_defs: dict) -> dict:
    """Resolve re-export refs (following at most a few hops, guarding
    against cycles) into flat component lists."""
    resolved = {}

    def resolve(key, depth=0):
        if key in resolved:
            return resolved[key]
        resolved[key] = None  # cycle guard
        if depth > 5 or key not in raw_defs:
            return None
        val = raw_defs[key]
        if isinstance(val, list):
            result = val
        else:
            _, other_module, other_name = val
            result = resolve((other_module or key[0], other_name), depth + 1)
        resolved[key] = result
        return result

    for key in list(raw_defs):
        resolve(key)
    return resolved


def open_modules_of(clean: str):
    """Modules brought into unqualified scope via "open Module" -- a bare
    alias reference can resolve against one of these too, e.g. "open
    Efuns" bringing "frame_caps" into scope from Efuns.ml's own
    definition. For a dotted open like "open A.B" we try both the full
    path and its last component, since our alias index is keyed by
    simple filename-derived module names."""
    modules = []
    for m in OPEN_RE.finditer(clean):
        path = m.group(1)
        modules.append(path)
        if "." in path:
            modules.append(path.rsplit(".", 1)[1])
    return modules


def scan_clean_text(clean: str, own_module: str, alias_index: dict, spans=None, open_modules=()) -> FileStats:
    stats = FileStats()
    search_modules = [own_module, *open_modules]
    for start, end in (spans if spans is not None else find_annotation_spans(clean)):
        block_text = clean[start:end]
        cap_names = [f"Cap.{n}" for n in CAP_NAME_RE.findall(block_text)]
        alias_uses = [(q, n) for q, n in ALIAS_TOKEN_RE.findall(block_text) if q != "Cap"]
        if not cap_names and not alias_uses:
            continue  # an ordinary (non-capability) object type -- ignore
        stats.annotations += 1
        block_size = len(cap_names)
        stats.cap_counts.update(cap_names)
        block_unresolved = False
        for qualifier, name in alias_uses:
            candidates = [qualifier] if qualifier else search_modules
            components = next((c for c in (alias_index.get((m, name)) for m in candidates) if c is not None), None)
            if components is not None:
                stats.cap_counts.update(components)
                block_size += len(components)
            else:
                stats.cap_counts[UNRESOLVED_ALIAS] += 1
                block_unresolved = True
                block_size += 1
        if block_unresolved:
            stats.unresolved_annotations += 1
        stats.block_sizes.append(block_size)
    return stats


def scan_file(path: Path) -> FileStats:
    """Scan a single file in isolation (its own module's aliases and its
    own "open"s only -- no cross-file alias definitions). Used by tests
    and for one-off lookups."""
    text = path.read_text(errors="replace")
    clean = strip_noise(text)
    module = module_name_of(path)
    spans = find_annotation_spans(clean)
    alias_index = resolve_alias_index(file_alias_defs(clean, module, spans))
    stats = scan_clean_text(clean, module, alias_index, spans, open_modules_of(clean))
    stats.loc = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return stats


def iter_source_files(root: Path, skip_submodules: bool = True):
    excluded_dirs = submodule_dirs(root) if skip_submodules else set()
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if excluded_dirs and any(sub == path or sub in path.parents for sub in excluded_dirs):
            continue
        if path.suffix in SOURCE_SUFFIXES:
            yield path


def top_level_bucket(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    return rel.parts[0] if len(rel.parts) > 1 else "(root)"


def collect(root: Path, skip_submodules: bool = True):
    """Return (per_directory: dict[str, FileStats], total: FileStats).

    Two passes: first build a tree-wide alias index (so e.g. "Shell.caps"
    used in one file resolves against "type caps = < ... >" defined in
    Shell.ml), then scan every file against that shared index. Git
    submodules (per .gitmodules) are skipped by default -- a project's
    stats should reflect its own code, not code it merely vendors.
    """
    files = {}  # path -> (text, clean, module, spans)
    raw_defs = {}
    for f in iter_source_files(root, skip_submodules):
        text = f.read_text(errors="replace")
        clean = strip_noise(text)
        module = module_name_of(f)
        spans = find_annotation_spans(clean)
        files[f] = (text, clean, module, spans)
        raw_defs.update(file_alias_defs(clean, module, spans))

    alias_index = resolve_alias_index(raw_defs)

    per_dir = defaultdict(FileStats)
    total = FileStats()
    for f, (text, clean, module, spans) in files.items():
        fs = scan_clean_text(clean, module, alias_index, spans, open_modules_of(clean))
        fs.loc = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        per_dir[top_level_bucket(root, f)].add(fs)
        total.add(fs)
    return per_dir, total


def ratio_per_kloc(count: int, loc: int) -> str:
    if loc == 0:
        return "n/a"
    return f"{count * 1000 / loc:.2f}"


def size_stats(block_sizes):
    """(min, max, mean, median) capability items per annotation, as
    display strings; "n/a" for all four when there are no annotations."""
    if not block_sizes:
        return "n/a", "n/a", "n/a", "n/a"
    return (
        str(min(block_sizes)),
        str(max(block_sizes)),
        f"{statistics.mean(block_sizes):.2f}",
        f"{statistics.median(block_sizes):.2f}",
    )


def row_fields(name: str, fs: "FileStats"):
    uses = sum(fs.cap_counts.values())
    mn, mx, mean, median = size_stats(fs.block_sizes)
    return [name, str(fs.loc), str(fs.annotations), str(fs.unresolved_annotations), str(uses),
            ratio_per_kloc(uses, fs.loc), mn, mx, mean, median]


# "annotations" = total "< ... >" capability annotations found, resolved
# or not. "unresolved" = of those, how many contain a "caps" alias use
# this scanner couldn't expand (see UNRESOLVED_ALIAS).
TABLE_COLUMNS = ["directory", "LOC", "annotations", "unresolved", "cap uses", "uses/KLOC", "min", "max", "mean", "median"]


def print_report(label: str, per_dir, total, fmt: str, out):
    rows = [row_fields(d, per_dir[d]) for d in sorted(per_dir, key=lambda d: -sum(per_dir[d].cap_counts.values()))]
    rows.append(row_fields("TOTAL", total))

    if fmt == "csv":
        out.write("label," + ",".join(c.lower().replace(" ", "_").replace("/", "_per_") for c in TABLE_COLUMNS) + "\n")
        for row in rows:
            out.write(f"{label}," + ",".join(row) + "\n")
        return

    if fmt == "markdown":
        out.write(f"\n**{label}**\n\n")
        out.write("| " + " | ".join(TABLE_COLUMNS) + " |\n")
        out.write("|" + "|".join("---" if i == 0 else "---:" for i in range(len(TABLE_COLUMNS))) + "|\n")
        for row in rows:
            out.write("| " + " | ".join(row) + " |\n")
        out.write("\n(min/max/mean/median = capability items per individual `< ... >` annotation)\n")
    else:
        out.write(f"\n=== {label} ===\n")
        widths = [20, 8, 12, 10, 9, 10, 4, 4, 6, 7]
        header = " ".join(c.rjust(w) if i else c.ljust(w) for i, (c, w) in enumerate(zip(TABLE_COLUMNS, widths)))
        out.write(header + "\n")
        out.write("-" * len(header) + "\n")
        for row in rows:
            out.write(" ".join(v.rjust(w) if i else v.ljust(w) for i, (v, w) in enumerate(zip(row, widths))) + "\n")
        out.write("-" * len(header) + "\n")
        out.write("(min/max/mean/median = capability items per individual < ... > annotation)\n")

    if total.cap_counts:
        out.write(f"\nCapability breakdown for {label}:\n")
        for name, count in total.cap_counts.most_common():
            out.write(f"  {name:<20} {count:>6}\n")


def print_summary(roots_totals, fmt: str, out):
    """One row per project (root), for cross-project comparison tables."""
    cols = ["project"] + TABLE_COLUMNS[1:]
    rows = [row_fields(name, fs) for name, fs in roots_totals]

    if fmt == "csv":
        out.write(",".join(c.lower().replace(" ", "_").replace("/", "_per_") for c in cols) + "\n")
        for row in rows:
            out.write(",".join(row) + "\n")
        return

    if fmt == "markdown":
        out.write("\n**Capability usage by project**\n\n")
        out.write("| " + " | ".join(cols) + " |\n")
        out.write("|" + "|".join("---" if i == 0 else "---:" for i in range(len(cols))) + "|\n")
        for row in rows:
            out.write("| " + " | ".join(row) + " |\n")
        return

    out.write("\n=== Capability usage by project ===\n")
    widths = [20, 8, 12, 10, 9, 10, 4, 4, 6, 7]
    header = " ".join(c.rjust(w) if i else c.ljust(w) for i, (c, w) in enumerate(zip(cols, widths)))
    out.write(header + "\n")
    out.write("-" * len(header) + "\n")
    for row in rows:
        out.write(" ".join(v.rjust(w) if i else v.ljust(w) for i, (v, w) in enumerate(zip(row, widths))) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roots", nargs="+", type=Path, help="root directories to scan (e.g. ~/xix)")
    fmt_group = parser.add_mutually_exclusive_group()
    fmt_group.add_argument("--csv", action="store_const", dest="fmt", const="csv", help="emit CSV instead of a text table")
    fmt_group.add_argument("--markdown", action="store_const", dest="fmt", const="markdown",
                            help="emit a pandoc-style pipe table (handy for slides/docs)")
    parser.add_argument("--summary-only", action="store_true",
                         help="with multiple roots, skip the per-directory breakdowns and print only "
                              "the one-row-per-project comparison table")
    parser.add_argument("--include-submodules", action="store_true",
                         help="also scan directories declared as git submodules in .gitmodules "
                              "(skipped by default, e.g. shared libs vendored into several projects)")
    parser.set_defaults(fmt="text")
    args = parser.parse_args(argv)

    roots_totals = []

    for root_arg in args.roots:
        label = root_arg.expanduser().name  # as typed, before resolving symlinks
        root = root_arg.expanduser().resolve()
        if not root.is_dir():
            print(f"error: {root} is not a directory", file=sys.stderr)
            return 1
        per_dir, total = collect(root, skip_submodules=not args.include_submodules)
        if not (args.summary_only and len(args.roots) > 1):
            print_report(str(root), per_dir, total, args.fmt, sys.stdout)
        roots_totals.append((label, total))

    if len(args.roots) > 1:
        print_summary(roots_totals, args.fmt, sys.stdout)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
