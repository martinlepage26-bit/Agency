import io
import importlib
import os
import shutil
import sys
import tempfile
from builtins import __import__ as builtin_import
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from lotus.core.storage import save_project
from lotus import main as lotus_main


class LotusTtsCliTests(TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.data_dir_patcher = patch.object(lotus_main, "DATA_DIR", self.temp_dir)
        self.data_dir_patcher.start()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.data_dir_patcher.stop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("flowerapp.main._voice11_helpers")
    def test_tts_list_voices_invokes_helpers(self, mock_helpers):
        create_mp3 = MagicMock()
        live = MagicMock()
        mock_helpers.return_value = (create_mp3, live, lambda: ["alpha", "bravo"])

        with patch("sys.argv", ["lotus", "tts", "--list-voices"]):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                lotus_main.main()
        output_lines = stdout.getvalue().strip().splitlines()

        self.assertEqual(output_lines, ["alpha", "bravo"])
        mock_helpers.assert_called_once()

    @patch("flowerapp.main._voice11_helpers")
    @patch("flowerapp.main.calculate_agency")
    def test_tts_renders_mp3_summary(self, mock_calculate, mock_helpers):
        project_name = "test-project"
        summary = {
            "agency_total": 66.0,
            "subscores": {
                "perceptual_latitude": {"score": 11.0, "caps_applied": ["isolation"]},
            },
        }
        mock_calculate.return_value = summary

        create_mp3 = MagicMock(return_value=Path("rendered.mp3"))
        live = MagicMock()
        mock_helpers.return_value = (create_mp3, live, lambda: [])

        project_data = {
            "metadata": {"project_id": project_name, "project_name": "Test Project"},
            "intake": {},
            "scoring": {},
        }
        target = self.temp_dir / project_name
        save_project(project_data, str(target))

        output_base = self.temp_dir / "tts-output"
        with patch("sys.argv", ["lotus", "tts", "--project", project_name, "--output", str(output_base)]):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                lotus_main.main()

        create_mp3.assert_called_once()
        text_arg = create_mp3.call_args[0][0]
        path_arg = create_mp3.call_args[0][1]
        self.assertEqual(path_arg, output_base)
        self.assertIn("Test Project agency score is 66.0", text_arg)
        self.assertIn("Caps applied: isolation", text_arg)


class Voice11CliDependencyTests(TestCase):
    def _import_voice11_cli_without_speech_modules(self):
        cached_modules = {
            name: module
            for name, module in sys.modules.items()
            if name == "voice11" or name.startswith("voice11.")
        }
        for name in cached_modules:
            sys.modules.pop(name, None)

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            root_name = name.split(".", 1)[0]
            if root_name in {"pyttsx3", "pydub"}:
                error = ImportError(f"No module named '{root_name}'")
                error.name = root_name
                raise error
            return builtin_import(name, globals, locals, fromlist, level)

        self.addCleanup(self._restore_voice11_modules, cached_modules)
        with patch("builtins.__import__", side_effect=guarded_import):
            return importlib.import_module("voice11.cli")

    def _restore_voice11_modules(self, cached_modules):
        for name in list(sys.modules):
            if name == "voice11" or name.startswith("voice11."):
                sys.modules.pop(name, None)
        sys.modules.update(cached_modules)

    def test_voice11_cli_module_imports_without_optional_speech_dependencies(self):
        module = self._import_voice11_cli_without_speech_modules()
        self.assertTrue(callable(module.main))

    def test_voice11_cli_surfaces_friendly_dependency_message(self):
        import voice11.cli as voice11_cli

        message = "Voice11 helpers are unavailable. Install the speech extras before using Voice11."
        with patch("voice11.cli.check_speech_dependencies", side_effect=voice11_cli.Voice11DependencyError(message)):
            with patch("sys.argv", ["voice11", "list"]):
                with self.assertRaises(SystemExit) as exc_info:
                    voice11_cli.main()

        self.assertEqual(str(exc_info.exception), message)
