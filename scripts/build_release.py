#!/usr/bin/env python3
"""Build a deterministic release archive from an explicit publication allowlist."""
import hashlib
import json
from pathlib import Path
import zipfile
import argparse

ROOT = Path(__file__).resolve().parents[1]


def release_files(root):
    catalog = json.loads((root / 'catalog.json').read_text(encoding='utf-8'))
    top = ['README.md', 'LICENSE', 'CHANGELOG.md', 'catalog.json', 'requirements-dev.txt', '.gitignore']
    folders = ['docs', 'scripts', 'tests', '.github', 'workbuddy'] + [s['path'] for s in catalog['skills']]
    files = [root / p for p in top]
    files += [p for folder in folders for p in (root / folder).rglob('*') if p.is_file()]
    return sorted({p for p in files if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.zip'} and p.name != '.DS_Store'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    version = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))['version']
    files = release_files(ROOT)
    manifest = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    manifest_text = json.dumps({'version': version, 'algorithm': 'sha256', 'files': manifest}, ensure_ascii=False, indent=2) + '\n'
    archive = args.out / f'teacher-workflow-skills-v{version}.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, content in [(p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in files] + [('MANIFEST.json', manifest_text.encode())]:
            info = zipfile.ZipInfo('teacher-workflow-skills/' + name, (2026, 10, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, content)
    (args.out / 'MANIFEST.json').write_text(manifest_text, encoding='utf-8')
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (args.out / 'SHA256SUMS').write_text(checksum + '  ' + archive.name + '\n', encoding='utf-8')
    print(json.dumps({'archive': str(archive), 'files': len(files), 'sha256': checksum}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
