import base64
import zlib

from colorama import Fore, Style
from src.utils import compute_checksum
import json

class Metadata:
    def __init__(self, logger):
        self.logger = logger
        self.metadata = {}
        
    def generate_metadata(self, original_filename, checksum, file_data, encrypted_data=""):
        """Generate metadata for the encoded file."""
        encoded_encrypted_data = base64.b64encode(encrypted_data).decode('utf-8')
        self.metadata = {
            "original_filename": original_filename,
            "file_size": len(file_data),
            "original_hash": checksum,
            "data": encoded_encrypted_data
        }
        self.logger.info("Metadata generated.")
        return self.metadata

    def to_json(self):
        """Convert metadata to JSON string."""
        return json.dumps(self.metadata)
    
    def encrypt_metadata(self, encryption_handler):
        """Encrypt the metadata JSON using the EncryptionHandler."""
        metadata_json = self.to_json().encode('utf-8')
        encrypted_metadata = encryption_handler.encrypt(metadata_json)
        self.logger.info("Metadata encrypted.")
        return encrypted_metadata
    
    def load_encrypted_metadata(self, encrypted_metadata, encryption_handler):
        """
        Decrypt the compressed and encrypted metadata. 
        Returns the decompressed and decrypted metadata.
        """
        # Decompress the encrypted metadata first
        # decompressed_metadata = zlib.decompress(encrypted_metadata)
        decrypted_metadata_json = encryption_handler.decrypt(encrypted_metadata)
        self.metadata = json.loads(decrypted_metadata_json.decode('utf-8'))
        self.logger.info("Metadata successfully loaded and decrypted.")
        
    def get_info(self):
        """
        Retrieve the basic metadata information such as the original filename, file size, and hash.
        """
        info = {
            "original_filename": self.metadata.get("original_filename"),
            "file_size": self.metadata.get("file_size"),
            "original_hash": self.metadata.get("original_hash"),
            "data": self.metadata.get("data"),
        }
        return info
    
    def print_metadata(self):
        """Print metadata in a human-readable format with colors."""
        print(f"{Fore.YELLOW}=== Metadata Information ==={Style.RESET_ALL}")
        print(f"{Fore.CYAN}Original Filename: {Style.RESET_ALL}{self.metadata.get('original_filename')}")
        print(f"{Fore.CYAN}File Size: {Style.RESET_ALL}{self.metadata.get('file_size')} bytes")
        print(f"{Fore.CYAN}Original File Hash (Checksum): {Style.RESET_ALL}{self.metadata.get('original_hash')}")
        
        # Truncate the encrypted data for better display
        encrypted_data = self.metadata.get("data")
        truncated_encrypted_data = encrypted_data[:60] + "..." if len(encrypted_data) > 60 else encrypted_data
        
        print(f"{Fore.CYAN}Encrypted Data (Base64-encoded, first 60 chars): {Style.RESET_ALL}{truncated_encrypted_data}")
        print(f"{Fore.YELLOW}============================={Style.RESET_ALL}")
        
    def validate_integrity(self, encryption_handler, security_levels):
        """
        Validate the integrity of the extracted file by comparing its checksum with the original hash stored in the metadata.
        """
        decrypted_data = self.metadata.get('data')
        decrypted_data = base64.b64decode(decrypted_data)
        for _ in range(security_levels):
            decrypted_data = encryption_handler.decrypt(decrypted_data)
        
        original_hash = self.metadata.get("original_hash")
        
        extracted_file_hash = compute_checksum(decrypted_data)

        if original_hash == extracted_file_hash:
            self.logger.info(Fore.GREEN + "Integrity check passed: the file is intact." + Style.RESET_ALL)
            return True
        else:
            self.logger.error(Fore.RED + "Integrity check failed: the file has been modified." + Style.RESET_ALL)
            return False