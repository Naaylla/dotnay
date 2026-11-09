import unittest
from pathlib import Path

from dotnay.file_association import PROJECT_ROOT, build_open_command


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


if __name__ == "__main__":
    unittest.main()
