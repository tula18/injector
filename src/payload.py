import base64
import os

from colorama import Fore, Style

from src.encryption import Encryptor
from src.metadata import Metadata
from src.utils import readfile, writefile, compute_checksum


def build_encrypted_payload(input_file, password, security_levels, logger):
    """Read a file, encrypt it with multiple layers, wrap it in encrypted metadata,
    and return the single encrypted_metadata byte-string.

    This is the same payload the image path embeds via LSB; here it is returned so a
    different carrier (e.g. a QR-code video) can store it. Mirrors Encoder.encrypt_and_embed.
    """
    logger.info(f"{Fore.CYAN}Building encrypted payload from {input_file}{Style.RESET_ALL}")

    file_data = readfile(input_file, logger)
    if file_data is None:
        raise FileNotFoundError(f"Input file {input_file} not found or unreadable")

    checksum = compute_checksum(file_data)

    encryption = Encryptor(password, logger)

    encrypted_data = file_data
    for i in range(security_levels):
        encryption.generate_salt()
        encrypted_data = encryption.encrypt(encrypted_data)
        logger.debug(f"Encryption round {i + 1} complete.")

    original_filename = os.path.basename(input_file)
    metadata = Metadata(logger)
    metadata.generate_metadata(original_filename, checksum, file_data, encrypted_data)

    encrypted_metadata = metadata.encrypt_metadata(encryption)
    logger.info(f"Encrypted payload built ({len(encrypted_metadata)} bytes).")
    return encrypted_metadata


def recover_file_from_payload(encrypted_metadata, password, security_levels, logger, out_dir="."):
    """Reverse of build_encrypted_payload: decrypt the metadata blob, peel off the
    encryption layers, write the recovered file to out_dir and return (info, data).
    Mirrors Decoder.extract_and_decrypt.
    """
    encryption_handler = Encryptor(password, logger)
    metadata = Metadata(logger)
    metadata.load_encrypted_metadata(encrypted_metadata, encryption_handler)

    info = metadata.get_info()
    output_filename = info.get('original_filename')

    decrypted_data = base64.b64decode(info.get('data'))
    for i in range(security_levels):
        decrypted_data = encryption_handler.decrypt(decrypted_data)
        logger.debug(f"Decryption round {i + 1} complete.")

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"output_{output_filename}")
    writefile(out_path, decrypted_data, logger)
    logger.info(f"File recovered and saved as {out_path}.")
    return info, decrypted_data
