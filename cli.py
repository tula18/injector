import argparse
from colorama import Fore, Style, init
from src.encoder import Encoder
from src.decoder import Decoder
from src.encryption import Encryptor
from src.metadata import Metadata
from src.utils import setup_logger

# Initialize colorama
init(autoreset=True)

# Pretty separators and ASCII art for headers
PRETTY_HEADER = f"{Fore.CYAN}{'*' * 10} SecureStegCLI {Fore.CYAN}{'*' * 10}\n"

def print_header():
    print(PRETTY_HEADER)
    print(f"{Fore.YELLOW}SecureStegCLI - Secure file encoding using steganography and multi-layer encryption.{Style.RESET_ALL}")
    print(f"For more information on a specific command, use --help with the command name.\n")
    print("-" * 50)

def main():
    print_header()
    
    parser = argparse.ArgumentParser(
        description=f'{Fore.YELLOW}SecureStegCLI: A tool for securely encoding files in images using encryption and steganography.{Style.RESET_ALL}',
        epilog=f'{Fore.CYAN}For more details on a specific command, use the --help flag after the command.{Style.RESET_ALL}',
        formatter_class=argparse.RawTextHelpFormatter  # Use raw text formatter for better formatting of help messages
    )
    
    parser.add_argument('--verbose', action='store_true', help=f'{Fore.GREEN}Enable verbose logging for detailed output.{Style.RESET_ALL}')

    subparsers = parser.add_subparsers(dest='command', required=True, help=f"{Fore.CYAN}Available Commands{Style.RESET_ALL}")

    
    # Encode command
    encode_parser = subparsers.add_parser('encode', help=f"{Fore.CYAN}Encode a file into an image using steganography.{Style.RESET_ALL}")
    encode_parser.add_argument('input_file', type=str, help=f"{Fore.GREEN}The file to be encoded into the image.{Style.RESET_ALL}")
    encode_parser.add_argument('image_file', type=str, help=f"{Fore.GREEN}The image file to hide the encoded data in.{Style.RESET_ALL}")
    encode_parser.add_argument('--password', required=True, type=str, help=f"{Fore.GREEN}Password for encrypting the data.{Style.RESET_ALL}")
    encode_parser.add_argument('--security-levels', type=int, default=5, help=f"{Fore.GREEN}Number of encryption levels (default: 5).{Style.RESET_ALL}")

    # Decode command
    decode_parser = subparsers.add_parser('decode', help=f"{Fore.CYAN}Decode and extract the hidden file from an image.{Style.RESET_ALL}")
    decode_parser.add_argument('image_file', type=str, help=f"{Fore.GREEN}The image file to extract the encoded data from.{Style.RESET_ALL}")
    decode_parser.add_argument('--password', required=True, type=str, help=f"{Fore.GREEN}Password for decrypting the data.{Style.RESET_ALL}")
    decode_parser.add_argument('--security-levels', type=int, default=5, help=f"{Fore.GREEN}Number of encryption levels (default: 5).{Style.RESET_ALL}")

    # Info command
    info_parser = subparsers.add_parser('info', help=f"{Fore.CYAN}Retrieve metadata info from an encoded image.{Style.RESET_ALL}")
    info_parser.add_argument('image_file', type=str, help=f"{Fore.GREEN}The image file containing the encoded metadata.{Style.RESET_ALL}")
    info_parser.add_argument('--password', required=True, type=str, help=f"{Fore.GREEN}Password to decrypt and access metadata.{Style.RESET_ALL}")

    # Integrity command
    integrity_parser = subparsers.add_parser('integrity', help=f"{Fore.CYAN}Check the integrity of the encoded file.{Style.RESET_ALL}")
    integrity_parser.add_argument('image_file', type=str, help=f"{Fore.GREEN}The image file containing the hidden data.{Style.RESET_ALL}")
    integrity_parser.add_argument('--password', required=True, type=str, help=f"{Fore.GREEN}Password to check file integrity.{Style.RESET_ALL}")
    integrity_parser.add_argument('--security-levels', type=int, default=5, help=f"{Fore.GREEN}Number of encryption levels (default: 5).{Style.RESET_ALL}")
    
    args = parser.parse_args()

    # Set up the logger
    logger = setup_logger(verbose=args.verbose)

    if args.command == 'encode':
        encoder = Encoder(args.input_file, args.image_file, "tst/output.png", args.password, args.security_levels, logger)
        encoder.encrypt_and_embed()
    elif args.command == 'decode':
        decoder = Decoder(args.image_file, args.password, args.security_levels, logger)
        decoder.extract_and_decrypt()
    elif args.command == 'info':
        logger.info(f"{Fore.CYAN}Retrieving metadata information{Style.RESET_ALL}")
        metadata = Metadata(logger)
        encryptor = Encryptor(args.password, logger)
        decoder = Decoder(args.image_file, args.password, 5, logger)
        compressed_metadata_str = decoder.extract_from_image(args.image_file)
        compressed_metadata = compressed_metadata_str.encode('latin1')
        metadata.load_encrypted_metadata(compressed_metadata, encryptor)

        metadata.print_metadata()
    elif args.command == 'integrity':
        logger.info(f"{Fore.CYAN}Checking file integrity{Style.RESET_ALL}")
        metadata = Metadata(logger)
        encryptor = Encryptor(args.password, logger)
        decoder = Decoder(args.image_file, args.password, 5, logger)
        compressed_metadata_str = decoder.extract_from_image(args.image_file)
        compressed_metadata = compressed_metadata_str.encode('latin1')
        metadata.load_encrypted_metadata(compressed_metadata, encryptor)
        metadata.validate_integrity(encryptor, args.security_levels)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
