from flask import render_template, request, redirect, url_for, flash
from app.database import usuarios_collection  # Certifique-se de importar a coleção de usuários do MongoDB
from werkzeug.security import generate_password_hash, check_password_hash
from . import main_bp  # Importando o blueprint

@main_bp.route('/')
def index():
    return render_template('main/index.html')

@main_bp.route('/addNewEvent', methods=['GET', 'POST'])
def new_event():
    if request.method == 'POST':
        # Aqui você pode adicionar o código para lidar com o envio do formulário
        # Exemplo: salvar os dados no banco de dados
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        valor_cota = request.form.get('valor_cota')
        inicio_apostas = request.form.get('inicio_apostas')
        fim_apostas = request.form.get('fim_apostas')
        data_evento = request.form.get('data_evento')
        
        # Adicione aqui a lógica para processar os dados

        flash('Evento criado com sucesso!')
        return redirect(url_for('main_bp.index'))
    
    return render_template('main/addNewEvent.html')

