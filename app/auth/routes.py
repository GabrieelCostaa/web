from flask import render_template, request, redirect, url_for, flash, Blueprint, session
from app.database import usuarios_collection  # Certifique-se de importar a coleção de usuários do MongoDB
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

# Função de registro do usuário
def registrar_usuario(nome, email, senha, data_nascimento):
    novo_usuario = {
        "nome": nome,
        "email": email,
        "senha": senha,
        "data_nascimento": data_nascimento  # Adicionando a data de nascimento
    }
    usuarios_collection.insert_one(novo_usuario)  # Insere no MongoDB

# Rota de registro de usuário
# Rota de registro de usuário
@auth_bp.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        data_nascimento = request.form['data_nascimento']

        # Adiciona o usuário ao MongoDB
        novo_usuario = {
            "nome": nome,
            "email": email,
            "senha": senha,
            "data_nascimento": data_nascimento
        }
        
        usuarios_collection.insert_one(novo_usuario)

        # Mensagem de sucesso e redireciona de volta para o index
        flash('Usuário registrado com sucesso!', 'success')
        return redirect(url_for('main.index'))  # Redireciona para a rota principal (index)

# Rota para login de usuário
@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    senha = request.form['senha']

    # Procura o usuário no MongoDB
    usuario = usuarios_collection.find_one({"email": email})

    if usuario and usuario['senha'] == senha:
        flash('Login realizado com sucesso!')
        # Aqui você pode iniciar a sessão ou redirecionar para uma página protegida
        session['success'] = True
        return redirect(url_for('main.index'))
    else:
        flash('Email ou senha inválidos.')
    
        session['error'] = True
        return redirect(url_for('main.index'))

