from flask import render_template, request, redirect, url_for, flash, Blueprint, session
from app.database import usuarios_collection  # Certifique-se de importar a coleção de usuários do MongoDB
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

auth_bp = Blueprint('auth', __name__)

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
            "data_nascimento": data_nascimento,
            "primeiro_login": True
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
        
        # Armazena o _id do usuário e o nome na sessão
        session['usuario_id'] = str(usuario['_id'])  # Converte o ObjectId para string
        session['nome'] = usuario['nome']
        session['success'] = True
        
            # Verifica se é o primeiro login
        if usuario.get('primeiro_login', True):  # Se 'primeiro_login' for True, significa que é o primeiro login
            session['first_login'] = True
            usuarios_collection.update_one({"_id": usuario['_id']}, {"$set": {"primeiro_login": False}})
        else:
            session['first_login'] = False
      
        return redirect(url_for('main.index'))
    else:
        flash('Email ou senha inválidos.')
        session['error'] = True
        return redirect(url_for('main.index'))
    
    
@auth_bp.route('/logout')
def logout():
    # Limpa a sessão do usuário
    session.clear()
    flash('Você saiu da sua conta.')
    return redirect(url_for('main.index'))

