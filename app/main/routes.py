from flask import render_template, request, redirect, url_for, flash
from app.database import usuarios_collection  # Certifique-se de importar a coleção de usuários do MongoDB
from werkzeug.security import generate_password_hash, check_password_hash
from . import main_bp  # Importando o blueprint

@main_bp.route('/')
def index():
    return render_template('main/index.html')

