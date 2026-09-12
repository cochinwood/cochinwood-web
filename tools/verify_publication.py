"""Prove a staged/committed publication contains exactly the reviewed build bytes.

python tools/verify_publication.py dist PUBLICATION_WORKTREE --output proof.json
python tools/verify_publication.py dist PUBLICATION_WORKTREE --ref HEAD --output proof.json

Read-only except for the explicitly requested JSON receipt. Exit 1 on any mismatch.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def verify(dist, publication, ref=None):
    dist = Path(dist).resolve()
    publication = Path(publication).resolve()
    if not dist.is_dir():
        raise ValueError('Build directory does not exist')
    algorithm = git(publication, 'rev-parse', '--show-object-format').decode().strip()
    tracked = {}
    raw = (git(publication, 'ls-tree', '-rz', ref) if ref
           else git(publication, 'ls-files', '--stage', '-z'))
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        meta, name = entry.split(b'\t', 1)
        mode, middle, last = meta.decode().split()
        oid = last if ref else middle
        if mode not in ('100644', '100755') or (not ref and last != '0'):
            raise ValueError('Publication contains a non-file or unmerged entry: ' + name.decode())
        tracked[name.decode()] = oid
    built, inventory = {}, {}
    for path in sorted(dist.rglob('*')):
        if path.is_symlink():
            raise ValueError('Build contains a symlink: ' + str(path))
        if not path.is_file():
            continue
        data = path.read_bytes()
        name = path.relative_to(dist).as_posix()
        built[name] = hashlib.new(algorithm, b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        inventory[name] = hashlib.sha256(data).hexdigest()
    if not built:
        raise ValueError('Build directory is empty')
    missing = sorted(built.keys() - tracked.keys())
    extra = sorted(tracked.keys() - built.keys())
    changed = sorted(name for name in built.keys() & tracked.keys() if built[name] != tracked[name])
    return {
        'ok': not (missing or extra or changed),
        'verification_tool_commit': git(Path(__file__).resolve().parents[1], 'rev-parse', 'HEAD').decode().strip(),
        'publication_ref': ref or 'staged index',
        'publication_commit': git(publication, 'rev-parse', ref + '^{commit}').decode().strip() if ref else None,
        'build_files': len(built), 'publication_files': len(tracked),
        'missing_in_publication': missing, 'extra_in_publication': extra,
        'different_bytes': changed, 'sha256': inventory,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dist')
    parser.add_argument('publication')
    parser.add_argument('--ref')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = verify(args.dist, args.publication, args.ref)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'sha256'}, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
