import sys
import unittest
from pathlib import Path
from unittest import mock

from dotnay.file_association import PROJECT_ROOT, build_open_command
from dotnay.resources import asset_dir


class FileAssociationTests(unittest.TestCase):
    def test_open_command_quotes_python_path_and_filename(self):
        command = build_open_command(r"C:\Program Files\Python\pythonw.exe")
        self.assertTrue(command.startswith('"C:\\Program Files\\Python\\pythonw.exe" -c "'))
        self.assertIn("from dotnay.app import main", command)
        self.assertIn(repr(str(PROJECT_ROOT)), command)
        self.assertTrue(command.endswith('"%1"'))

    def test_open_command_supports_project_paths_with_spaces(self):
        project = Path(r"C:\Users\Some User\dotnay")
        command = build_open_command(r"C:\Python\pythonw.exe", project)
        self.assertIn("Some User", command)
        self.assertIn("sys.path.insert", command)
        self.assertTrue(command.endswith('"%1"'))

    def test_frozen_open_command_runs_the_exe_directly(self):
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "_MEIPASS", r"C:\Temp\_MEI123", create=True):
            command = build_open_command(r"C:\Apps\dotnay.exe")
        self.assertEqual(command, '"C:\\Apps\\dotnay.exe" "%1"')

    def test_asset_dir_uses_the_bundle_when_frozen(self):
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "_MEIPASS", r"C:\Temp\_MEI123", create=True):
            self.assertEqual(asset_dir(), Path(r"C:\Temp\_MEI123") / "dotnay" / "assets")


if __name__ == "__main__":
    unittest.main()
