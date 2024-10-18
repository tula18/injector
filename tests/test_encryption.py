import unittest
import os
from src.encryption import Encryptor
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

class TestEncryptor(unittest.TestCase):

    def setUp(self):
        self.password = "test_password"
        self.encryptor = Encryptor(self.password)

    def test_encryption_decryption(self):
        original_data = b"This is a test message."
        encrypted_data = self.encryptor.encrypt(original_data)
        decrypted_data = self.encryptor.decrypt(encrypted_data)
        self.assertEqual(original_data, decrypted_data)

    def test_different_passwords(self):
        original_data = b"This is a test message."
        encrypted_data = self.encryptor.encrypt(original_data)
        
        wrong_password_encryptor = Encryptor("wrong_password")
        with self.assertRaises(Exception):
            wrong_password_encryptor.decrypt(encrypted_data)

    def test_data_integrity(self):
        original_data = b"This is a test message."
        encrypted_data = self.encryptor.encrypt(original_data)
        
        # Tamper with the encrypted data
        tampered_data = bytearray(encrypted_data)
        tampered_data[50] ^= 1  # Flip a bit
        
        with self.assertRaises(Exception):
            self.encryptor.decrypt(bytes(tampered_data))

    def test_unique_encryption(self):
        data = b"This is a test message."
        encryptor1 = Encryptor(self.password)
        encryptor2 = Encryptor(self.password)
        encrypted1 = encryptor1.encrypt(data)
        encrypted2 = encryptor2.encrypt(data)
        self.assertNotEqual(encrypted1, encrypted2)

    def test_key_derivation(self):
        password = b"test_password"
        salt1 = os.urandom(16)
        salt2 = os.urandom(16)
        
        kdf1 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt1,
            iterations=100000,
            backend=default_backend()
        )
        kdf2 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt2,
            iterations=100000,
            backend=default_backend()
        )
        
        key1 = kdf1.derive(password)
        key2 = kdf2.derive(password)
        
        self.assertEqual(len(key1), 32)  # 256 bits
        self.assertNotEqual(key1, key2)  # Different salts should produce different keys

    def test_long_message(self):
        long_message = b"A" * 1000000  # 1 MB of data
        encrypted_data = self.encryptor.encrypt(long_message)
        decrypted_data = self.encryptor.decrypt(encrypted_data)
        self.assertEqual(long_message, decrypted_data)

    def test_empty_message(self):
        empty_message = b""
        encrypted_data = self.encryptor.encrypt(empty_message)
        decrypted_data = self.encryptor.decrypt(encrypted_data)
        self.assertEqual(empty_message, decrypted_data)

if __name__ == '__main__':
    unittest.main()