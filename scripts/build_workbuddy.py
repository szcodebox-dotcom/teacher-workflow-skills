#!/usr/bin/env python3
"""Build one original WorkBuddy expert containing the twelve maintained skills."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
import yaml

ROOT=Path(__file__).resolve().parents[1]
NAME='teacher-workflow-expert'
VERSION='1.0.0'
AUTHOR='李老师AI教育实验室'
EN={
 'teacher-lesson-pack':('Complete Lesson Pack','Create a coherent lesson plan, slide content, worksheet, exercises and homework from one teaching request.'),
 'teacher-lesson-plan':('Lesson Design','Design a teachable lesson with aligned objectives, activities, formative checks and teacher answers.'),
 'teacher-slide-deck':('Editable Slide Deck','Generate editable teaching PPTX files with speaker notes, source JSON and structural checks.'),
 'teacher-exam-builder':('Original Exam','Write original assessment items with independent answers, detailed scoring and coverage checks.'),
 'teacher-blueprint-exam':('Blueprint Exam','Assemble assessments against a knowledge-by-skill blueprint and audit point allocation.'),
 'teacher-source-question-bank':('Sourced Question Bank','Extract questions from authorized materials while retaining page references and verification status.'),
 'teacher-mistake-coach':('Mistake Coaching','Use visible question and student-response evidence to produce correction, practice and retest tasks.'),
 'teacher-learning-insights':('Learning Insights','Analyze anonymized item-level scores with explicit denominators, missing records and evidence limits.'),
 'teacher-class-action-plan':('Class Follow-up','Turn verified assessment evidence into lesson review, flexible exercises and a two-week retest plan.'),
 'teacher-communication-studio':('Teaching Communication','Create parent meeting scripts, comments and teaching reports grounded in available evidence.'),
 'teacher-workflow-router':('Workflow Routing','Select necessary teaching workflows and define input, output and handoff contracts.'),
 'teacher-workflow-maker':('Workflow Packaging','Package a reusable teaching method as a self-contained WorkBuddy skill with behavioral checks.'),
}


def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')


def adapt_markdown(path):
    text=path.read_text(encoding='utf-8')
    text=re.sub(r'\$(teacher-[a-z0-9-]+)',r'\1',text)
    text=text.replace('/tmp/teacher-learning-demo','./output/teacher-learning-demo').replace('/tmp/teacher-learning-aligned','./output/teacher-learning-aligned')
    if path.parent.name=='references' and path.parent.parent.name=='teacher-workflow-maker':
        text=text.replace('  agents/openai.yaml\n','').replace('下面四个文件','下面三个文件').replace('四个文件互相引用有效','三个文件互相引用有效')
        text=re.sub(r'### agents/openai\.yaml\n.*?(?=### references/example\.md)', '### WorkBuddy 元数据\n\n上面的 SKILL.md frontmatter 还应补 description_zh、description_en、version 和 author；它们是技能元数据，不需要另建 Codex 界面配置。\n\n',text,flags=re.S)
        text=text.replace('资源：SKILL.md、界面配置、完整合成例子。','资源：SKILL.md、双语技能元数据、完整合成例子。')
        text=text.replace('界面短描述28字符，处于25–64字符范围。','WorkBuddy双语技能元数据与输入输出一致。')
        text=text.replace('metadata:\n  version: "2.0.0"','description_zh: 制作离堂检测，按作答步骤整理次日反馈。\ndescription_en: Create an exit check and next-day feedback from observed student work.\nversion: "2.0.0"\nauthor: "李老师AI教育实验室"')
    if path.parent.name=='references' and path.parent.parent.name=='teacher-slide-deck' or path.name=='SKILL.md' and path.parent.name=='teacher-slide-deck':
        fence='.venv/bin/python scripts/build_deck.py references/example-deck.json --output lesson.pptx\n```'
        text=text.replace(fence,fence+'\n\nWindows PowerShell 使用：\n\n```powershell\npy -3 -m venv .venv\n.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n.\\.venv\\Scripts\\python.exe scripts/build_deck.py references/example-deck.json --output lesson.pptx\n```')
    if path.parent.name=='teacher-workflow-maker' and path.name=='SUMMARY.md':
        text=text.replace('`agents/openai.yaml`','WorkBuddy双语技能元数据').replace('agents/openai.yaml','WorkBuddy双语技能元数据')
    path.write_text(text,encoding='utf-8')


def build(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    pkg=out/NAME
    if pkg.exists():shutil.rmtree(pkg)
    pkg.mkdir()
    catalog=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
    assert len(catalog['skills'])==12
    for item in catalog['skills']:
        dst=pkg/'skills'/item['id']
        shutil.copytree(ROOT/item['path'],dst,ignore=shutil.ignore_patterns('agents','__pycache__','*.pyc','.DS_Store','.venv'))
        for md in dst.rglob('*.md'):adapt_markdown(md)
        entry=dst/'SKILL.md'
        text=entry.read_text(encoding='utf-8');match=re.match(r'^---\n(.*?)\n---\n(.*)$',text,re.S)
        meta=yaml.safe_load(match.group(1));body=match.group(2)
        if item['id']=='teacher-workflow-maker':body=(ROOT/'workbuddy/adaptations/workflow-maker.md').read_text(encoding='utf-8')
        fields={'name':item['id'],'display_name':item['title'],'display_name_en':EN[item['id']][0],'description':meta['description'],'description_zh':item['summary'],'description_en':EN[item['id']][1],'version':catalog['version'],'author':AUTHOR}
        write(entry,'---\n'+'\n'.join(k+': '+json.dumps(v,ensure_ascii=False) for k,v in fields.items())+'\n---\n\n'+body)
    desc='把备课、课件、命题、错题、学情和教学沟通串成可复用流程，内置十二套技能，交付完整文件与核验记录。'
    assert 40<=len(desc)<=50,len(desc)
    quick=[
      {'zh':'为五年级数学“平均数”备一节40分钟课，交付教案、学案、练习、作业和课件内容，单列答案。','en':'Prepare a 40-minute Grade 5 lesson on the arithmetic mean, with lesson plan, worksheet, practice, homework and slide content.'},
      {'zh':'为七年级一元一次方程编写20分小测，交付原创试题、独立答案、逐点评分和覆盖表。','en':'Create an original 20-point Grade 7 linear-equation quiz with answers, scoring criteria and a coverage table.'},
      {'zh':'分析我上传的脱敏小题成绩，区分空分与零分，报告分母与限制，再安排两周讲评和复测。','en':'Analyze uploaded anonymized item scores, preserve missing values, explain denominators, and plan a two-week review and retest.'},
    ]
    plugin={'name':NAME,'version':VERSION,'description':'A teaching workflow expert with twelve self-contained skills for lesson preparation, assessments, learning evidence and communication.',
      'author':{'name':AUTHOR,'email':'277401656+szcodebox-dotcom@users.noreply.github.com'},'agents':['./agents/'+NAME+'.md'],'expertType':'agent','agentName':NAME,
      'skills':['./skills/'+s['id'] for s in catalog['skills']],'homepage':'https://github.com/szcodebox-dotcom/teacher-workflow-skills','license':'MIT',
      'displayName':{'en':'Teacher Workflow Expert','zh':'教师工作流专家'},'profession':{'en':'Teaching Workflow Consultant','zh':'教师备课与教学工作流专家'},
      'displayDescription':{'en':'Prepare lessons and editable slides, build assessments, analyze anonymized item scores, and create follow-up materials with twelve reusable skills.','zh':desc},
      'avatar':'avatars/expert.png','categoryId':'12-IndustryConsultant','defaultInitPrompt':quick[0],'plugin':NAME,
      'tags':[{'en':'Lesson Preparation','zh':'备课课件'},{'en':'Assessment','zh':'命题订正'},{'en':'Learning Evidence','zh':'学情跟进'}],'quickPrompts':quick}
    write(pkg/'.codebuddy-plugin/plugin.json',json.dumps(plugin,ensure_ascii=False,indent=2)+'\n')
    agent_meta={'name':NAME,'description':plugin['description'],'displayName':plugin['displayName'],'profession':plugin['profession'],'skills':['teacher-workflow-router']}
    write(pkg/('agents/'+NAME+'.md'),'---\n'+'\n'.join(k+': '+json.dumps(v,ensure_ascii=False) for k,v in agent_meta.items())+'\n---\n\n'+(ROOT/'workbuddy/content/expert-instructions.md').read_text(encoding='utf-8'))
    for name in ['README.md','INSTALL.md','VALIDATION.md']:shutil.copy2(ROOT/'workbuddy'/name,pkg/name)
    if (ROOT/'workbuddy/independent-verification.json').is_file():
        (pkg/'validation').mkdir(exist_ok=True)
        shutil.copy2(ROOT/'workbuddy/independent-verification.json',pkg/'validation/independent-verification.json')
    shutil.copy2(ROOT/'workbuddy/content/USAGE.md',pkg/'USAGE.md')
    for name in ['expert.png','expert.svg']:
        (pkg/'avatars').mkdir(exist_ok=True);shutil.copy2(ROOT/'workbuddy/assets'/name,pkg/'avatars'/name)
    for name in ['install_expert.py','verify_package.py','run_examples.py','test_install_expert.py']:
        (pkg/'scripts').mkdir(exist_ok=True);shutil.copy2(ROOT/'workbuddy/tools'/name,pkg/'scripts'/name)
    shutil.copy2(ROOT/'LICENSE',pkg/'LICENSE')
    install=(pkg/'INSTALL.md').read_text(encoding='utf-8')
    prompt=re.search(r'## 安装提示词全文\n\n```text\n(.*?)\n```',install,re.S).group(1)
    write(pkg/'安装提示词.txt',prompt+'\n')
    write(pkg/'requirements-demo.txt',(ROOT/'teacher-slide-deck/requirements.txt').read_text(encoding='utf-8'))
    wb_catalog={'schema_version':1,'expert_version':VERSION,'skill_version':catalog['version'],'skills':[{**s,'path':'skills/'+s['id'],'entrypoint':'skills/'+s['id']+'/SKILL.md'} for s in catalog['skills']]}
    write(pkg/'catalog.json',json.dumps(wb_catalog,ensure_ascii=False,indent=2)+'\n')
    files=sorted(p for p in pkg.rglob('*') if p.is_file())
    manifest={'expert':NAME,'version':VERSION,'skill_version':catalog['version'],'algorithm':'sha256','files':{p.relative_to(pkg).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    write(pkg/'MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    archive=out/(NAME+'-v'+VERSION+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for file in sorted(p for p in pkg.rglob('*') if p.is_file()):
            info=zipfile.ZipInfo(NAME+'/'+file.relative_to(pkg).as_posix(),(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,file.read_bytes())
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    write(out/'WORKBUDDY-SHA256SUMS',sha+'  '+archive.name+'\n')
    print(json.dumps({'expert_directory':str(pkg),'archive':str(archive),'files':len(files)+1,'skills':12,'sha256':sha},ensure_ascii=False,indent=2))
    return pkg


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'dist/workbuddy');build(parser.parse_args().out)
