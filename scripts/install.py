#!/usr/bin/env python3
"""Install selected local skills without silently replacing an existing skill."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]


def install(source_root, destination, selected=None, replace=False, dry_run=False):
    source_root, destination = Path(source_root), Path(destination).expanduser()
    catalog = json.loads((source_root / 'catalog.json').read_text(encoding='utf-8'))
    by_id = {s['id']: s for s in catalog['skills']}
    names = list(dict.fromkeys(selected or by_id))
    unknown = set(names) - set(by_id)
    if unknown:
        raise ValueError('Unknown skills: ' + ', '.join(sorted(unknown)))
    for name in names:
        src = source_root / by_id[name]['path']
        if not (src / 'SKILL.md').is_file():
            raise ValueError('Incomplete source: ' + name)
        target = destination / name
        if target.is_symlink():
            raise ValueError('Refusing to replace a symlink: ' + name)
        if target.exists() and not target.is_dir():
            raise ValueError('Destination is not a directory: ' + name)
        if target.exists() and not replace:
            raise FileExistsError('Already installed: ' + name + '; use --replace to keep a backup and replace')
    if dry_run:
        return [{'skill': n, 'action': 'replace' if (destination / n).exists() else 'install'} for n in names]
    destination.mkdir(parents=True, exist_ok=True)
    report = []
    for name in names:
        target = destination / name
        backup = None
        staging = Path(tempfile.mkdtemp(prefix='.teacher-stage-', dir=destination.parent)) / name
        try:
            shutil.copytree(source_root / by_id[name]['path'], staging,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
            if target.exists():
                backup_dir = destination.parent / 'teacher-skill-backups'
                backup_dir.mkdir(exist_ok=True)
                backup = Path(tempfile.mkdtemp(prefix=name + '-' + datetime.now().strftime('%Y%m%d-'), dir=backup_dir)) / name
                target.rename(backup)
            try:
                staging.rename(target)
            except Exception:
                if backup is not None:
                    backup.rename(target)
                raise
            report.append({'skill': name, 'installed': True, 'backup': str(backup) if backup else None})
        finally:
            shutil.rmtree(staging.parent, ignore_errors=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dest', default=str(Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills'))
    parser.add_argument('--skill', action='append', help='Repeat to select skills; default: all twelve')
    parser.add_argument('--replace', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        result = install(ROOT, args.dest, args.skill, args.replace, args.dry_run)
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
