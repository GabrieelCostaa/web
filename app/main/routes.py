from flask import render_template, request, redirect, url_for, flash, session
from app.database import eventos_collection  # Certifique-se de importar a coleção de usuários do MongoDB
from werkzeug.security import generate_password_hash, check_password_hash
from . import main_bp  # Importando o blueprint
from datetime import datetime
from bson import ObjectId

@main_bp.route('/')
def index():
    # Buscar todos os eventos aprovados
    eventos_aprovados = eventos_collection.find({"aprovado": True})
    now = datetime.utcnow()
    return render_template('main/index.html', eventos=eventos_aprovados, now=now)

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
            "aprovado": False # Evento começa como não aprovado
        }

        eventos_collection.insert_one(novo_evento)

        flash('Evento criado com sucesso! Aguarde a aprovação do moderador.')
        return redirect(url_for('main.index'))
    
    return render_template('main/addNewEvent.html')


@main_bp.route('/eventos_pendentes')
def listar_eventos_pendentes():
    # Verifica se o usuário é um moderador
    ##if not session.get('is_moderador'):
        ##flash("Acesso negado. Você não tem permissão para acessar esta página.")
       ## return redirect(url_for('main.index'))

    # Buscar todos os eventos pendentes de aprovação
    eventos_pendentes = eventos_collection.find({"aprovado": False})
    
    return render_template('main/eventos_pendentes.html', eventos=eventos_pendentes)


@main_bp.route('/aprovar_evento/<evento_id>', methods=['POST'])
def aprovar_evento(evento_id):
    # Verifica se o usuário é um moderador
    ##if not session.get('is_moderador'):
       ## flash("Acesso negado. Você não tem permissão para acessar esta página.")
       ## return redirect(url_for('main.index'))
    # Aprova o evento
    eventos_collection.update_one({"_id": ObjectId(evento_id)}, {"$set": {"aprovado": True}})
    flash('Evento aprovado com sucesso!')
    return '', 204  # Retorna uma resposta vazia indicando sucesso  

