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
        annotations, counts = self.counts("dir_a/multiline.ml")
        self.assertEqual(annotations, 3)
        self.assertEqual(counts, {
            "Cap.stdin": 1, "Cap.stdout": 2, "Cap.stderr": 2,
            "Cap.open_in": 1, "Cap.open_out": 1,
            "caps (alias)": 2,
        })

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
        self.assertEqual(sum(per_dir["dir_a"].cap_counts.values()), 19)

        self.assertEqual(per_dir["dir_b"].loc, 5)
        self.assertEqual(per_dir["dir_b"].annotations, 3)
        self.assertEqual(dict(per_dir["dir_b"].cap_counts),
                          {"Cap.chdir": 1, "Cap.kill": 1, "Cap.env": 1})

        self.assertEqual(total.loc, per_dir["dir_a"].loc + per_dir["dir_b"].loc)
        self.assertEqual(total.annotations, 12)
        self.assertEqual(sum(total.cap_counts.values()), 22)
        # ignored.txt must not contribute despite containing "< Cap.should_not_count; .. >"
        self.assertNotIn("Cap.should_not_count", total.cap_counts)


if __name__ == "__main__":
    unittest.main()
