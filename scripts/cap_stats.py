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

"caps" alone (no "Cap." prefix) is a capability alias, a bundle of
capabilities defined via "type caps = < ... >". When that definition
is found locally in the same file, each "caps" usage is *expanded*:
its component capabilities are counted individually, folded into the
same Cap.xxx totals as direct uses. When no local definition can be
found (e.g. "type caps = Other_module.caps", or no definition at all
in that file), the use is tallied under "caps_unresolved" instead of
being silently dropped, so you can see how much of the total is
missing an expansion.

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

# A capability "item" inside a <...> block: either "Cap.<name>" or the
# bare alias identifier "caps".
CAP_ITEM = r"(?:Cap\.[A-Za-z_][A-Za-z0-9_']*|\bcaps\b)"

# One "token" allowed inside a capability block: a capability item, the
# ".." open-row marker, a ';' separator, or whitespace. Comments and
# string literals are blanked out beforehand by strip_noise(), so they
# never appear here.
_TOKEN = rf"(?:{CAP_ITEM}|\.\.|;|\s)"

# A whole "< ... >" block, required to contain at least one capability
# item somewhere inside (otherwise it's just some unrelated "<...>"
# such as a comparison or a "<>" operator).
CAP_BLOCK_RE = re.compile(
    rf"<(?=[^>]*?{CAP_ITEM}){_TOKEN}*>",
    re.DOTALL,
)

CAP_NAME_RE = re.compile(r"Cap\.([A-Za-z_][A-Za-z0-9_']*)")
CAPS_ALIAS_RE = re.compile(r"\bcaps\b")

# A local "type caps = < ... >" definition, e.g.:
#   type caps = < Cap.open_in; Cap.open_out; Cap.env >
#   type caps = <
#       Cap.stdin; Cap.stdout; ...
#     >
# Used to expand bare "caps" usages (< caps; Cap.stdout; .. >) into their
# individual components when the alias is defined in the same file. Not
# matched when the alias just re-exports another module's type, e.g.
# "type caps = Cmd_.caps" (no "<" follows) -- that case is left
# unresolved since it needs cross-file/module resolution.
TYPE_CAPS_DEF_RE = re.compile(
    rf"\btype\s+caps\s*=\s*(<(?=[^>]*?{CAP_ITEM}){_TOKEN}*>)",
    re.DOTALL,
)

UNRESOLVED_ALIAS = "caps_unresolved"

SOURCE_SUFFIXES = (".ml", ".mli")
EXCLUDED_DIR_NAMES = {"_build", ".git"}


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
    __slots__ = ("loc", "annotations", "cap_counts", "block_sizes")

    def __init__(self):
        self.loc = 0
        self.annotations = 0
        self.cap_counts = Counter()
        # Number of capability items in each individual "< ... >" block
        # (bare "caps" counts as its expanded size when resolved, else 1),
        # one entry per annotation -- used for min/max/mean/median.
        self.block_sizes = []

    def add(self, other):
        self.loc += other.loc
        self.annotations += other.annotations
        self.cap_counts.update(other.cap_counts)
        self.block_sizes.extend(other.block_sizes)


def local_caps_alias(clean_text: str):
    """Return the list of "Cap.xxx" names in this file's local
    "type caps = < ... >" definition, or None if there isn't one (e.g.
    the file has no such definition, or it's a re-export like
    "type caps = Cmd_.caps" that this text-based scanner can't resolve).
    """
    m = TYPE_CAPS_DEF_RE.search(clean_text)
    if not m:
        return None
    return [f"Cap.{n}" for n in CAP_NAME_RE.findall(m.group(1))]


def scan_text(text: str) -> FileStats:
    stats = FileStats()
    clean = strip_noise(text)
    alias = local_caps_alias(clean)
    def_block = TYPE_CAPS_DEF_RE.search(clean)
    def_span = def_block.span(1) if def_block else None

    for block in CAP_BLOCK_RE.finditer(clean):
        block_text = block.group(0)
        stats.annotations += 1
        block_size = 0
        for m in CAP_NAME_RE.finditer(block_text):
            stats.cap_counts[f"Cap.{m.group(1)}"] += 1
            block_size += 1

        # Bare "caps" alias occurrences (excluding "caps" as part of a
        # "Cap.xxx" token, which CAP_NAME_RE already handled above;
        # CAPS_ALIAS_RE only matches the standalone word). Skip the
        # definition block itself -- it doesn't reference its own alias.
        is_def_block = def_span is not None and block.span() == def_span
        alias_count = 0 if is_def_block else len(CAPS_ALIAS_RE.findall(block_text))
        if alias_count:
            if alias is not None:
                # Expand: each "caps" use pulls in every component
                # capability of the locally-defined alias.
                for _ in range(alias_count):
                    for name in alias:
                        stats.cap_counts[name] += 1
                    block_size += len(alias)
            else:
                # No local "type caps = < ... >" found in this file -- we
                # can't tell what "caps" expands to, so tally it
                # separately rather than silently under-counting, and
                # conservatively count it as a single item for the
                # per-annotation size distribution.
                stats.cap_counts[UNRESOLVED_ALIAS] += alias_count
                block_size += alias_count
        stats.block_sizes.append(block_size)
    return stats


def scan_file(path: Path) -> FileStats:
    text = path.read_text(errors="replace")
    stats = scan_text(text)
    stats.loc = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return stats


def iter_source_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.suffix in SOURCE_SUFFIXES:
            yield path


def top_level_bucket(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    return rel.parts[0] if len(rel.parts) > 1 else "(root)"


def collect(root: Path):
    """Return (per_directory: dict[str, FileStats], total: FileStats)."""
    per_dir = defaultdict(FileStats)
    total = FileStats()
    for f in iter_source_files(root):
        fs = scan_file(f)
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
    return [name, str(fs.loc), str(fs.annotations), str(uses),
            ratio_per_kloc(uses, fs.loc), mn, mx, mean, median]


TABLE_COLUMNS = ["directory", "LOC", "annotations", "cap uses", "uses/KLOC", "min", "max", "mean", "median"]


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
        widths = [20, 8, 12, 9, 10, 4, 4, 6, 7]
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
    cols = ["project", "LOC", "annotations", "cap uses", "uses/KLOC", "min", "max", "mean", "median"]
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
    widths = [20, 8, 12, 9, 10, 4, 4, 6, 7]
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
    parser.set_defaults(fmt="text")
    args = parser.parse_args(argv)

    roots_totals = []

    for root_arg in args.roots:
        label = root_arg.expanduser().name  # as typed, before resolving symlinks
        root = root_arg.expanduser().resolve()
        if not root.is_dir():
            print(f"error: {root} is not a directory", file=sys.stderr)
            return 1
        per_dir, total = collect(root)
        if not (args.summary_only and len(args.roots) > 1):
            print_report(str(root), per_dir, total, args.fmt, sys.stdout)
        roots_totals.append((label, total))

    if len(args.roots) > 1:
        print_summary(roots_totals, args.fmt, sys.stdout)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
