import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import build


class SitemapLastmodTests(unittest.TestCase):
    def git(self, root, *args, date=None):
        env = os.environ.copy()
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(('git', *args), cwd=root, env=env, check=True,
                       capture_output=True, text=True)

    def write_posts(self, root, first, second):
        posts = [
            {'slug': 'unchanged-post', 'html': first, 'words': 1},
            {'slug': 'changed-post', 'html': second, 'words': 1},
        ]
        (root / 'posts.json').write_text(
            json.dumps(posts, indent=1, ensure_ascii=False) + '\n',
            encoding='utf-8', newline='\n')

    def test_one_json_record_change_does_not_redate_the_other(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.git(root, 'init', '-q')
            self.git(root, 'config', 'user.name', 'Sitemap Test')
            self.git(root, 'config', 'user.email', 'sitemap@example.invalid')
            self.write_posts(root, '<p>same</p>', '<p>before</p>')
            self.git(root, 'add', 'posts.json')
            self.git(root, 'commit', '-qm', 'initial posts', date='2026-08-01T12:00:00+0530')

            self.write_posts(root, '<p>same</p>', '<p>after</p>')
            self.git(root, 'add', 'posts.json')
            self.git(root, 'commit', '-qm', 'change one post', date='2026-09-02T12:00:00+0530')

            dates = build.git_json_record_dates(
                'posts.json', ('unchanged-post', 'changed-post'), root=str(root))
            self.assertEqual(dates['unchanged-post'], '2026-08-01')
            self.assertEqual(dates['changed-post'], '2026-09-02')


if __name__ == '__main__':
    unittest.main()
