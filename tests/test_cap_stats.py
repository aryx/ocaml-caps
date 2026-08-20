#!/usr/bin/env python3
"""Unit tests for scripts/cap_stats.py, run against tests/fixtures/.

Run with:  python3 tests/test_cap_stats.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import cap_stats  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CROSSFILE_FIXTURES = Path(__file__).resolve().parent / "fixtures_crossfile"
SUBMODULE_FIXTURES = Path(__file__).resolve().parent / "fixtures_submodule"


class TestScanFile(unittest.TestCase):
    def counts(self, relpath):
        fs = cap_stats.scan_file(FIXTURES / relpath)
        return fs.annotations, dict(fs.cap_counts)

    def sizes(self, relpath):
        return cap_stats.scan_file(FIXTURES / relpath).block_sizes

    def test_single_line_ml(self):
        annotations, counts = self.counts("dir_a/single_line.ml")
        self.assertEqual(annotations, 2)
        self.assertEqual(counts, {
            "Cap.open_in": 1, "Cap.fork": 1, "Cap.exec": 1, "Cap.wait": 1,
        })

    def test_single_line_mli(self):
        annotations, counts = self.counts("dir_a/single_line.mli")
        self.assertEqual(annotations, 2)
        self.assertEqual(counts, {
            "Cap.open_in": 1, "Cap.fork": 1, "Cap.exec": 1, "Cap.wait": 1,
        })

    def test_multiline_with_alias_and_inline_comments(self):
        # "type caps = < Cap.stdin; Cap.stdout; Cap.stderr; Cap.open_in;
        # Cap.open_out >" is defined locally, so both "caps" usages
        # below it get expanded into these five components each, on top
        # of the definition's own literal occurrence and the explicit
        # Cap.stdout/Cap.stderr in the "main" signature.
        annotations, counts = self.counts("dir_a/multiline.ml")
        self.assertEqual(annotations, 3)
        self.assertEqual(counts, {
            "Cap.stdin": 3, "Cap.stdout": 4, "Cap.stderr": 4,
            "Cap.open_in": 3, "Cap.open_out": 3,
        })
        # def block (5 items), restrict_caps (expands to 5), main
        # (expands to 5 + 2 explicit Cap.stdout/Cap.stderr = 7)
        self.assertEqual(self.sizes("dir_a/multiline.ml"), [5, 5, 7])

    def test_unresolved_alias_is_not_expanded(self):
        fs = cap_stats.scan_file(FIXTURES / "dir_b/unresolved_alias.ml")
        self.assertEqual(fs.annotations, 1)
        self.assertEqual(dict(fs.cap_counts), {"Cap.env": 1, "caps_unresolved": 1})
        # unresolved "caps" is conservatively counted as 1 item + Cap.env
        self.assertEqual(fs.block_sizes, [2])
        # the one annotation here is unresolved
        self.assertEqual(fs.unresolved_annotations, 1)

    def test_decoys_are_not_counted(self):
        # includes non-capability object types in the ":>" / "(" / "*"
        # positions the broader anchor now covers (hashtable-style
        # interfaces, GUI widget types, plain coercions) -- none of them
        # contain a Cap.xxx/alias token, so none should be counted.
        annotations, counts = self.counts("dir_a/decoys.ml")
        self.assertEqual(annotations, 1)
        self.assertEqual(counts, {"Cap.env": 1})

    def test_nested_comment_is_stripped(self):
        annotations, counts = self.counts("dir_a/nested_comment.ml")
        self.assertEqual(annotations, 1)
        self.assertEqual(counts, {"Cap.readdir": 1})

    def test_other_directory(self):
        annotations, counts = self.counts("dir_b/other.ml")
        self.assertEqual(annotations, 3)
        self.assertEqual(counts, {"Cap.chdir": 1, "Cap.kill": 1, "Cap.env": 1})


class TestCollect(unittest.TestCase):
    def test_non_source_files_ignored_and_directories_aggregate(self):
        per_dir, total = cap_stats.collect(FIXTURES)

        self.assertEqual(set(per_dir), {"dir_a", "dir_b"})

        self.assertEqual(per_dir["dir_a"].loc, 21 + 16 + 3 + 10 + 2)
        self.assertEqual(per_dir["dir_a"].annotations, 9)
        self.assertEqual(sum(per_dir["dir_a"].cap_counts.values()), 27)

        self.assertEqual(per_dir["dir_b"].loc, 5 + 4)
        self.assertEqual(per_dir["dir_b"].annotations, 4)
        self.assertEqual(dict(per_dir["dir_b"].cap_counts), {
            "Cap.chdir": 1, "Cap.kill": 1, "Cap.env": 2, "caps_unresolved": 1,
        })

        self.assertEqual(total.loc, per_dir["dir_a"].loc + per_dir["dir_b"].loc)
        self.assertEqual(total.annotations, 13)
        self.assertEqual(sum(total.cap_counts.values()), 32)
        # ignored.txt must not contribute despite containing "< Cap.should_not_count; .. >"
        self.assertNotIn("Cap.should_not_count", total.cap_counts)
        # one block_sizes entry per annotation, summing to total cap uses
        self.assertEqual(len(total.block_sizes), total.annotations)
        self.assertEqual(sum(total.block_sizes), sum(total.cap_counts.values()))


class TestCrossFileResolution(unittest.TestCase):
    """Aliases resolved using tree-wide context from collect(), which a
    standalone scan_file() call cannot see."""

    def test_qualified_alias_and_coercion(self):
        per_dir, total = cap_stats.collect(CROSSFILE_FIXTURES)

        # "Shell.caps" (used in scheduler.ml) resolves against Shell.ml's
        # own "type caps = < Cap.exec; Cap.fork; Cap.wait >"; a bare
        # ":>" coercion "(caps :> < Cap.exec >)" is also picked up.
        self.assertEqual(total.annotations, 9)
        self.assertEqual(total.unresolved_annotations, 0)
        self.assertEqual(dict(total.cap_counts), {
            "Cap.exec": 5, "Cap.fork": 4, "Cap.wait": 4, "Cap.env": 1,
            "Cap.stdout": 2, "Cap.chdir": 2, "Cap.draw": 2, "Cap.keyboard": 2,
        })
        self.assertNotIn("caps_unresolved", total.cap_counts)

    def test_one_hop_reexport_chain(self):
        # "type caps = Cmd_.caps" (a re-export, no "<" of its own) must
        # resolve one hop to Cmd_'s own "type caps = < ... >" definition.
        raw_defs = {
            ("Main", "caps"): ("ref", "Cmd_", "caps"),
            ("Cmd_", "caps"): ["Cap.stdout", "Cap.chdir"],
        }
        index = cap_stats.resolve_alias_index(raw_defs)
        self.assertEqual(index[("Main", "caps")], ["Cap.stdout", "Cap.chdir"])

    def test_unresolvable_ref_and_cycle_are_none_not_a_crash(self):
        raw_defs = {
            ("A", "caps"): ("ref", "B", "caps"),  # B.caps is never defined
            ("C", "caps"): ("ref", "D", "caps"),
            ("D", "caps"): ("ref", "C", "caps"),  # C <-> D cycle
        }
        index = cap_stats.resolve_alias_index(raw_defs)
        self.assertIsNone(index[("A", "caps")])
        self.assertIsNone(index[("C", "caps")])
        self.assertIsNone(index[("D", "caps")])

    def test_open_brings_alias_into_scope(self):
        # frame.ml has "open Efuns" and uses the bare "frame_caps" alias
        # defined in efuns.ml, not frame.ml itself.
        per_dir, total = cap_stats.collect(CROSSFILE_FIXTURES)
        self.assertEqual(total.cap_counts["Cap.draw"], 2)  # efuns.ml's own def + frame.ml's use
        self.assertEqual(total.cap_counts["Cap.keyboard"], 2)


class TestSubmodules(unittest.TestCase):
    def test_submodule_skipped_by_default(self):
        per_dir, total = cap_stats.collect(SUBMODULE_FIXTURES)
        self.assertEqual(dict(total.cap_counts), {"Cap.chdir": 1})
        self.assertNotIn("vendored_lib", per_dir)

    def test_submodule_included_when_asked(self):
        per_dir, total = cap_stats.collect(SUBMODULE_FIXTURES, skip_submodules=False)
        self.assertEqual(dict(total.cap_counts), {"Cap.chdir": 1, "Cap.network": 1, "Cap.exec": 1})
        self.assertIn("vendored_lib", per_dir)

    def test_submodule_dirs_parses_gitmodules(self):
        dirs = cap_stats.submodule_dirs(SUBMODULE_FIXTURES)
        self.assertEqual(dirs, {SUBMODULE_FIXTURES / "vendored_lib"})

    def test_no_gitmodules_file_means_no_exclusions(self):
        self.assertEqual(cap_stats.submodule_dirs(FIXTURES), set())


if __name__ == "__main__":
    unittest.main()
