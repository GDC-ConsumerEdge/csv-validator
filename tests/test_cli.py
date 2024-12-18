###############################################################################
# Copyright 2024 Google, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
import pathlib
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from unittest import TestCase


@dataclass
class ExecResult:
    process: subprocess.Popen
    stdout: str
    stderr: str
    tempdir: tempfile.TemporaryDirectory
    outfile: pathlib.Path

    def cleanup(self):
        self.tempdir.cleanup()


def exec_validator(sot, model=None, output_dir=None):
    py = shutil.which('python3')
    args = "-m csv_validator -v ".split()
    mod = ["-m", model] if model else []
    t, outfile = None, None
    if output_dir is None:
        t = tempfile.TemporaryDirectory()
    outfile = f"{t.name}/output.csv"
    out = ["-o", outfile]
    p = subprocess.Popen(
        [py, *args, *mod, *out, sot],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True)
    stdout, stderr = p.communicate()
    return ExecResult(
        process=p,
        stdout=stdout,
        stderr=stderr,
        tempdir=t,
        outfile=pathlib.Path(outfile))


class TestCLI(TestCase):
    def test_empty_sot(self):
        r = exec_validator('sources_of_truth/empty.csv')

        self.assertEqual(1, r.process.returncode)
        self.assertIn("Missing CSV field names", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_sot_invalid_header(self):
        r = exec_validator('sources_of_truth/header_invalid.csv')

        self.assertEqual(255, r.process.returncode, "wrong exit code")
        found = re.findall("^ERROR", r.stdout, flags=re.MULTILINE)
        self.assertEqual(3, len(found))
        self.assertIn("CSV is invalid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_sot_invalid_bytes(self):
        r = exec_validator('sources_of_truth/very_invalid.csv')

        self.assertEqual(r.process.returncode, 1, "wrong exit code")
        self.assertIn("Unicode decoding issues", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_sot_dupes(self):
        r = exec_validator('sources_of_truth/dupes_invalid.csv')

        self.assertEqual(255, r.process.returncode, "wrong exit code")
        found = re.findall("^ERROR", r.stdout, flags=re.MULTILINE)
        self.assertEqual(2, len(found), "mismatched number of dupes")
        self.assertIn("CSV is invalid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_sot_dupes_long(self):
        r = exec_validator('sources_of_truth/dupes_long_invalid.csv')

        self.assertEqual(255, r.process.returncode, "wrong exit code")
        dupes = re.findall("^ERROR.*not unique", r.stdout, flags=re.MULTILINE)
        self.assertEqual(50, len(dupes), "mismatched number of dupes")
        self.assertIn("CSV is invalid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_example_valid(self):
        r = exec_validator('sources_of_truth/example/valid.csv',
                           'models/example_model.py')

        self.assertEqual(0, r.process.returncode, "wrong exit code")
        self.assertIn("CSV is valid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertTrue(r.outfile.exists())
        with open(r.outfile) as f:
            self.assertTrue(f.readlines())

        r.cleanup()

    def test_example_invalid(self):
        r = exec_validator('sources_of_truth/example/invalid.csv',
                           'models/example_model.py')

        self.assertEqual(255, r.process.returncode, "wrong exit code")
        found = re.findall("^ERROR", r.stdout, flags=re.MULTILINE)
        self.assertEqual(42, len(found))
        self.assertIn("CSV is invalid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_bad_model_empty(self):
        r = exec_validator('sources_of_truth/example/valid.csv',
                           'models/invalid/invalid_model_missing.py')

        self.assertEqual(1, r.process.returncode, "wrong exit code")
        found = re.findall(r'^ERROR\s+Error accessing "SourceOfTruthModel" from loaded module', r.stdout, flags=re.MULTILINE)
        self.assertEqual(1, len(found))
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_bad_model_not_a_class(self):
        r = exec_validator('sources_of_truth/example/valid.csv',
                           'models/invalid/invalid_model_missing.py')

        self.assertEqual(1, r.process.returncode, "wrong exit code")
        found = re.findall(r'^ERROR\s+Error accessing "SourceOfTruthModel" from loaded module', r.stdout, flags=re.MULTILINE)
        self.assertEqual(1, len(found))
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_clus_reg_valid(self):
        r = exec_validator(
            'sources_of_truth/cluster_registry/cluster_reg_sot_valid.csv',
            'models/cluster_registry.py')

        self.assertEqual(0, r.process.returncode, "wrong exit code")
        self.assertIn("CSV is valid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertTrue(r.outfile.exists())
        with open(r.outfile) as f:
            self.assertTrue(f.readlines())

        r.cleanup()

    def test_clus_reg_invalid(self):
        r = exec_validator('sources_of_truth/cluster_registry/cluster_reg_sot_invalid.csv',
                           'models/cluster_registry.py')

        self.assertEqual(255, r.process.returncode, "wrong exit code")
        found = re.findall("^ERROR", r.stdout, flags=re.MULTILINE)
        self.assertEqual(2, len(found))
        self.assertIn("CSV is invalid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()
    def test_clus_reg_invalid_unknown_cols(self):
        r = exec_validator('sources_of_truth/cluster_registry/cluster_reg_sot_invalid_unknown_cols.csv',
                           'models/cluster_registry.py')

        self.assertEqual(255, r.process.returncode, "wrong exit code")
        found = re.findall("^ERROR.*Extra inputs are not permitted", r.stdout, flags=re.MULTILINE)
        self.assertEqual(42, len(found))
        self.assertIn("CSV is invalid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_clus_reg_invalid_extra_whitespace(self):
        r = exec_validator('sources_of_truth/cluster_registry/cluster_reg_sot_invalid_whitespace.csv',
                           'models/cluster_registry.py')

        self.assertEqual(255, r.process.returncode, "wrong exit code")
        found = re.findall("^ERROR.*Required field", r.stdout, flags=re.MULTILINE)
        self.assertEqual(7, len(found))
        self.assertIn("Encountered CSV parsing error", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_clus_reg_valid_(self):
        r = exec_validator('sources_of_truth/cluster_registry/cluster_reg_sot_valid.csv',
                           'models/cluster_registry.py')

        self.assertEqual(0, r.process.returncode, "wrong exit code")
        self.assertIn("CSV is valid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertTrue(r.outfile.exists())

        r.cleanup()

    def test_clus_reg_valid_with_warnings(self):
        r = exec_validator('sources_of_truth/cluster_registry/cluster_reg_sot_valid_missing_optionals.csv',
                           'models/cluster_registry.py')

        self.assertEqual(0, r.process.returncode, "wrong exit code")
        found = re.findall("^WARNING", r.stdout,
                           flags=re.MULTILINE)
        self.assertEqual(3, len(found))
        self.assertIn("CSV is valid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertTrue(r.outfile.exists())

        r.cleanup()

    def test_platform_invalid(self):
        r = exec_validator('sources_of_truth/platform/platform_invalid.csv',
                           'models/platform.py')
        self.assertEqual(255, r.process.returncode, "wrong exit code")
        found = re.findall(r"^ERROR\s+Line", r.stdout, flags=re.MULTILINE)
        self.assertEqual(6, len(found))
        self.assertIn("CSV is invalid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_platform_extra_cols(self):
        r = exec_validator('sources_of_truth/platform/platform_invalid_extra_cols.csv',
                           'models/platform.py')

        self.assertEqual(255, r.process.returncode, "wrong exit code")
        found = re.findall("^ERROR.*Extra inputs are not permitted", r.stdout,
                           flags=re.MULTILINE)
        self.assertEqual(28, len(found))
        self.assertIn("CSV is invalid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertFalse(r.outfile.exists())

        r.cleanup()

    def test_platform_valid_(self):
        r = exec_validator(
            'sources_of_truth/platform/platform_valid.csv',
            'models/platform.py')

        self.assertEqual(0, r.process.returncode, "wrong exit code")
        self.assertIn("CSV is valid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertTrue(r.outfile.exists())

        r.cleanup()

    def test_platform_valid_missing_optional_cols(self):
        r = exec_validator(
            'sources_of_truth/platform/platform_valid_optional.csv',
            'models/platform.py')

        self.assertEqual(0, r.process.returncode, "wrong exit code")
        found = re.findall("^WARNING", r.stdout, flags=re.MULTILINE)
        self.assertEqual(0, len(found))
        self.assertIn("CSV is valid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertTrue(r.outfile.exists())

        r.cleanup()

    def test_platform_valid_whitespace(self):
        r = exec_validator(
            'sources_of_truth/platform/platform_valid_whitespace.csv',
            'models/platform.py')

        self.assertEqual(0, r.process.returncode, "wrong exit code")
        found = re.findall("^WARNING", r.stdout, flags=re.MULTILINE)
        self.assertEqual(0, len(found))
        self.assertIn("CSV is valid", r.stdout)
        self.assertEqual("", r.stderr)
        self.assertTrue(r.outfile.exists())

        r.cleanup()
