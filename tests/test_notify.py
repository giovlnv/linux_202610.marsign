import os
import unittest
from datetime import datetime
from unittest import mock

import notify


class NotifyTest(unittest.TestCase):
    def test_nothing_to_say(self):
        self.assertIsNone(notify.message())

    def test_resigned(self):
        title, body = notify.message(resigned=[("Marscade", datetime(2026, 11, 17))])
        self.assertEqual(title, "Marsign: apps re-signed")
        self.assertEqual(body, "Re-signed Marscade (until 17/11).")

    def test_failure_wins_title_and_keeps_successes(self):
        title, body = notify.message(resigned=[("Marscade", datetime(2026, 11, 17))], failed=["Familiar: boom"])
        self.assertEqual(title, "Marsign: re-sign failed")
        self.assertEqual(body.splitlines(), ["Familiar: boom", "Re-signed Marscade (until 17/11)."])

    def test_unreachable(self):
        title, body = notify.message(unreachable=[("Familiar", 1.5)])
        self.assertEqual(title, "Marsign: iPhone not reachable")
        self.assertIn("Familiar (1.5 days left)", body)

    def test_send_without_webhook_does_nothing(self):
        with mock.patch.dict(os.environ, {"MARSIGN_HA_WEBHOOK": ""}), mock.patch("requests.post") as post:
            self.assertFalse(notify.send("t", "m"))
            post.assert_not_called()

    def test_send_posts_json(self):
        with mock.patch.dict(os.environ, {"MARSIGN_HA_WEBHOOK": "http://ha/api/webhook/x"}), \
                mock.patch("requests.post") as post:
            self.assertTrue(notify.send("t", "m"))
            post.assert_called_once_with("http://ha/api/webhook/x", json={"title": "t", "message": "m"}, timeout=15)


if __name__ == "__main__":
    unittest.main()
