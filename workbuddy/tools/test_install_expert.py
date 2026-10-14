#!/usr/bin/env python3
"""Risk-focused installer tests. All registrars and config roots are temporary."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).with_name("install_expert.py")
spec = importlib.util.spec_from_file_location("teacher_expert_installer", SCRIPT)
installer = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="teacher-expert-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.package = self.base / "source"
        self.config = self.base / "workbuddy-config"
        self.manager = self.base / "TEST-STUB-expert-manager"
        self.name = "teacher-workflow-expert"
        self.target = self.config / "plugins/marketplaces/my-experts/plugins" / self.name
        self.registry = self.target.parent.parent / ".codebuddy-plugin/marketplace.json"
        self.session = "test-workbuddy-session-not-a-real-session"
        self.package.mkdir()
        self.make_package(self.package)
        (self.manager / "scripts").mkdir(parents=True)
        (self.manager / "scripts/validate_expert.py").write_text(textwrap.dedent("""
            # Explicit test stub: never a real WorkBuddy validator.
            import os, pathlib, sys
            root = pathlib.Path(sys.argv[1])
            config = pathlib.Path(os.environ['WORKBUDDY_CONFIG_DIR'])
            assert root.is_relative_to(config)
            assert (root / '.codebuddy-plugin/plugin.json').is_file()
            if (root / 'validation-must-fail').exists():
                sys.exit(9)
        """), encoding="utf-8")
        self.write_registrar()
        self.env = patch.dict(os.environ, {"CODEBUDDY_SESSION_ID": self.session}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def make_package(self, root):
        (root / ".codebuddy-plugin").mkdir(parents=True)
        (root / "agents").mkdir()
        (root / "agents/teacher-workflow-expert.md").write_text("---\nname: teacher-workflow-expert\ndescription: test expert\n---\nTest fixture.\n", encoding="utf-8")
        (root / "avatars").mkdir()
        (root / "avatars/expert.png").write_bytes(b"test-avatar-file")
        skills = []
        for number in range(12):
            skill = root / "skills" / f"teacher-test-{number}"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(f"---\nname: teacher-test-{number}\ndescription: test fixture\n---\nTest only.\n", encoding="utf-8")
            skills.append(f"./skills/teacher-test-{number}")
        manifest = {"name": self.name, "plugin": self.name, "expertType": "agent", "agentName": self.name,
                    "agents": [f"./agents/{self.name}.md"], "skills": skills,
                    "avatar": "avatars/expert.png", "homepage": "https://example.invalid/teacher-tests"}
        (root / ".codebuddy-plugin/plugin.json").write_text(json.dumps(manifest), encoding="utf-8")

    def write_registrar(self, fail=False, concurrent=False, missing_marker=False):
        code = """
            # Explicit test stub: never a real WorkBuddy registrar.
            import argparse, json, os, pathlib, sys
            p = argparse.ArgumentParser()
            p.add_argument('expert')
            p.add_argument('--session-id')
            a = p.parse_args()
            root = pathlib.Path(a.expert)
            manifest = json.loads((root / '.codebuddy-plugin/plugin.json').read_text())
            config = pathlib.Path(os.environ['WORKBUDDY_CONFIG_DIR'])
            registry = config / 'plugins/marketplaces/my-experts/.codebuddy-plugin/marketplace.json'
            value = json.loads(registry.read_text()) if registry.exists() else {'name':'my-experts','description':'stub registry','plugins':[]}
            name = manifest['name']
            value['plugins'] = [x for x in value['plugins'] if x['name'] != name]
            value['plugins'].append({'name':name,'source':'./plugins/'+name,'description':'new test expert'})
            if CONCURRENT:
                value['plugins'].append({'name':'unrelated-concurrent-expert','source':'./plugins/unrelated-concurrent-expert'})
            registry.write_text(json.dumps(value))
            if not MISSING_MARKER:
                (root / '.created-by-session').write_text(a.session_id)
            if FAIL:
                sys.exit(7)
        """
        code = textwrap.dedent(code).replace("CONCURRENT", repr(concurrent)).replace("MISSING_MARKER", repr(missing_marker)).replace("FAIL", repr(fail))
        (self.manager / "scripts/register_expert.py").write_text(code, encoding="utf-8")

    def run_install(self, **kwargs):
        return installer.install(self.package, self.config, self.manager, **kwargs)

    def seed_existing(self):
        self.target.parent.mkdir(parents=True)
        import shutil
        shutil.copytree(self.package, self.target)
        (self.target / "old-version.txt").write_text("preserve this old version", encoding="utf-8")
        self.registry.parent.mkdir(parents=True)
        self.original_registry = {"name": "my-experts", "description": "keep registry metadata", "ownerHint": "test only", "plugins": [
            {"name": "unrelated-expert", "source": "./plugins/unrelated-expert", "description": "never alter"},
            {"name": self.name, "source": f"./plugins/{self.name}", "description": "old version"}]}
        self.registry.write_text(json.dumps(self.original_registry), encoding="utf-8")

    def test_normal_install_and_readonly_check(self):
        result = self.run_install()
        self.assertEqual(result["status"], "installed")
        self.assertTrue(result["current_session_verified"])
        self.assertEqual((self.target / ".created-by-session").read_text(), self.session)
        self.assertEqual(installer.check_install(self.package, self.config)["skills"], 12)
        self.assertFalse((self.config / "plugins/installed_plugins.json").exists())
        self.assertFalse((self.config / "settings.json").exists())

    def test_existing_directory_is_not_overwritten(self):
        self.seed_existing()
        before = self.registry.read_bytes()
        with self.assertRaises(installer.InstallError):
            self.run_install()
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertEqual((self.target / "old-version.txt").read_text(), "preserve this old version")
        self.assertFalse((self.target.parent.parent / ".install-backups").exists())

    def test_replace_success_retains_backup_and_other_registration(self):
        self.seed_existing()
        result = self.run_install(replace=True)
        backup = Path(result["backup"])
        self.assertEqual((backup / "plugin/old-version.txt").read_text(), "preserve this old version")
        self.assertEqual(json.loads((backup / "marketplace.json").read_text()), self.original_registry)
        current = json.loads(self.registry.read_text())
        self.assertEqual(current["plugins"][0], self.original_registry["plugins"][0])
        self.assertEqual(current["ownerHint"], "test only")
        self.assertFalse((self.target / "old-version.txt").exists())

    def test_replace_failure_restores_own_plugin_and_registration(self):
        self.seed_existing()
        self.write_registrar(fail=True)
        with self.assertRaisesRegex(installer.InstallError, "已恢复"):
            self.run_install(replace=True)
        self.assertEqual((self.target / "old-version.txt").read_text(), "preserve this old version")
        self.assertEqual(json.loads(self.registry.read_text()), self.original_registry)

    def test_failure_retains_unrelated_concurrent_registration(self):
        self.seed_existing()
        self.write_registrar(fail=True, concurrent=True)
        with self.assertRaises(installer.InstallError):
            self.run_install(replace=True)
        plugins = json.loads(self.registry.read_text())["plugins"]
        self.assertIn(self.original_registry["plugins"][0], plugins)
        self.assertIn(self.original_registry["plugins"][1], plugins)
        self.assertTrue(any(x["name"] == "unrelated-concurrent-expert" for x in plugins))

    def test_missing_session_fails_before_user_config_writes(self):
        with patch.dict(os.environ, {"CODEBUDDY_SESSION_ID": ""}):
            with self.assertRaisesRegex(installer.InstallError, "CODEBUDDY_SESSION_ID"):
                self.run_install()
        self.assertFalse(self.config.exists())

    def test_unexpanded_session_is_rejected(self):
        with patch.dict(os.environ, {"CODEBUDDY_SESSION_ID": "$CODEBUDDY_SESSION_ID"}):
            with self.assertRaises(installer.InstallError):
                self.run_install()
        self.assertFalse(self.config.exists())

    def test_dry_run_without_session_makes_no_config_writes(self):
        with patch.dict(os.environ, {"CODEBUDDY_SESSION_ID": ""}):
            result = self.run_install(dry_run=True)
        self.assertEqual(result["status"], "dry-run")
        self.assertFalse(result["writes"])
        self.assertFalse(result["session_available"])
        self.assertFalse(self.config.exists())
        self.assertTrue(result["gaps"])

    def test_official_validation_failure_creates_no_user_plugin(self):
        (self.package / "validation-must-fail").touch()
        with self.assertRaisesRegex(installer.InstallError, "validate_expert.py"):
            self.run_install()
        self.assertFalse(self.config.exists())

    def test_missing_session_marker_causes_first_install_rollback(self):
        self.write_registrar(missing_marker=True)
        with self.assertRaisesRegex(installer.InstallError, "会话归属"):
            self.run_install()
        self.assertFalse(self.target.exists())
        self.assertFalse(self.registry.exists())

    def test_replace_refuses_other_plugin_in_same_directory(self):
        self.seed_existing()
        manifest_path = self.target / ".codebuddy-plugin/plugin.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["name"] = "another-expert"
        manifest_path.write_text(json.dumps(manifest))
        before = self.registry.read_bytes()
        with self.assertRaisesRegex(installer.InstallError, "其他插件"):
            self.run_install(replace=True)
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertTrue((self.target / "old-version.txt").exists())

    def test_registration_name_collision_cannot_modify_other_expert(self):
        self.registry.parent.mkdir(parents=True)
        existing = {"name": "my-experts", "plugins": [
            {"name": self.name, "source": "./plugins/another-expert", "description": "do not touch"}]}
        self.registry.write_text(json.dumps(existing))
        before = self.registry.read_bytes()
        with self.assertRaisesRegex(installer.InstallError, "冲突"):
            self.run_install()
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertFalse(self.target.exists())

    def test_config_subdirectory_symlink_cannot_escape_config(self):
        self.config.mkdir()
        outside = self.base / "outside-config"
        outside.mkdir()
        (self.config / "plugins").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallError, "越出"):
            self.run_install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_and_path_traversal_packages_are_rejected(self):
        (self.package / "external-link").symlink_to(self.base)
        with self.assertRaisesRegex(installer.InstallError, "符号链接"):
            self.run_install()
        (self.package / "external-link").unlink()
        manifest_path = self.package / ".codebuddy-plugin/plugin.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["skills"][0] = "../external"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(installer.InstallError, "越界"):
            self.run_install()
        self.assertFalse(self.config.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
