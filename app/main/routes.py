from flask import render_template, request, redirect, url_for, flash
from app.database import eventos_collection  # Certifique-se de importar a coleção de usuários do MongoDB
from werkzeug.security import generate_password_hash, check_password_hash
from . import main_bp  # Importando o blueprint
from datetime import datetime

@main_bp.route('/')
def index():
    return render_template('main/index.html')

@main_bp.route('/addNewEvent', methods=['GET', 'POST'])
def new_event():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        valor_cota = request.form.get('valor_cota')
        
        # Captura os campos de data e hora separados para o início do período de apostas
        inicio_apostas_data = request.form.get('inicio_apostas_data')
        inicio_apostas_horario = request.form.get('inicio_apostas_horario')
        inicio_apostas = datetime.strptime(f"{inicio_apostas_data} {inicio_apostas_horario}", "%Y-%m-%d %H:%M")

        # Captura os campos de data e hora separados para o fim do período de apostas
        fim_apostas_data = request.form.get('fim_apostas_data')
        fim_apostas_horario = request.form.get('fim_apostas_horario')
        fim_apostas = datetime.strptime(f"{fim_apostas_data} {fim_apostas_horario}", "%Y-%m-%d %H:%M")

        data_evento_str = request.form.get('data_evento')
        data_evento = datetime.strptime(data_evento_str, '%Y-%m-%d')

        novo_evento = {
            "titulo": titulo,
            "descricao": descricao,
            "valor_cota": valor_cota,
            "inicio_apostas": inicio_apostas,
            "fim_apostas": fim_apostas,
            "data_evento": data_evento,
        }

        eventos_collection.insert_one(novo_evento)

        flash('Evento criado com sucesso!')
        return redirect(url_for('main.index'))
    
    return render_template('main/addNewEvent.html')

