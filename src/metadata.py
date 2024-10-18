import base64

from colorama import Fore, Style
from utils import compute_checksum
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