"""Exercise artifact rejection without an Android device or upstream source build."""
import struct
import tempfile
import unittest
from pathlib import Path
from verify_smb_rng import verify


class RngGuardTests(unittest.TestCase):
    def sample(self):
        data = bytearray(256)
        data[:7] = b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HH', data, 16, 2, 183)
        struct.pack_into('<Q', data, 32, 64)
        struct.pack_into('<HH', data, 54, 56, 1)
        struct.pack_into('<IIQQQQQQ', data, 64, 1, 5, 0, 0, 0, 256, 256, 16384)
        data[160:201] = b'SpeedBackup: kernel random source failed\n'
        return data

    def check(self, data, passes=False):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'elf'
            p.write_bytes(data)
            if passes:
                self.assertTrue(verify(p))
            else:
                with self.assertRaises(ValueError):
                    verify(p)

    def test_valid_structure(self):
        self.check(self.sample(), True)

    def test_obsolete_rng(self):
        self.check(self.sample() + b'arc4random data MADV_WIPEONFORK failed')

    def test_missing_rng(self):
        data = self.sample(); data[160:201] = b' ' * 41
        self.check(data)

    def test_truncated_headers(self):
        self.check(self.sample()[:70])

    def test_dynamic(self):
        data = self.sample(); struct.pack_into('<H', data, 16, 3)
        self.check(data)

    def test_interpreter(self):
        data = self.sample(); struct.pack_into('<I', data, 64, 3)
        self.check(data)

    def test_alignment(self):
        data = self.sample(); struct.pack_into('<Q', data, 112, 4096)
        self.check(data)


if __name__ == '__main__':
    unittest.main()
