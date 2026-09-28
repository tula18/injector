from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'app/uploads'
    # QR-code videos are large (a small file can become tens/hundreds of MB), so the upload
    # cap must be generous — especially for decoding, where the big MP4 is uploaded.
    # Override with MAX_UPLOAD_MB if needed; default 2 GB.
    max_upload_mb = int(os.environ.get('MAX_UPLOAD_MB', 2048))
    app.config['MAX_CONTENT_LENGTH'] = max_upload_mb * 1024 * 1024

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    from .routes import main
    app.register_blueprint(main)

    return app
