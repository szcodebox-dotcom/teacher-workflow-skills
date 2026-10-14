#!/usr/bin/env python3
"""Draw original repository diagrams as editable SVG and matching PNG images."""
import argparse
import html
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INK = '#132B39'
MUTED = '#4F6573'
BG = '#F4F7F4'
TEAL = '#007E76'
COLORS = {'备课': '#DCEFEB', '命题': '#F7E9C9', '学情': '#E1E8F7', '教研': '#F4E1D9', '工具': '#E9E3F4'}


class Canvas:
    def __init__(self, width, height, font_path):
        self.width, self.height, self.font_path = width, height, font_path
        self.img = Image.new('RGB', (width, height), BG)
        self.draw = ImageDraw.Draw(self.img)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                    f'<rect width="{width}" height="{height}" fill="{BG}"/>']

    def box(self, x, y, w, h, color='#FFFFFF', radius=20, outline=None):
        self.draw.rounded_rectangle((x, y, x + w, y + h), radius, fill=color, outline=outline, width=2)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{color}" stroke="{outline or color}"/>')

    def text(self, x, y, text, size=28, color=INK):
        font = ImageFont.truetype(self.font_path, size)
        self.draw.text((x, y), text, font=font, fill=color, anchor='lt')
        self.svg.append(f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, sans-serif" font-size="{size}" fill="{color}">{html.escape(text)}</text>')

    def arrow(self, x1, y1, x2, y2, color=TEAL):
        self.draw.line((x1, y1, x2, y2), fill=color, width=5)
        self.draw.polygon([(x2, y2), (x2 - 13, y2 - 9), (x2 - 13, y2 + 9)], fill=color)
        self.svg.append(f'<path d="M{x1} {y1} L{x2} {y2} M{x2-13} {y2-9} L{x2} {y2} L{x2-13} {y2+9}" fill="none" stroke="{color}" stroke-width="5"/>')

    def save(self, name):
        folder = ROOT / 'docs/assets'
        folder.mkdir(parents=True, exist_ok=True)
        self.img.save(folder / (name + '.png'))
        (folder / (name + '.svg')).write_text('\n'.join(self.svg + ['</svg>']) + '\n', encoding='utf-8')


def draw_all(font_path):
    items = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))['skills']
    c = Canvas(1600, 1100, font_path)
    c.box(56, 40, 180, 44, TEAL, 12)
    c.text(74, 48, '教师工作流 2.0', 22, '#FFFFFF')
    c.text(56, 118, '12 套教学工作流，把任务变成成品', 56)
    c.text(58, 202, '备课 · 命题 · 学情 · 教研 · 工具   /   独立安装 · 示例完整 · 结果可核验', 28, MUTED)
    summaries = [
        ['教案 + 课件 + 学案', '练习与作业一次配齐'], ['目标与课堂活动对齐', '用检测证据检验目标'],
        ['生成可编辑 PPTX', '附逐页讲者备注'], ['原创题 + 答案 + 评分', '按范围与难度出卷'],
        ['知识点 × 能力矩阵', '核对分值和覆盖'], ['获授权材料提取题目', '逐题保留来源证据'],
        ['识别 → 订正 → 变式', '复测检验掌握情况'], ['统一有效作答口径', '定位知识点薄弱处'],
        ['讲评与弹性练习', '安排两周跟进复测'], ['家长会 · 教研 · 评语', '依据实际课堂事例'],
        ['匹配这十二套流程', '说明顺序和交接材料'], ['把教学方法封装成包', '用案例验证输入输出']]
    for i, item in enumerate(items):
        x, y = 56 + (i % 4) * 376, 284 + (i // 4) * 245
        c.box(x, y, 352, 218)
        c.box(x + 20, y + 18, 65, 34, COLORS[item['category']], 9)
        c.text(x + 30, y + 23, item['category'], 20)
        c.text(x + 285, y + 23, f'{i+1:02d}', 21, MUTED)
        c.text(x + 22, y + 73, item['title'], 35)
        c.text(x + 22, y + 128, summaries[i][0], 23, MUTED)
        c.text(x + 22, y + 164, summaries[i][1], 23, MUTED)
    c.text(58, 1042, 'Teacher Workflow Skills   ·   新版说明 / 示例 / 脚本 / 图示自主编写   ·   MIT', 22, MUTED)
    c.save('overview')

    c = Canvas(1600, 680, font_path)
    c.text(56, 52, '一节课，从输入到复测形成闭环', 52)
    stages = [('输入', '课题 / 学情 / 材料', '明确范围与已有证据'), ('备课', '目标 / 活动 / 检测', '教案、课件与学案对齐'),
              ('教学与测验', '原创试题 / 评分', '保留课堂作答证据'), ('分析与跟进', '知识点表现 / 练习', '把数据转成教学安排')]
    for i, lines in enumerate(stages):
        x = 56 + i * 380
        c.box(x, 180, 350, 212, '#FFFFFF')
        c.text(x + 22, 210, lines[0], 35, TEAL)
        c.text(x + 22, 276, lines[1], 23)
        c.text(x + 22, 327, lines[2], 21, MUTED)
        if i < 3:
            c.arrow(x + 352, 286, x + 377, 286)
    c.box(56, 448, 1488, 155, '#DCEFEB')
    c.text(84, 478, '复测 → 更新教学安排', 32, TEAL)
    c.text(84, 534, '使用同一知识点与明确评分口径，记录有效作答数；证据不足时说明限制，不猜测原因。', 26)
    c.save('workflow')

    c = Canvas(1600, 620, font_path)
    c.text(56, 48, '每套技能的交付结构', 52)
    blocks = [('SKILL.md', '触发边界 · 输入处理', '执行步骤 · 验收条件'), ('SUMMARY.md', '用途 · 输入 · 输出', '依赖 · 调用示例'),
              ('完整示例', '原创教学内容', '题目 · 答案 · 合成数据'), ('运行与检查', '必要脚本 · 行为测试', '结构校验 · 审计记录')]
    for i, (title, a, b) in enumerate(blocks):
        x = 56 + i * 380
        c.box(x, 168, 350, 226)
        c.text(x + 20, 195, title, 34, TEAL)
        c.text(x + 20, 268, a, 24)
        c.text(x + 20, 315, b, 23, MUTED)
    c.box(56, 452, 1488, 100, '#132B39')
    c.text(84, 475, '题库来源留证  ·  学生信息脱敏  ·  工具不足如实报告  ·  测试结论与教学效果分开', 28, '#FFFFFF')
    c.save('package')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', help='Path to a CJK TTF/OTF/TTC font; the font is not redistributed')
    args = parser.parse_args()
    candidates = [args.font, '/System/Library/Fonts/STHeiti Medium.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'C:/Windows/Fonts/msyh.ttc']
    font = next((p for p in candidates if p and Path(p).is_file()), None)
    if font is None:
        parser.error('Provide --font with an installed CJK font')
    draw_all(font)
    print('Generated 3 original SVG diagrams and 3 PNG previews in docs/assets')


if __name__ == '__main__':
    main()
