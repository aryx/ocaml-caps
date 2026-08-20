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
        annotations, counts = self.counts("dir_b/unresolved_alias.ml")
        self.assertEqual(annotations, 1)
        self.assertEqual(counts, {"Cap.env": 1, "caps_unresolved": 1})
        # unresolved "caps" is conservatively counted as 1 item + Cap.env
        self.assertEqual(self.sizes("dir_b/unresolved_alias.ml"), [2])

    def test_decoys_are_not_counted(self):
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

        self.assertEqual(per_dir["dir_a"].loc, 13 + 16 + 3 + 10 + 2)
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


if __name__ == "__main__":
    unittest.main()
