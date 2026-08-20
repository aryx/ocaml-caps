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

"caps" alone (no "Cap." prefix) is treated as a capability alias
(a bundle of capabilities defined elsewhere via "type caps = < ... >"),
and is counted separately from individual "Cap.xxx" capabilities.

Usage:
    scripts/cap_stats.py [--csv] <root_dir> [<root_dir2> ...]

For each root directory, statistics are grouped by its immediate
subdirectory (e.g. lib_core, assembler, shell, ...), plus a grand
total across all roots.
"""
import argparse
import re
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
    __slots__ = ("loc", "annotations", "cap_counts")

    def __init__(self):
        self.loc = 0
        self.annotations = 0
        self.cap_counts = Counter()

    def add(self, other):
        self.loc += other.loc
        self.annotations += other.annotations
        self.cap_counts.update(other.cap_counts)


def scan_text(text: str) -> FileStats:
    stats = FileStats()
    clean = strip_noise(text)
    for block in CAP_BLOCK_RE.finditer(clean):
        block_text = block.group(0)
        stats.annotations += 1
        for m in CAP_NAME_RE.finditer(block_text):
            stats.cap_counts[f"Cap.{m.group(1)}"] += 1
        # Count bare "caps" alias occurrences, excluding the "caps" that
        # is part of "Cap.xxx" matches (CAP_NAME_RE already consumed
        # those separately; CAPS_ALIAS_RE only matches standalone words
        # so "Cap.stdout" does not also match "\bcaps\b").
        alias_count = len(CAPS_ALIAS_RE.findall(block_text))
        if alias_count:
            stats.cap_counts["caps (alias)"] += alias_count
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


def print_report(label: str, per_dir, total, csv: bool, out):
    if csv:
        w = out
        for d in sorted(per_dir):
            fs = per_dir[d]
            w.write(f"{label},{d},{fs.loc},{fs.annotations},"
                     f"{sum(fs.cap_counts.values())},{ratio_per_kloc(sum(fs.cap_counts.values()), fs.loc)}\n")
        w.write(f"{label},TOTAL,{total.loc},{total.annotations},"
                f"{sum(total.cap_counts.values())},{ratio_per_kloc(sum(total.cap_counts.values()), total.loc)}\n")
        return

    out.write(f"\n=== {label} ===\n")
    header = f"{'directory':<20} {'LOC':>8} {'annotations':>12} {'cap uses':>9} {'uses/KLOC':>10}"
    out.write(header + "\n")
    out.write("-" * len(header) + "\n")
    for d in sorted(per_dir, key=lambda d: -sum(per_dir[d].cap_counts.values())):
        fs = per_dir[d]
        uses = sum(fs.cap_counts.values())
        out.write(f"{d:<20} {fs.loc:>8} {fs.annotations:>12} {uses:>9} {ratio_per_kloc(uses, fs.loc):>10}\n")
    out.write("-" * len(header) + "\n")
    uses = sum(total.cap_counts.values())
    out.write(f"{'TOTAL':<20} {total.loc:>8} {total.annotations:>12} {uses:>9} {ratio_per_kloc(uses, total.loc):>10}\n")

    if total.cap_counts:
        out.write(f"\nCapability breakdown for {label}:\n")
        for name, count in total.cap_counts.most_common():
            out.write(f"  {name:<20} {count:>6}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roots", nargs="+", type=Path, help="root directories to scan (e.g. ~/xix)")
    parser.add_argument("--csv", action="store_true", help="emit CSV instead of a text table")
    args = parser.parse_args(argv)

    grand_per_dir = defaultdict(FileStats)
    grand_total = FileStats()

    for root in args.roots:
        root = root.expanduser().resolve()
        if not root.is_dir():
            print(f"error: {root} is not a directory", file=sys.stderr)
            return 1
        per_dir, total = collect(root)
        print_report(str(root), per_dir, total, args.csv, sys.stdout)
        for d, fs in per_dir.items():
            grand_per_dir[f"{root.name}/{d}"].add(fs)
        grand_total.add(total)

    if len(args.roots) > 1:
        print_report("GRAND TOTAL (all roots)", grand_per_dir, grand_total, args.csv, sys.stdout)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
