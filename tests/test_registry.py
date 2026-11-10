import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MARSIGN_DATA"] = self.tmp.name
        import registry
        self.registry = registry

    def tearDown(self):
        os.environ.pop("MARSIGN_DATA")
        self.tmp.cleanup()

    def test_record_stores_relative_path(self):
        ipa = Path(self.tmp.name) / "app.ipa"
        ipa.write_bytes(b"ipa")
        expires = datetime(2026, 11, 17, tzinfo=timezone.utc)
        self.registry.record(ipa, {"bundle_id": "com.x", "name": "X", "version": "1"}, "com.x.TEAM", expires)
        entry = self.registry.load()["com.x.TEAM"]
        self.assertEqual(entry["ipa"], "ipas/com.x.ipa")
        self.assertEqual(self.registry.ipa_path(entry), Path(self.tmp.name) / "ipas" / "com.x.ipa")
        self.assertTrue(self.registry.ipa_path(entry).is_file())

    def test_moved_absolute_path_falls_back_to_data_folder(self):
        entry = {"ipa": "/home/someone/.local/share/Marsign/ipas/com.x.ipa"}
        self.assertEqual(self.registry.ipa_path(entry), Path(self.tmp.name) / "ipas" / "com.x.ipa")

    def test_days_left(self):
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        entry = {"expires": (now + timedelta(days=2, hours=12)).isoformat()}
        self.assertAlmostEqual(self.registry.days_left(entry, now), 2.5)


if __name__ == "__main__":
    unittest.main()
