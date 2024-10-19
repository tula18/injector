from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'app/uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit to 16MB files

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    from .routes import main
    app.register_blueprint(main)

    return app
