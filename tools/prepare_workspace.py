#!/usr/bin/env python3
"""Prepare an exact original library checkout for a research snapshot."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('commit')
    parser.add_argument('destination', type=Path)
    parser.add_argument('--source', default='https://github.com/alex-1974/concurrency-d.git')
    args = parser.parse_args()
    refs = json.loads((ROOT / 'SOURCE_REFS.json').read_text())
    assert args.commit in {r['commit'] for r in refs}, 'commit is not an inventoried snapshot'
    assert not args.destination.exists(), 'destination must not exist'
    subprocess.run(['git', 'clone', '--no-checkout', '--', args.source, str(args.destination)], check=True)
    subprocess.run(['git', '-C', str(args.destination), 'checkout', '--detach', args.commit], check=True)
    manifest = json.loads((ROOT / 'SNAPSHOT_MANIFEST.json').read_text())
    selected = [e for e in manifest if e['path'].startswith('snapshots/' + args.commit + '/')]
    for e in selected:
        p = args.destination / e['source_path']
        assert p.read_bytes() == (ROOT / e['path']).read_bytes(), e['source_path']
        assert bool(p.stat().st_mode & 0o100) == (e['mode'] == '100755'), e['source_path']
    print(f'WORKSPACE_PASS commit={args.commit} verified_research_files={len(selected)}; experiments not executed')


if __name__ == '__main__':
    main()
