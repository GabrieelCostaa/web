from flask import request, redirect, url_for, flash, Blueprint, session
from app.database import usuarios_collection  # Certifique-se de importar a coleção de usuários do MongoDB

# Criação de um Blueprint para autenticação, organizando rotas relacionadas ao login, logout e registro
auth_bp = Blueprint('auth', __name__)

# Rota de registro de usuário
@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registra um novo usuário no sistema.
    - Coleta dados do formulário e armazena no MongoDB.
    - Define valores padrão como 'primeiro_login' e 'moderador'.
    """
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
            "primeiro_login": True,
            "moderador": False
        }
        # Insere o usuário no banco de dados
        usuarios_collection.insert_one(novo_usuario)

        # Mensagem de sucesso e redireciona de volta para o index
        flash('Usuário registrado com sucesso!', 'success')
        return redirect(url_for('main.index'))  # Redireciona para a rota principal (index)
    
@auth_bp.route('/set_auto_open', methods=['POST'])
def set_auto_open():
    """
    Ativa a funcionalidade de abrir popups automaticamente.
    - Define a variável 'auto_open' na sessão como True.
    """
    session['auto_open'] = True  # Ativa o auto_open para abrir o popup
    return '', 204  # Retorna uma resposta vazia e um status 204 No Content

# Rota para login de usuário
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Realiza o login do usuário.
    - Valida credenciais (email e senha) com os dados armazenados no MongoDB.
    - Armazena informações na sessão para identificar o usuário.
    """
    email = request.form['email']
    senha = request.form['senha']

    # Procura o usuário no MongoDB
    usuario = usuarios_collection.find_one({"email": email})

    if usuario and usuario['senha'] == senha: # Verifica se as credenciais estão corretas
        flash('Login realizado com sucesso!')
        
        # Armazena o _id do usuário e o nome na sessão
        session['usuario_id'] = str(usuario['_id'])  # Converte o ObjectId para string e Armazena o ID do usuário na sessão
        session['nome'] = usuario['nome']
        session['moderador'] = usuario['moderador']    #  Moderador
        session['success'] = True   # Logado com sucesso
        
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
    """
    Realiza o logout do usuário.
    - Limpa todos os dados da sessão.
    """
    # Limpa a sessão do usuário
    session.clear()
    flash('Você saiu da sua conta.')
    return redirect(url_for('main.index'))

