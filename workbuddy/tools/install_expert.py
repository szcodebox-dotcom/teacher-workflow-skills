#!/usr/bin/env python3
"""Install this expert using WorkBuddy's own validator and registrar.

Run the packaged copy from a WorkBuddy conversation.  No credentials are read;
the current runtime's CODEBUDDY_SESSION_ID is passed to the official registrar.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSION_ENV = "CODEBUDDY_SESSION_ID"


class InstallError(RuntimeError):
    pass


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallError(f"无法读取有效 JSON：{path} ({exc})") from exc
    if not isinstance(value, dict):
        raise InstallError(f"JSON 顶层必须是对象：{path}")
    return value


def local_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise InstallError(f"包内路径必须是相对路径：{value!r}")
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise InstallError(f"包内路径越界：{value!r}") from exc
    return candidate


def inspect_package(root: Path) -> dict:
    manifest = read_json(root / ".codebuddy-plugin" / "plugin.json")
    name = manifest.get("name", "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) < 2:
        raise InstallError("专家 name 必须是至少两字符的小写连字符标识。")
    if manifest.get("expertType") != "agent":
        raise InstallError("本安装器仅用于此单专家包（expertType: agent）。")
    if manifest.get("plugin") != name:
        raise InstallError("plugin 必须与 name 一致。")
    agent = manifest.get("agentName", "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", agent):
        raise InstallError("agentName 无效。")
    agent_path = local_path(root, f"agents/{agent}.md")
    if not agent_path.is_file():
        raise InstallError(f"缺少主专家定义：{agent_path}")
    for value in manifest.get("agents", []):
        if not local_path(root, value).is_file():
            raise InstallError(f"缺少 Agent 文件：{value}")
    skills = manifest.get("skills")
    if (not isinstance(skills, list) or len(skills) != 12
            or any(not isinstance(value, str) for value in skills)
            or len(set(skills)) != 12):
        raise InstallError("本包必须声明 12 个不同的内置技能目录。")
    for value in skills:
        if not (local_path(root, value) / "SKILL.md").is_file():
            raise InstallError(f"缺少内置技能 SKILL.md：{value}")
    avatar = local_path(root, manifest.get("avatar", ""))
    if not avatar.is_file():
        raise InstallError("缺少专家头像。")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise InstallError(f"拒绝安装含符号链接的包：{path.relative_to(root)}")
    return manifest


def manager_candidates(config_dir: Path) -> list[Path]:
    return [
        config_dir / "plugins/marketplaces/workbuddy-builtin/skills/expert-manager",
        Path.home() / ".workbuddy/plugins/marketplaces/workbuddy-builtin/skills/expert-manager",
        Path("/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/expert-manager"),
    ]


def locate_manager(explicit: Path | None, config_dir: Path) -> Path | None:
    candidates = [explicit] if explicit else manager_candidates(config_dir)
    for candidate in candidates:
        if candidate is None:
            continue
        candidate = candidate.expanduser().resolve()
        if all((candidate / "scripts" / script).is_file()
               for script in ("validate_expert.py", "register_expert.py")):
            return candidate
    if explicit:
        raise InstallError("--manager-dir 必须指向包含官方 scripts/validate_expert.py 与 register_expert.py 的 expert-manager 目录。")
    return None


def current_session() -> str | None:
    value = os.environ.get(SESSION_ENV, "").strip()
    if not value or "$" in value or value in {"None", "null", "undefined"}:
        return None
    if len(value) > 256 or any(ord(c) < 32 for c in value):
        return None
    return value


def supports_session_argument(registrar: Path) -> bool:
    source = registrar.read_text(encoding="utf-8")
    return bool(re.search(r"(?:add_argument\s*\(\s*['\"]--session-id['\"]|==\s*['\"]--session-id['\"])", source))


def official_run(script: Path, expert: Path, config: Path, args: list[str] | None = None) -> None:
    env = os.environ.copy()
    env["WORKBUDDY_CONFIG_DIR"] = str(config)
    command = [sys.executable, str(script), str(expert)] + (args or [])
    try:
        result = subprocess.run(command, cwd=str(expert), env=env,
                                capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallError(f"官方脚本执行失败：{script.name} ({type(exc).__name__})") from exc
    if result.returncode:
        detail = (result.stdout + result.stderr).strip()[-6000:]
        # Neither this installer nor the official scripts need to print a session.
        session = current_session()
        if session:
            detail = detail.replace(session, "[当前会话]")
        raise InstallError(f"官方脚本 {script.name} 未通过（退出码 {result.returncode}）：\n{detail}")


def marketplace_entries(path: Path) -> tuple[dict | None, list]:
    if not path.exists():
        return None, []
    manifest = read_json(path)
    plugins = manifest.get("plugins", [])
    if not isinstance(plugins, list) or any(not isinstance(item, dict) for item in plugins):
        raise InstallError(f"注册清单 plugins 格式异常，未修改：{path}")
    return manifest, plugins


def is_own_entry(entry: dict, name: str) -> bool:
    return entry.get("name") == name or entry.get("source") == f"./plugins/{name}"


def verify_registered(manifest_path: Path, name: str) -> None:
    _, entries = marketplace_entries(manifest_path)
    own = [item for item in entries if is_own_entry(item, name)]
    if len(own) != 1 or own[0].get("name") != name or own[0].get("source") != f"./plugins/{name}":
        raise InstallError("官方注册器未生成唯一、名称及路径一致的本专家注册项。")


def ensure_owned_destination(target: Path, manifest_path: Path, package: dict, config: Path) -> None:
    """Reject ambiguous existing ownership and config paths escaping their root."""
    for path in (target, manifest_path):
        try:
            path.resolve().relative_to(config.resolve())
        except ValueError as exc:
            raise InstallError("目标路径通过符号链接越出 WorkBuddy 配置根目录，未修改。") from exc
    for path in (target, target.parent, target.parent.parent,
                 manifest_path, manifest_path.parent):
        if path.is_symlink():
            raise InstallError("专家目录或注册清单路径是符号链接，未修改。")
    name = package["name"]
    _, entries = marketplace_entries(manifest_path)
    own = [item for item in entries if is_own_entry(item, name)]
    if len(own) > 1 or any(item.get("name") != name or item.get("source") != f"./plugins/{name}" for item in own):
        raise InstallError("现有注册清单的本专家名称或目录与其他插件冲突，未修改。")
    if target.exists():
        existing = read_json(target / ".codebuddy-plugin/plugin.json")
        if existing.get("name") != name or existing.get("plugin") != name:
            raise InstallError("同名目录属于其他插件或格式不明，拒绝替换。")
        if existing.get("homepage") != package.get("homepage"):
            raise InstallError("同名专家主页与本包不一致，拒绝替换。")


def atomic_json(path: Path, value: dict) -> None:
    temp = path.with_name(f".{path.name}.rollback-{uuid.uuid4().hex}")
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def restore_own_registration(path: Path, before: dict | None, name: str) -> None:
    """Roll back only our entry, retaining unrelated concurrent registrations."""
    current, entries = marketplace_entries(path)
    if current is None:
        if before is not None:
            atomic_json(path, before)
        return
    prior_entries = [] if before is None else before.get("plugins", [])
    prior_own = [item for item in prior_entries if is_own_entry(item, name)]
    result = [item for item in entries if not is_own_entry(item, name)] + prior_own
    # Restore original ordering when the registrar changed only our entry.
    old_others = [item for item in prior_entries if not is_own_entry(item, name)]
    new_others = [item for item in entries if not is_own_entry(item, name)]
    if before is not None and old_others == new_others:
        current["plugins"] = prior_entries
    else:
        current["plugins"] = result
    if before is None and not result and set(current) <= {"name", "description", "plugins"} and current.get("name") == "my-experts":
        path.unlink()
    else:
        atomic_json(path, current)


def check_install(root: Path, config: Path) -> dict:
    package = inspect_package(root)
    name = package["name"]
    target = config / "plugins/marketplaces/my-experts/plugins" / name
    manifest_path = target.parent.parent / ".codebuddy-plugin/marketplace.json"
    if not target.is_dir() or target.is_symlink():
        raise InstallError(f"本专家尚未安装到预期目录：{target}")
    installed = inspect_package(target)
    if installed["name"] != name:
        raise InstallError("已安装目录的专家标识与此包不一致。")
    verify_registered(manifest_path, name)
    return {"status": "checked", "name": name, "target": str(target), "skills": len(installed["skills"]), "registered": True}


def install(root: Path, config: Path, explicit_manager: Path | None, *, dry_run: bool = False, replace: bool = False) -> dict:
    package = inspect_package(root)
    name = package["name"]
    manager = locate_manager(explicit_manager, config)
    session = current_session()
    base = config / "plugins/marketplaces/my-experts"
    target = base / "plugins" / name
    manifest_path = base / ".codebuddy-plugin/marketplace.json"
    before, _ = marketplace_entries(manifest_path)
    gaps = []
    if manager is None:
        gaps.append("未找到 WorkBuddy 内置 expert-manager；请在 WorkBuddy 内执行，或用 --manager-dir 指定其目录。")
    if session is None:
        gaps.append("缺少 WorkBuddy 当前会话 CODEBUDDY_SESSION_ID；需在 WorkBuddy 对话运行，禁止自行设置虚构值。")
    if target.exists() and not replace:
        gaps.append("同名专家已存在；默认不覆盖。核对后可使用 --replace 备份更新。")
    if dry_run:
        return {"status": "dry-run", "name": name, "target": str(target), "skills": len(package["skills"]),
                "manager": str(manager) if manager else None, "session_available": session is not None,
                "writes": False, "replace": replace, "gaps": gaps,
                "plan": ["在临时隔离目录用官方验证器完整校验", "备份本专家和注册清单（若更新）", "复制本包到专家目录", "用官方注册器注册当前会话", "回读本专家注册项及当前会话标记"]}
    if gaps:
        raise InstallError("\n".join(gaps))
    assert manager is not None and session is not None
    ensure_owned_destination(target, manifest_path, package, config)
    registrar = manager / "scripts/register_expert.py"
    if not supports_session_argument(registrar):
        raise InstallError("该官方注册器未确认支持 --session-id；请更新 WorkBuddy 后在其内置管理器中安装。")
    # The official validator insists on an installation-shaped path.  Validate an
    # isolated copy before creating or altering anything in the user's config.
    with tempfile.TemporaryDirectory(prefix="teacher-expert-preflight-") as temporary:
        staged_config = Path(temporary)
        staged = staged_config / "plugins/marketplaces/my-experts/plugins" / name
        shutil.copytree(root, staged, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store", ".created-by-session"))
        official_run(manager / "scripts/validate_expert.py", staged, staged_config)
        # Recheck immediately before mutation: native validation may take time.
        ensure_owned_destination(target, manifest_path, package, config)
        if target.exists() and not replace:
            raise InstallError("校验期间出现同名专家，默认不覆盖，未修改。")
        before, _ = marketplace_entries(manifest_path)
        base.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = base / ".install-backups" / f"{name}-{stamp}-{uuid.uuid4().hex[:8]}"
        backup.mkdir(parents=True)
        if manifest_path.exists():
            shutil.copy2(manifest_path, backup / "marketplace.json")
        (backup / "backup-state.json").write_text(json.dumps({"expert": name, "manifest_existed": before is not None, "plugin_existed": target.exists()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        previous = backup / "plugin"
        temp_target = target.with_name(f".{name}-install-{uuid.uuid4().hex}")
        moved_old = False
        installed_new = False
        try:
            shutil.copytree(staged, temp_target)
            if target.exists():
                os.replace(target, previous)
                moved_old = True
            os.replace(temp_target, target)
            installed_new = True
            official_run(registrar, target, config, ["--session-id", session])
            verify_registered(manifest_path, name)
            marker = target / ".created-by-session"
            if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != session:
                raise InstallError("官方注册器未确认当前 WorkBuddy 会话归属，已回滚。")
        except Exception as exc:
            rollback_errors = []
            if installed_new and target.exists():
                try:
                    shutil.rmtree(target)
                except OSError as error:
                    rollback_errors.append(f"无法移除本次新专家：{type(error).__name__}")
            if moved_old and previous.exists() and not target.exists():
                try:
                    os.replace(previous, target)
                except OSError as error:
                    rollback_errors.append(f"无法恢复本专家备份：{type(error).__name__}")
            try:
                restore_own_registration(manifest_path, before, name)
            except Exception as error:
                rollback_errors.append(f"注册项回滚失败：{error}")
            if rollback_errors:
                raise InstallError(f"安装失败；需从备份恢复：{backup}\n" + "\n".join(rollback_errors)) from exc
            raise InstallError(f"安装失败，已恢复本专家及其注册项。备份：{backup}\n{exc}") from exc
        finally:
            if temp_target.exists():
                shutil.rmtree(temp_target)
    return {"status": "installed", "name": name, "target": str(target), "skills": len(package["skills"]),
            "registered": True, "current_session_verified": True, "backup": str(backup)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="在 WorkBuddy 当前对话中安装此教师专家包；默认不覆盖现有专家。")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--dry-run", action="store_true", help="只显示计划和缺口，不写配置")
    action.add_argument("--check", action="store_true", help="只读检查本专家目录和注册项")
    parser.add_argument("--manager-dir", type=Path, help="明确指定官方 expert-manager 目录")
    parser.add_argument("--config-dir", type=Path, help="WorkBuddy 配置根目录；传递给原生脚本的 WORKBUDDY_CONFIG_DIR")
    parser.add_argument("--replace", action="store_true", help="备份本专家和注册清单后更新，失败回滚")
    args = parser.parse_args(argv)
    config = (args.config_dir or Path(os.environ.get("WORKBUDDY_CONFIG_DIR", "").strip() or Path.home() / ".workbuddy")).expanduser().resolve()
    try:
        result = check_install(ROOT, config) if args.check else install(ROOT, config, args.manager_dir, dry_run=args.dry_run, replace=args.replace)
    except (InstallError, OSError) as exc:
        print(f"未完成安装：{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
