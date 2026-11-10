import os
import platform
import tempfile
import unittest


class PairingHostTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MARSIGN_DATA"] = self.tmp.name
        import device
        self.device = device

    def tearDown(self):
        os.environ.pop("MARSIGN_DATA")
        self.tmp.cleanup()

    def test_defaults_to_this_machine(self):
        self.assertEqual(self.device.pairing_host(), platform.node())

    def test_saved_host_is_used(self):
        self.device.save_pairing_host("mars-marsbook")
        self.assertEqual(self.device.pairing_host(), "mars-marsbook")


if __name__ == "__main__":
    unittest.main()
