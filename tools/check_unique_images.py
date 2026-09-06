"""Release gate: no missing, unreviewed or multiply-owned editorial photographs."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from unique_imagery import read_manifest, validate_ownership


def scope_report(root, scope='full'):
    owners = read_manifest(root)['owners']
    included = set(owners)
    errors = []
    if scope == 'blog':
        taxonomy = json.loads((root / 'content/blog/topics.json').read_text(encoding='utf-8'))['posts']
        included = {'/blogs/post/' + slug for slug in taxonomy}
        text = {'/blogs/post/' + slug for slug, topic in taxonomy.items() if topic == 'city-supply'}
        if len(included) != 157 or len(text) != 109:
            errors.append('Blog scope must contain exactly157 existing articles and109 location guides')
        if included - set(owners):
            errors.append('Blog owner assignments missing: ' + ', '.join(sorted(included - set(owners))))
        for owner in included & set(owners):
            if (owners[owner].get('kind') == 'text_guide') != (owner in text):
                errors.append(owner + ': expected text-guide/photo mode does not match taxonomy')
        excluded = set(owners) - included
        if len(excluded) != 28 or any(owners[p].get('category') != 'country-export' for p in excluded):
            errors.append('Blog scope may exclude only the28 declared country-export owners')
    elif scope != 'full':
        raise ValueError('Unknown imagery scope')
    if len(owners) != 185:
        errors.append('Expected185 declared owner assignments')
    full_errors = validate_ownership(root)
    errors += full_errors if scope == 'full' else validate_ownership(root, required_owners=included)
    excluded = sorted(set(owners) - included)
    return {'scope': scope, 'passed': not errors, 'required_owners': len(included),
            'included_owners': sorted(included), 'excluded_owners': excluded,
            'excluded_pending_owners': [p for p in excluded if owners[p].get('status') != 'approved'],
            'full_migration_complete': not full_errors and len(owners) == 185,
            'full_migration_error_count': len(full_errors), 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--scope', choices=['full', 'blog'], default='full',
                        help='Default validates all185; blog explicitly reports28 deferred export owners')
    args = parser.parse_args()
    report = scope_report(args.root, args.scope)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return not report['passed']


if __name__ == '__main__':
    raise SystemExit(main())
