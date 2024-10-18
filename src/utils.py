import logging
import os

def setup_logger(verbose=False):
    """Sets up the logger with the appropriate level of verbosity."""
    logger = logging.getLogger('securestegcli')
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    logger.addHandler(handler)
    return logger

def readfile(input_file, logger):
    if not os.path.exists(input_file):
        logger.error(f"Input file {input_file} not found!")
        return
    with open(input_file, 'rb') as f:
        data = f.read()
    return data

def compute_checksum(file_path):
    """Compute checksum of the file for integrity check."""
    import hashlib
    hash_func = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()
