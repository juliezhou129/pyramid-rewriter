"""Run with: python3 -m unittest discover -s evals -p 'test_check_length.py'."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_length.py"
SPEC = importlib.util.spec_from_file_location("check_length", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CheckLengthTests(unittest.TestCase):
    def test_inclusive_bounds(self):
        for length, valid, missing, excess in [
            (599, False, 1, 0), (600, True, 0, 0),
            (800, True, 0, 0), (801, False, 0, 1),
        ]:
            with self.subTest(length=length):
                result = MODULE.check_length("中" * length, 600, 800)
                self.assertEqual(
                    (result["count"], result["within_range"], result["missing"], result["excess"]),
                    (length, valid, missing, excess),
                )

    def test_unicode_and_whitespace(self):
        self.assertEqual(MODULE.check_length("中 文\tA\n12，。🙂\u3000")["count"], 8)

    def test_explicit_punctuation_exclusion(self):
        self.assertEqual(MODULE.check_length("中文，A12。", exclude_punctuation=True)["count"], 5)

    def test_one_sided_bounds_and_zero(self):
        self.assertTrue(MODULE.check_length("", 0)["within_range"])
        self.assertFalse(MODULE.check_length("多", maximum=0)["within_range"])
        self.assertTrue(MODULE.check_length("中文", minimum=1)["within_range"])

    def test_invalid_bounds(self):
        for lower, upper in [(-1, None), (None, -1), (800, 600)]:
            with self.subTest(bounds=(lower, upper)):
                with self.assertRaises(ValueError):
                    MODULE.check_length("", lower, upper)

    def test_cli_stdin_exit_codes_and_file_equivalence(self):
        command = [sys.executable, str(SCRIPT), "--min", "2", "--max", "3"]
        valid = subprocess.run(command, input="中文", capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0)
        result = json.loads(valid.stdout)
        self.assertEqual(result["count"], 2)
        invalid = subprocess.run(command, input="中", capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(json.loads(invalid.stdout)["missing"], 1)
        bad_args = subprocess.run(command + ["--min", "4"], input="中文", capture_output=True, text=True)
        self.assertEqual(bad_args.returncode, 2)
        with tempfile.TemporaryDirectory() as directory:
            body = Path(directory) / "body.txt"
            body.write_text("中文", encoding="utf-8")
            from_file = subprocess.run(command + [str(body)], capture_output=True, text=True)
            self.assertEqual(from_file.returncode, 0)
            self.assertEqual(json.loads(from_file.stdout), result)


if __name__ == "__main__":
    unittest.main()
