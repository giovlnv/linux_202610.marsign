import asyncio
import io
import os
import tempfile
import unittest
from argparse import Namespace
from unittest import mock

import marsign


class UninstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"MARSIGN_DATA": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_uninstall(self, yes=False, tty=False, answer=""):
        args = Namespace(bundle_id="com.x.app", yes=yes, udid=None)
        with mock.patch("sys.stdin", io.StringIO(answer)), mock.patch("sys.stdin.isatty", return_value=tty), \
                mock.patch("builtins.input", return_value=answer), mock.patch("device.connect") as connect:
            try:
                asyncio.run(marsign.cmd_uninstall(args))
            except SystemExit as e:
                return str(e), connect
        return None, connect

    def test_without_terminal_needs_yes(self):
        message, connect = self.run_uninstall()
        self.assertIn("--yes", message)
        connect.assert_not_called()

    def test_declined_keeps_the_app(self):
        message, connect = self.run_uninstall(tty=True, answer="n")
        self.assertEqual(message, "Not removed")
        connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
