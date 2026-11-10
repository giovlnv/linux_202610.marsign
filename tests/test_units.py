import unittest

import marsign


class UnitsTest(unittest.TestCase):
    def test_timer_time(self):
        _, timer = marsign.units("03:00", credential=False)
        self.assertIn("OnCalendar=*-*-* 03:00:00", timer)
        self.assertIn("Persistent=true", timer)

    def test_credential_only_when_saved(self):
        service, _ = marsign.units("03:00", credential=False)
        self.assertNotIn("LoadCredentialEncrypted", service)
        service, _ = marsign.units("03:00", credential=True)
        self.assertIn("LoadCredentialEncrypted=marsign-apple", service)
        self.assertIn("refresh", service.splitlines()[-2])


if __name__ == "__main__":
    unittest.main()
