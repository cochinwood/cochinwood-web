import unittest

import build


class CarriedInventoryTests(unittest.TestCase):
    def test_reported_count_matches_every_carried_blob(self):
        expected = 0
        for path in ('files', build.CARRIED_WORKFLOW, *build.CARRIED_ROOT_FILES):
            blobs = build._live_tree(path)
            self.assertIsNotNone(blobs, path)
            expected += len(blobs)
        self.assertEqual(build.carried_live_count(), expected)


if __name__ == '__main__':
    unittest.main()
