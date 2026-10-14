#!/usr/bin/env python3
"""Check checksums, official plugin fields, twelve skills, links and avatar."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]


def validate(root):
    root=Path(root).resolve()
    errors=[]
    try:
        plugin=json.loads((root/'.codebuddy-plugin/plugin.json').read_text(encoding='utf-8'))
        manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:
        return {'passed':False,'errors':[str(exc)]}
    def local(rel):
        p=(root/rel).resolve()
        if not p.is_relative_to(root):
            raise ValueError('Path leaves package: '+rel)
        return p
    for rel,digest in manifest['files'].items():
        try:
            f=local(rel)
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=digest:
                errors.append('Missing or changed file: '+rel)
        except ValueError as exc:
            errors.append(str(exc))
    for key in ['name','version','description','author','agents','expertType','agentName','displayName','profession','displayDescription','avatar','categoryId','defaultInitPrompt','plugin','tags','quickPrompts','skills']:
        if key not in plugin: errors.append('Missing plugin field: '+key)
    if plugin.get('name')!='teacher-workflow-expert' or plugin.get('plugin')!=plugin.get('name'): errors.append('Plugin identity mismatch')
    if plugin.get('expertType')!='agent': errors.append('Expected one agent')
    if plugin.get('categoryId') not in {'12-IndustryConsultant','15-Education'}: errors.append('Unexpected category')
    for key in ['displayName','profession','displayDescription','defaultInitPrompt']:
        if not all(plugin.get(key,{}).get(lang) for lang in ['en','zh']): errors.append('Missing i18n: '+key)
    if not 40<=len(plugin.get('displayDescription',{}).get('zh',''))<=50: errors.append('Chinese display description must contain 40–50 characters')
    for key in ['tags','quickPrompts']:
        if len(plugin.get(key,[]))!=3: errors.append('Expected three '+key)
    if plugin.get('quickPrompts',[{}])[0]!=plugin.get('defaultInitPrompt'): errors.append('Default prompt differs from first quick prompt')
    skills=plugin.get('skills',[])
    if len(skills)!=12 or len(set(skills))!=12: errors.append('Expected twelve unique skills')
    for rel in skills:
        try:
            folder=local(rel)
            s=(folder/'SKILL.md').read_text(encoding='utf-8')
            front=re.match(r'^---\n(.*?)\n---\n',s,re.S)
            if not front: errors.append('Bad frontmatter: '+rel);continue
            for field in ['name','description','description_zh','description_en','version','author']:
                if not re.search(r'^'+field+r':\s*\S',front.group(1),re.M): errors.append(rel+': missing '+field)
            name=re.search(r'^name:\s*(.+)',front.group(1),re.M)
            if name and json.loads(name.group(1))!=folder.name: errors.append('Skill name mismatch: '+rel)
            for f in ['SUMMARY.md','references/worked-example.md']:
                if not (folder/f).is_file():errors.append('Missing skill resource: '+rel+'/'+f)
        except (OSError,ValueError) as exc:
            errors.append(str(exc))
    try:
        agent=local('agents/'+plugin['agentName']+'.md').read_text(encoding='utf-8')
        if re.search(r'^tools:',agent.split('---')[1],re.M): errors.append('Agent must not declare tools')
        if len(re.findall(r'^> 召唤教师工作流专家', (root/'USAGE.md').read_text(encoding='utf-8'),re.M))!=36: errors.append('Expected 36 user prompts')
        avatar=local(plugin['avatar']); data=avatar.read_bytes()
        if data[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',data[16:24])!=(512,512) or len(data)>500*1024: errors.append('Avatar must be 512×512 PNG ≤500KB')
    except (OSError,KeyError,ValueError,IndexError,struct.error) as exc: errors.append(str(exc))
    for path in root.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or '.venv' in path.parts:continue
        if path.suffix=='.py':
            try:ast.parse(path.read_text(encoding='utf-8'))
            except SyntaxError as exc:errors.append(str(exc))
        if path.suffix!='.md':continue
        text=path.read_text(encoding='utf-8')
        if re.search(r'\$teacher-|/Users/keli/|\[TODO:|\bTBD\b|Lorem ipsum',text):errors.append('Host-specific syntax or unfinished content: '+str(path.relative_to(root)))
        text=re.sub(r'```.*?```','',text,flags=re.S)
        for link in re.findall(r'!?\[[^\]\n]*\]\(([^)\n]+)\)',text):
            if link.startswith(('https://','http://','#','mailto:')):continue
            try:
                resolved=(path.parent/link.strip('<>').split('#')[0]).resolve()
                if not resolved.is_relative_to(root) or not resolved.exists():errors.append('Broken local link: '+str(path.relative_to(root))+' → '+link)
            except ValueError:errors.append('Bad local link: '+link)
    return {'passed':not errors,'expert':plugin.get('name'),'version':plugin.get('version'),'skills':len(skills),'verified_files':len(manifest['files']),'errors':errors}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args()
    result=validate(args.root);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1


if __name__=='__main__':sys.exit(main())
