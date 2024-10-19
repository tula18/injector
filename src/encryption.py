import os
import sys
from colorama import Fore, Style
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

class Encryptor:
    def __init__(self, password: str, logger):
        self.password = password.encode()
        self.salt = os.urandom(16)
        self.iv = os.urandom(12)
        self.logger = logger
        self.logger.info(f"{Fore.CYAN}Starting the encrypting process")
    
    def generate_salt(self):
        self.salt = os.urandom(16)

    def _derive_key(self) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(self.password)

    def encrypt(self, data: bytes) -> bytes:
        try:
            key = self._derive_key()
            cipher = Cipher(algorithms.AES(key), modes.GCM(self.iv), backend=default_backend())
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(data) + encryptor.finalize()
            return self.salt + self.iv + encryptor.tag + ciphertext
        except Exception as e:
            self.logger.error(f"{Fore.RED}Error during encryption: {e}{Style.RESET_ALL}")
            raise

    def decrypt(self, encrypted_data: bytes) -> bytes:
        self.salt = encrypted_data[:16]
        self.iv = encrypted_data[16:28]
        tag = encrypted_data[28:44]
        ciphertext = encrypted_data[44:]
        
        key = self._derive_key()
        cipher = Cipher(algorithms.AES(key), modes.GCM(self.iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
        

# Usage example
if __name__ == "__main__":
    password = "supersecretpassword"
    encryptor = Encryptor(password)
    
    original_data = b"This is a secret message."
    encrypted_data = encryptor.encrypt(original_data)
    decrypted_data = encryptor.decrypt(encrypted_data)
    
    print(f"Original: {original_data}")
    print(f"Encrypted: {encrypted_data}")
    print(f"Decrypted: {decrypted_data}")
    assert original_data == decrypted_data, "Decryption failed"