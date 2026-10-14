#!/usr/bin/env python3
"""Validate skill packaging, invocation metadata, references, and source syntax."""
import argparse
import ast
import json
from pathlib import Path
import re
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate(root):
    root = Path(root).resolve()
    errors = []
    catalog = json.loads((root / 'catalog.json').read_text(encoding='utf-8'))
    skills = catalog['skills']
    if len(skills) != 12 or len({s['id'] for s in skills}) != 12:
        errors.append('Catalog must contain exactly twelve unique skills')
    names = {s['id'] for s in skills}
    for item in skills:
        folder = root / item['path']
        for rel in ['SKILL.md', 'SUMMARY.md', 'agents/openai.yaml', 'references/worked-example.md']:
            if not (folder / rel).is_file():
                errors.append(f"{item['id']}: missing {rel}")
        entry = folder / 'SKILL.md'
        if not entry.exists():
            continue
        body = entry.read_text(encoding='utf-8')
        match = re.match(r'^---\n(.*?)\n---(?:\n|$)', body, re.S)
        if not match:
            errors.append(f"{item['id']}: invalid frontmatter")
            continue
        try:
            meta = yaml.safe_load(match.group(1))
            if not isinstance(meta, dict) or meta.get('name') != item['id']:
                errors.append(f"{item['id']}: frontmatter name mismatch")
            elif set(meta) - {'name', 'description', 'metadata', 'license', 'allowed-tools'}:
                errors.append(f"{item['id']}: unsupported frontmatter keys")
            if not isinstance(meta.get('description'), str) or not 1 <= len(meta['description'].strip()) <= 1024:
                errors.append(f"{item['id']}: missing/invalid description")
            if str(meta.get('metadata', {}).get('version')) != catalog['version']:
                errors.append(f"{item['id']}: version mismatch")
            if not re.fullmatch(r'teacher-[a-z0-9]+(?:-[a-z0-9]+)*', item['id']) or len(item['id']) > 64:
                errors.append(f"{item['id']}: naming convention")
            ui = yaml.safe_load((folder / 'agents/openai.yaml').read_text(encoding='utf-8'))
            interface = ui['interface']
            if '$' + item['id'] not in interface['default_prompt']:
                errors.append(f"{item['id']}: default_prompt must invoke this skill")
            if not 25 <= len(interface['short_description']) <= 64:
                errors.append(f"{item['id']}: short_description must contain 25–64 characters")
        except (yaml.YAMLError, TypeError, KeyError, AttributeError, OSError) as exc:
            errors.append(f"{item['id']}: metadata error: {exc}")
        if 'references/worked-example.md' not in body:
            errors.append(f"{item['id']}: worked example is not linked from entrypoint")
    roots = [root / s['path'] for s in skills] + [root / 'scripts', root / 'tests', root / 'docs']
    files = [p for d in roots for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [p for p in root.glob('*.md')]
    for path in files:
        if path.suffix == '.py':
            try:
                ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            except SyntaxError as exc:
                errors.append(f'{path.relative_to(root)}: {exc}')
        if path.suffix != '.md':
            continue
        content = path.read_text(encoding='utf-8')
        # Only inline Markdown links; external links and local anchors are not fetched.
        content = re.sub(r'```.*?```', '', content, flags=re.S)
        for target in re.findall(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', content):
            target = target.strip().split(' "')[0].strip('<>')
            if not target or target.startswith(('#', 'https://', 'http://', 'mailto:', 'app://')):
                continue
            resolved = (path.parent / target.split('#')[0]).resolve()
            if not resolved.is_relative_to(root):
                errors.append(f'{path.relative_to(root)}: link leaves repository: {target}')
            elif not resolved.exists():
                errors.append(f'{path.relative_to(root)}: broken link: {target}')
        if re.search(r'\[TODO:|\b(?:TBD|FIXME)\b|Lorem ipsum|待填入|在此填写', content):
            errors.append(f'{path.relative_to(root)}: unfinished scaffold')
    extras = {p.name for p in root.glob('teacher-*') if p.is_dir()} - names
    if extras:
        errors.append('Uncatalogued skill directories: ' + ', '.join(sorted(extras)))
    return {'version': catalog['version'], 'skills': len(skills), 'files_checked': len(files), 'errors': errors, 'passed': not errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = validate(args.root)
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
