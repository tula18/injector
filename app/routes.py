import os
import shutil
from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename
from src.encoder import Encoder
from src.decoder import Decoder
from src.encryption import Encryptor
from src.metadata import Metadata
from src.utils import setup_logger

main = Blueprint('main', __name__)

UPLOAD_FOLDER = 'app/uploads'
ALLOWED_EXTENSIONS = {'png', 'txt', 'jpeg', 'jpg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@main.route('/encode', methods=['POST'])
def encode():
    # Check if the request has the file and image parts
    if 'file' not in request.files or 'image' not in request.files:
        return "Error: Both file and image are required", 400  # Return an error response

    file = request.files['file']
    image = request.files['image']
    password = request.form.get('password')

    # Check if all necessary parts are provided
    if not password:
        return "Error: Password is required", 400

    
    # Ensure that the uploaded files are valid
    if file and image and allowed_file(image.filename):
        file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        image_path = os.path.join(UPLOAD_FOLDER, secure_filename(image.filename))
        output_filename = secure_filename(f'encoded_{image.filename}')
        output_path = os.path.join("uploads", output_filename)
        print(output_path)

        # Save the uploaded files
        file.save(file_path)
        image.save(image_path)

        try:
            # Setup logger and perform encoding
            logger = setup_logger(verbose=True)
            encoder = Encoder(file_path, image_path, output_path, password, 5, logger)
            encoder.encrypt_and_embed()
            
            # After encoding, send the resulting image as a download
            return send_file(output_path, as_attachment=True)

        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            return f"Error during encoding: {str(e)}", 500

    # If the file types are not allowed
    return "Error: Invalid file or image format", 400

@main.route('/decode', methods=['POST'])
def decode():
    if 'image' not in request.files:
        return "Error: image are required", 400

    image = request.files['image']
    password = request.form.get('password')
    output_filename = 'decoded_file.txt'

    if image and allowed_file(image.filename):
        image_path = os.path.join(UPLOAD_FOLDER, secure_filename(image.filename))

        image.save(image_path)

        try:
            logger = setup_logger(verbose=True)
            decoder = Decoder(image_path, password, 5, logger)
            metadata, data = decoder.extract_and_decrypt()
            print(metadata.get('original_filename'))
            
            output_path = os.path.join("uploads", metadata.get('original_filename'))
            
            return send_file(output_path, as_attachment=True)
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            return f"Error during encoding: {str(e)}", 500
        
@main.route('/info', methods=['POST'])
def info():
    if 'image' not in request.files:
        flash('No image uploaded', 'error')
        

    image = request.files['image']
    password = request.form.get('password')

    if not password:
        flash('Password is required to retrieve metadata', 'error')
        

    if image and allowed_file(image.filename):
        try:
            # Save the uploaded image
            image_path = os.path.join(UPLOAD_FOLDER, secure_filename(image.filename))
            image.save(image_path)

            try:
                # Setup logger and extract metadata
                logger = setup_logger(verbose=True)
                decoder = Decoder(image_path, password, 5, logger)

                # Extract the hidden metadata from the image
                compressed_metadata_str = decoder.extract_from_image(image_path)
                if not compressed_metadata_str:
                    flash('No metadata found in the image.', 'error')
                    

                # Convert metadata from base64 to bytes
                compressed_metadata = compressed_metadata_str.encode('latin1')

                # Initialize metadata object and load the metadata
                metadata = Metadata(logger)
                encryption_handler = Encryptor(password, logger)
                
                metadata.load_encrypted_metadata(compressed_metadata, encryption_handler)

                # Get metadata info
                info = metadata.get_info()

                # Render the info page with the metadata information
                return render_template('info.html', info=info)
            except Exception as e:
                logger.error(f"Encoding failed: {e}")
                return f"Error during encoding: {str(e)}", 500

        except Exception as e:
            logger.error(f"Error retrieving metadata: {e}")
            flash(f"Error retrieving metadata: {str(e)}", 'error')
            return redirect(url_for('main.index'))

    else:
        flash('Invalid image format. Allowed formats are png, jpg, jpeg.', 'error')
        return redirect(url_for('main.index'))


@main.route('/clean/<filename>', methods=['POST'])
def clean(filename):
    """
    Delete the file after download.
    """
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return '', 204  # No content

