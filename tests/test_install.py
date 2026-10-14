import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('teacher_install', Path(__file__).resolve().parents[1] / 'scripts/install.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'src'
        self.source.mkdir()
        self.skill = 'teacher-example'
        folder = self.source / self.skill
        folder.mkdir()
        (folder / 'SKILL.md').write_text('new content')
        (self.source / 'catalog.json').write_text(json.dumps({'skills': [{'id': self.skill, 'path': self.skill}]}))
        self.dest = self.root / 'skills'

    def tearDown(self):
        self.temp.cleanup()

    def test_dry_run_writes_nothing(self):
        MODULE.install(self.source, self.dest, dry_run=True)
        self.assertFalse(self.dest.exists())

    def test_existing_install_is_preserved_and_replacement_is_backed_up(self):
        MODULE.install(self.source, self.dest)
        (self.dest / self.skill / 'SKILL.md').write_text('user edit')
        with self.assertRaises(FileExistsError):
            MODULE.install(self.source, self.dest)
        self.assertEqual((self.dest / self.skill / 'SKILL.md').read_text(), 'user edit')
        result = MODULE.install(self.source, self.dest, replace=True)
        self.assertEqual((Path(result[0]['backup']) / 'SKILL.md').read_text(), 'user edit')
        self.assertEqual((self.dest / self.skill / 'SKILL.md').read_text(), 'new content')

    def test_unknown_selection_does_not_mutate_destination(self):
        with self.assertRaises(ValueError):
            MODULE.install(self.source, self.dest, ['teacher-other'])
        self.assertFalse(self.dest.exists())

    def test_symlink_destination_is_rejected(self):
        self.dest.mkdir()
        (self.dest / self.skill).symlink_to(self.source / self.skill, target_is_directory=True)
        with self.assertRaises(ValueError):
            MODULE.install(self.source, self.dest, replace=True)


if __name__ == '__main__':
    unittest.main()
