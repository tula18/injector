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

def writefile(output_file, data, logger):
    with open(output_file, 'wb') as f:
        f.write(data)

def compute_checksum(file_data):
    """Compute checksum of the file data for integrity check."""
    import hashlib
    hash_func = hashlib.sha256()
    hash_func.update(file_data)
    return hash_func.hexdigest()
