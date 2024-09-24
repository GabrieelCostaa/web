from flask import Flask
from .main import main_bp
from app.auth.routes import auth_bp

def create_app():
    app = Flask(__name__)

    # Configurações da aplicação
    app.config.from_object('config.Config')

    # Registro dos Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app
