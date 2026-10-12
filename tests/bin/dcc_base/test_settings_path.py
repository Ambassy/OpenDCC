# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class TestApplicationSettingsPath(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="settings-path-")
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.home = self.directory / "home"
        self.home.mkdir()
        self.environment = os.environ.copy()
        self.environment["USERPROFILE"] = str(self.home)
        self.environment["HOME"] = str(self.home)
        self.environment.pop("OPENDCC_SETTINGS_DIR", None)

    def run_application(self, expected):
        fixture = Path(__file__).parent / "fixtures" / "settings_path.py"
        result = subprocess.run(
            [self.application, "--script", str(fixture), str(expected)],
            cwd=self.directory,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("isolated settings written", result.stdout + result.stderr)
        settings = json.loads((expected / "settings.json").read_text())
        self.assertEqual(settings["test"]["isolation"], "isolated")

    def test_absolute_override_creates_nested_directory_with_spaces(self):
        expected = self.directory / "custom profile" / "settings"
        self.environment["OPENDCC_SETTINGS_DIR"] = str(expected)
        self.run_application(expected)
        self.assertFalse((self.home / ".opendcc").exists())

    def test_relative_override(self):
        self.environment["OPENDCC_SETTINGS_DIR"] = "relative profile/settings"
        self.run_application(self.directory / "relative profile" / "settings")
        self.assertFalse((self.home / ".opendcc").exists())

    def test_unset_override_uses_home(self):
        self.run_application(self.home / ".opendcc")

    def test_empty_override_uses_home(self):
        self.environment["OPENDCC_SETTINGS_DIR"] = ""
        self.run_application(self.home / ".opendcc")

    def test_override_does_not_read_modify_or_migrate_user_preferences(self):
        sentinel = '{"test": {"isolation": "user preferences"}}'
        paths = [self.home / name / "settings.json" for name in (".opendcc", ".dcc")]
        for path in paths:
            path.parent.mkdir()
            path.write_text(sentinel)
        expected = self.directory / "isolated"
        self.environment["OPENDCC_SETTINGS_DIR"] = str(expected)
        self.run_application(expected)
        for path in paths:
            self.assertEqual(path.read_text(), sentinel)

    def test_override_skips_legacy_migration(self):
        legacy = self.home / ".dcc" / "settings.json"
        legacy.parent.mkdir()
        sentinel = '{"test": {"isolation": "legacy preferences"}}'
        legacy.write_text(sentinel)
        expected = self.directory / "isolated"
        self.environment["OPENDCC_SETTINGS_DIR"] = str(expected)
        self.run_application(expected)
        self.assertEqual(legacy.read_text(), sentinel)
        self.assertFalse((self.home / ".opendcc").exists())


if __name__ == "__main__":
    TestApplicationSettingsPath.application = sys.argv[1]
    unittest.main(argv=[__file__], verbosity=2)
