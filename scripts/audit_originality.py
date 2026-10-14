#!/usr/bin/env python3
"""Compare entrypoint prose to a user-provided baseline; not a plagiarism verdict."""
import argparse
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def prose(path):
    text = path.read_text(encoding='utf-8')
    text = re.sub(r'^---\n.*?\n---', '', text, count=1, flags=re.S)
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'`[^`]*`', '', text)
    text = re.sub(r'!?\[([^\]\n]*)\]\([^)\n]+\)', r'\1', text)
    return ''.join(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', text))


def compare(a, b):
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    longest = matcher.find_longest_match(0, len(a), 0, len(b))
    # A 24-character shared fragment is a review signal, never an automatic verdict.
    fragments = [a[x.a:x.a+x.size] for x in matcher.get_matching_blocks() if x.size >= 24]
    return {'longest_contiguous_characters': longest.size,
            'shared_fragments_24_plus': fragments,
            'sequence_similarity': round(matcher.ratio(), 4)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    items = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))['skills']
    new = {s['id']: prose(ROOT / s['path'] / 'SKILL.md') for s in items}
    baseline = []
    for item in items:
        old_path = args.baseline_root / item['legacy_id'] / 'SKILL.md'
        baseline.append({'skill': item['id'], 'legacy_id': item['legacy_id'],
                         'baseline_sha256': hashlib.sha256(old_path.read_bytes()).hexdigest(),
                         **compare(prose(old_path), new[item['id']])})
    peers = []
    for i, item in enumerate(items):
        for other in items[i+1:]:
            result = compare(new[item['id']], new[other['id']])
            if result['shared_fragments_24_plus']:
                peers.append({'a': item['id'], 'b': other['id'], **result})
    report = {'date': '2026-10-14', 'scope': 'SKILL.md prose after removing YAML, fenced/inline code, link destinations and punctuation',
              'method': 'SequenceMatcher; 24-character shared fragments are review signals',
              'limitations': 'Local baseline and intra-package comparison only; cannot prove global uniqueness or legal authorship',
              'baseline_comparisons': baseline, 'peer_review_signals': peers}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'baseline_entries': len(baseline), 'peer_signals': len(peers),
                      'baseline_fragments': sum(len(x['shared_fragments_24_plus']) for x in baseline)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
