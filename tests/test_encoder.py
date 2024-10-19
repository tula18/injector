import unittest
import os
from src.encoder import Encoder
from src.utils import setup_logger
from src.metadata import Metadata
from src.encryption import Encryptor

class TestEncoder(unittest.TestCase):
    def setUp(self):
        self.logger = setup_logger(verbose=True)
        self.password = "testpassword"
        self.image_file = "images.png"
        self.output_image = "encoded_images.png"
        self.input_file = "input.txt"
        self.security_levels = 3
        self.encoder = Encoder(self.input_file, self.image_file, self.password, self.security_levels, self.logger)

        # Create a small input file for testing
        with open(self.input_file, 'w') as f:
            f.write("This is a test file for encoding.")

    def test_encrypt_and_embed(self):
        """Test the encryption and embedding process."""
        self.encoder.encrypt_and_embed()
        self.assertTrue(os.path.exists(self.output_image))

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.input_file):
            os.remove(self.input_file)
        if os.path.exists(self.output_image):
            os.remove(self.output_image)

if __name__ == '__main__':
    unittest.main()
