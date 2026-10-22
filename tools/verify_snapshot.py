#!/usr/bin/env python3
"""Verify the complete imported corpus, modes and pinned Git blob identities."""
import hashlib
import json
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    entries = json.loads((ROOT / 'SNAPSHOT_MANIFEST.json').read_text())
    expected = {e['path'] for e in entries}
    assert len(expected) == len(entries), 'duplicate manifest path'
    actual = {str(p.relative_to(root)) for prefix in ('snapshots', 'research', 'docs/research', 'tools/research')
              for p in (root / prefix).rglob('*') if p.is_file()}
    assert actual == expected, f'corpus inventory mismatch missing={expected-actual} extra={actual-expected}'
    for e in entries:
        p = root / e['path']
        assert not p.is_symlink(), p
        data = p.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        mode = '100755' if p.stat().st_mode & stat.S_IXUSR else '100644'
        assert (len(data), hashlib.sha256(data).hexdigest(), blob, mode) == (e['bytes'], e['sha256'], e['git_blob'], e['mode']), str(p)
    print(f'SNAPSHOT_PASS files={len(entries)} bytes={sum(e["bytes"] for e in entries)} missing=0 extra=0 mismatches=0')


if __name__ == '__main__':
    verify()
