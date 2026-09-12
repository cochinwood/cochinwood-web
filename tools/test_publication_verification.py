import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('publication', Path(__file__).with_name('verify_publication.py'))
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


class PublicationProofTests(unittest.TestCase):
    def test_exact_binary_text_and_unstaged_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dist, pub = root / 'dist', root / 'pub'
            dist.mkdir(); pub.mkdir()
            subprocess.run(['git', 'init', '-q', str(pub)], check=True)
            subprocess.run(['git', '-C', str(pub), 'config', 'core.autocrlf', 'false'], check=True)
            for name, data in [('index.html', b'<h1>Reviewed</h1>\n'), ('photo.bin', bytes(range(256)))]:
                (dist / name).write_bytes(data); (pub / name).write_bytes(data)
            subprocess.run(['git', '-C', str(pub), 'add', '.'], check=True)
            self.assertTrue(publication.verify(dist, pub)['ok'])
            # Unstaged bytes are not what git will publish; compare to the index.
            (pub / 'index.html').write_text('Unstaged', encoding='utf-8')
            self.assertTrue(publication.verify(dist, pub)['ok'])
            subprocess.run(['git', '-C', str(pub), 'add', '.'], check=True)
            self.assertEqual(publication.verify(dist, pub)['different_bytes'], ['index.html'])
            (dist / 'new.html').write_text('Missing from publication', encoding='utf-8')
            (pub / 'unreviewed.html').write_text('Unexpected', encoding='utf-8')
            subprocess.run(['git', '-C', str(pub), 'add', '.'], check=True)
            report = publication.verify(dist, pub)
            self.assertFalse(report['ok'])
            self.assertEqual(report['missing_in_publication'], ['new.html'])
            self.assertEqual(report['extra_in_publication'], ['unreviewed.html'])


if __name__ == '__main__':
    unittest.main()
