import os
from colorama import Fore, Style
from encryption import Encryptor
from metadata import Metadata
from utils import readfile, compute_checksum
from stegano import lsb

class Encoder:
    def __init__(self, input_file, image_file, password, security_levels, logger):
        self.input_file = input_file
        self.image_file = image_file
        self.output_image = f"encoded_{image_file}"
        self.password = password
        self.security_levels = security_levels
        self.logger = logger
        
        self.logger.info(f"{Fore.CYAN}Starting the encoding process with security level {self.security_levels}{Style.RESET_ALL}")

    def encrypt_and_embed(self):
        self.logger.info(f"Reading input file: {self.input_file}")
        
        # Read input file
        file_data = readfile(self.input_file, self.logger)
        
        print(len(file_data))
        
        # Compute file checksum
        checksum = compute_checksum(self.input_file)
        
        # Initialize encryption handler
        encryption = Encryptor(self.password, self.logger)
        
        # Encrypt file data with multiple layers of encryption
        encrypted_data = file_data
        for i in range(self.security_levels):
            encryption.generate_salt()
            encrypted_data = encryption.encrypt(encrypted_data)
            self.logger.debug(f"Encryption round {i+1} complete.")
            
        # Generate metadata
        original_filename = os.path.basename(self.input_file)
        file_size = len(file_data)
        print(original_filename)
        print(file_size)
        metadata = Metadata(self.logger)
        metadata.generate_metadata(original_filename, checksum, file_data, encrypted_data)

        encrypted_metadata = metadata.encrypt_metadata(encryption)
        
        metadata.print_metadata()
        
        # Embed encrypted metadata and data into the image
        self.embed_in_image(encrypted_metadata)
        
        self.logger.info(f"Encoding complete. Encrypted file embedded into {self.output_image}.")


    def embed_in_image(self, encrypted_metadata):
        """Embed the encrypted metadata into the image using steganography."""
        try:
            # Convert the encrypted metadata (bytes) into a string for hiding in the image
            metadata_str = encrypted_metadata.decode('latin1')

            # Use LSB steganography to hide encrypted metadata
            encoded_image = lsb.hide(self.image_file, metadata_str)
            encoded_image.save(self.output_image)

            self.logger.info(f"Encrypted metadata embedded into image {self.output_image}.")
        except Exception as e:
            self.logger.error(f"Error embedding data into image: {str(e)}")