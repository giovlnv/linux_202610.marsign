import asyncio
import contextlib
import io
import json
import os
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from unittest import mock

import marsign
from apple import account


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


class OutputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"MARSIGN_DATA": self.tmp.name, "MARSIGN_HA_WEBHOOK": ""})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def save_apps(self, **days_left):
        now = datetime.now(timezone.utc)
        apps = {f"com.x.{name.lower()}": {"name": name, "version": "1.0", "ipa": "ipas/x.ipa",
                                           "expires": (now + timedelta(days=d, hours=1)).isoformat()}
                for name, d in days_left.items()}
        with open(os.path.join(self.tmp.name, "apps.json"), "w") as f:
            json.dump(apps, f)

    def output(self, command, args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch("device.connect") as connect, \
                mock.patch("requests.post") as post:
            asyncio.run(command(args))
        connect.assert_not_called()
        post.assert_not_called()
        return out.getvalue().splitlines()

    def test_columns_line_up(self):
        lines = marsign.columns([["Familiar", "1.0", "com.a"], ["Athena", "12.3", "com.b"]])
        self.assertEqual(lines, ["Familiar  1.0   com.a", "Athena    12.3  com.b"])
        self.assertEqual(marsign.columns([]), [])

    def test_status_columns_line_up(self):
        self.save_apps(Familiar=5, Athena=3)
        lines = self.output(marsign.cmd_status, Namespace())
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].index("until"), lines[1].index("until"))
        self.assertEqual(lines[0].index("com.x."), lines[1].index("com.x."))

    def test_refresh_nothing_due_singular_day(self):
        self.save_apps(Athena=3)
        lines = self.output(marsign.cmd_refresh, Namespace(force=False, days=1.0, udid=None))
        self.assertTrue(lines[-1].endswith("re-signed at 1 day or less"), lines[-1])

    def test_help_uses_the_script_name_and_puts_everyday_commands_first(self):
        parser = marsign.build_parser()
        self.assertEqual(parser.prog, "marsign.py")
        commands = list(parser._subparsers._group_actions[0].choices)
        self.assertEqual(commands[:4], ["login", "install", "status", "refresh"])
        self.assertEqual(len(commands), 17)

    def test_cancelled_prompt_exits_quietly(self):
        err = io.StringIO()
        with mock.patch("sys.argv", ["marsign.py", "status"]), \
                mock.patch("marsign.cmd_status", side_effect=EOFError), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as exit:
                marsign.main()
        self.assertEqual(exit.exception.code, 130)
        self.assertEqual(err.getvalue().strip(), "Cancelled")

    def test_runtime_errors_read_plainly(self):
        with mock.patch("sys.argv", ["marsign.py", "setup"]), \
                mock.patch("marsign.cmd_setup", side_effect=RuntimeError("zsign failed: bad p12")):
            with self.assertRaises(SystemExit) as exit:
                marsign.main()
        self.assertEqual(exit.exception.code, "\nzsign failed: bad p12")


class CodeTest(unittest.TestCase):
    def test_codes_accept_spaces_and_dashes(self):
        for typed in ("123456", " 123 456 ", "123-456"):
            self.assertEqual(account._clean_code(typed), "123456")
        self.assertEqual(account._clean_code("sms"), "sms")
        self.assertEqual(account._clean_code(""), "")


if __name__ == "__main__":
    unittest.main()
