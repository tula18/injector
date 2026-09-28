import os
import tempfile
import unittest
import zipfile

from src.qr_video import QRVideoEncoder, QRVideoDecoder
from src.utils import setup_logger, compute_checksum


class TestQRVideo(unittest.TestCase):
    def setUp(self):
        self.logger = setup_logger(verbose=False)
        self.password = "testpassword"
        self.security_levels = 3
        self.tmp_dir = tempfile.mkdtemp()
        self.input_file = os.path.join(self.tmp_dir, "input.txt")
        self.output_video = os.path.join(self.tmp_dir, "out.mp4")

        # Multi-chunk payload to exercise ordering/reassembly across several QR frames.
        self.original = ("This is a test file for QR video encoding. " * 200).encode("utf-8")
        with open(self.input_file, "wb") as f:
            f.write(self.original)

    def test_round_trip(self):
        QRVideoEncoder(self.input_file, self.output_video, self.password,
                       self.security_levels, self.logger).build_video()
        self.assertTrue(os.path.exists(self.output_video))
        self.assertGreater(os.path.getsize(self.output_video), 0)

        info, data = QRVideoDecoder(self.output_video, self.password, self.security_levels,
                                    self.logger, out_dir=self.tmp_dir).extract_and_decrypt()

        self.assertEqual(info["original_filename"], "input.txt")
        self.assertEqual(data, self.original)
        self.assertEqual(compute_checksum(data), compute_checksum(self.original))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "output_input.txt")))

    def test_zip_to_folder_round_trip(self):
        zip_path = os.path.join(self.tmp_dir, "out.zip")
        QRVideoEncoder(self.input_file, zip_path, self.password, self.security_levels,
                       self.logger, output_format="zip").build()

        self.assertTrue(os.path.exists(zip_path))
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".png")]
            self.assertGreater(len(names), 0)
            # Unzip the PNGs into a folder, then decode from that folder.
            extract_dir = os.path.join(self.tmp_dir, "qrs")
            os.makedirs(extract_dir, exist_ok=True)
            zf.extractall(extract_dir)

        info, data = QRVideoDecoder(extract_dir, self.password, self.security_levels,
                                    self.logger, out_dir=self.tmp_dir).extract_and_decrypt()

        self.assertEqual(info["original_filename"], "input.txt")
        self.assertEqual(data, self.original)
        self.assertEqual(compute_checksum(data), compute_checksum(self.original))

    def test_wrong_password_fails(self):
        QRVideoEncoder(self.input_file, self.output_video, self.password,
                       self.security_levels, self.logger).build_video()
        with self.assertRaises(Exception):
            QRVideoDecoder(self.output_video, "wrongpassword", self.security_levels,
                           self.logger, out_dir=self.tmp_dir).extract_and_decrypt()

    def tearDown(self):
        for name in os.listdir(self.tmp_dir):
            try:
                os.remove(os.path.join(self.tmp_dir, name))
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
