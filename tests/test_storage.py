import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema.exceptions import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from lotus.core.storage import load_project, save_project


class TestStorageValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_save_project_rejects_invalid_session_shape(self):
        with self.assertRaises(ValidationError):
            save_project({"metadata": {}}, str(self.temp_dir / "invalid"))

    def test_save_project_rejects_non_object_payloads(self):
        with self.assertRaises(ValidationError):
            save_project(None, str(self.temp_dir / "none"))

    def test_load_project_rejects_invalid_saved_session(self):
        target = self.temp_dir / "broken"
        target.mkdir()
        with open(target / "session.json", "w", encoding="utf-8") as handle:
            json.dump({"metadata": {}}, handle)

        with self.assertRaises(ValidationError):
            load_project(str(target))

    def test_load_project_rejects_non_object_saved_session(self):
        target = self.temp_dir / "broken-root"
        target.mkdir()
        with open(target / "session.json", "w", encoding="utf-8") as handle:
            json.dump("not-an-object", handle)

        with self.assertRaises(ValidationError):
            load_project(str(target))
