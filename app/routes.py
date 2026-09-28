import os
import shutil
import tempfile
from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename
from src.encoder import Encoder
from src.decoder import Decoder
from src.encryption import Encryptor
from src.metadata import Metadata
from src.qr_video import QRVideoEncoder, QRVideoDecoder
from src.utils import setup_logger

main = Blueprint('main', __name__)

UPLOAD_FOLDER = 'app/uploads'
ALLOWED_EXTENSIONS = {'png', 'txt', 'jpeg', 'jpg', 'mp4'}

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
        
@main.route('/encode-video', methods=['POST'])
def encode_video():
    if 'file' not in request.files:
        return "Error: file is required", 400

    file = request.files['file']
    password = request.form.get('password')

    if not password:
        return "Error: Password is required", 400

    output_format = request.form.get('format', 'mp4').lower()
    if output_format not in ('mp4', 'zip'):
        output_format = 'mp4'

    if file:
        file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        output_filename = secure_filename(f'{file.filename}.{output_format}')
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)

        file.save(file_path)

        try:
            logger = setup_logger(verbose=True)
            encoder = QRVideoEncoder(file_path, output_path, password, 5, logger,
                                     output_format=output_format)
            encoder.build()

            # send_file resolves relative paths against app.root_path, so pass an absolute one.
            return send_file(os.path.abspath(output_path), as_attachment=True)
        except Exception as e:
            logger.error(f"QR encoding failed: {e}")
            return f"Error during encoding: {str(e)}", 500

    return "Error: Invalid file", 400


@main.route('/decode-video', methods=['POST'])
def decode_video():
    password = request.form.get('password')
    if not password:
        return "Error: Password is required", 400

    # Two decode sources: a single MP4 video, or a set of QR PNG images (an unzipped folder).
    images = [img for img in request.files.getlist('images') if img and img.filename]
    video = request.files.get('video')

    logger = setup_logger(verbose=True)
    source_path = None
    try:
        if images:
            # Save the uploaded PNGs into a fresh folder and decode from it.
            source_path = tempfile.mkdtemp(prefix="qr_decode_", dir=UPLOAD_FOLDER)
            for img in images:
                if allowed_file(img.filename):
                    img.save(os.path.join(source_path, secure_filename(img.filename)))
        elif video and video.filename and allowed_file(video.filename):
            source_path = os.path.join(UPLOAD_FOLDER, secure_filename(video.filename))
            video.save(source_path)
        else:
            return "Error: provide an MP4 video or a set of QR PNG images", 400

        decoder = QRVideoDecoder(source_path, password, 5, logger, out_dir=UPLOAD_FOLDER)
        info, data = decoder.extract_and_decrypt()

        output_path = os.path.join(UPLOAD_FOLDER, f"output_{info.get('original_filename')}")
        # send_file resolves relative paths against app.root_path, so pass an absolute one.
        return send_file(os.path.abspath(output_path), as_attachment=True)
    except Exception as e:
        logger.error(f"QR decoding failed: {e}")
        return f"Error during decoding: {str(e)}", 500
    finally:
        if source_path and os.path.isdir(source_path):
            shutil.rmtree(source_path, ignore_errors=True)


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

