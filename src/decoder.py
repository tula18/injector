import base64
from src.utils import writefile
from colorama import Fore, Style
from stegano import lsb
from src.metadata import Metadata
from src.encryption import Encryptor
import zlib

class Decoder:
    def __init__(self, image_file, password, security_levels, logger):
        self.image_file = image_file
        self.password = password
        self.security_levels = security_levels
        self.logger = logger
        
        
    def extract_and_decrypt(self):
        """Extract compressed metadata from the image, decompress it, and decrypt the file."""
        self.logger.info(f"{Fore.CYAN}Starting the decoding process with security level {self.security_levels}{Style.RESET_ALL}")
        try:
            # Extract hidden data using LSB steganography
            compressed_metadata_str = self.extract_from_image(self.image_file).encode('latin1')
            print(compressed_metadata_str.hex()[:100])
            print(len(compressed_metadata_str))
            if not compressed_metadata_str:
                self.logger.error("No data was extracted from the image.")
                return

            # Convert the extracted string to bytes for decompression
            # compressed_metadata = compressed_metadata_str.encode('latin1')
            
            # Decompress the metadata
            # encrypted_metadata = zlib.decompress(compressed_metadata)


            
            encryption_handler = Encryptor(self.password, self.logger)
            metadata = Metadata(self.logger)
            metadata.load_encrypted_metadata(compressed_metadata_str, encryption_handler)

            # Get the output filename from metadata
            output_filename = metadata.get_info().get('original_filename')
            
            metadata.print_metadata()
            
            decrypted_data = metadata.get_info().get('data')
            decrypted_data = base64.b64decode(decrypted_data)
            print(type(decrypted_data))
            for i in range(self.security_levels):
                decrypted_data = encryption_handler.decrypt(decrypted_data)
                self.logger.debug(f"Decryption round {i+1} complete.")
            
            print(len(decrypted_data))
            
            writefile(f"output_{output_filename}", decrypted_data, self.logger)
            
            self.logger.info(f"File successfully decoded and saved as output_{output_filename}.")
            return metadata.get_info(), decrypted_data

        except Exception as e:
            self.logger.error(f"Error during decoding: {str(e)}")
        
    def extract_from_image(self, image_file):
        """Extract hidden compressed metadata from the image using steganography."""
        try:
            hidden_data = lsb.reveal(image_file)
            if hidden_data:
                self.logger.info(f"Compressed metadata extracted from image {image_file}.")
                return hidden_data
            else:
                raise ValueError("No hidden data found in the image.")
        except ValueError as ve:
            self.logger.error(f"Error: {ve}")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting data from image: {str(e)}")
            raise