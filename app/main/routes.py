import pymongo
from flask import render_template, request, redirect, url_for, flash, session
from app.database import eventos_collection, usuarios_collection, transactions_collection # Certifique-se de importar a coleção de usuários do MongoDB
from . import main_bp  # Importando o blueprint
from datetime import datetime
from bson import ObjectId


@main_bp.route('/')
def index():
    now = datetime.utcnow()
    # Verificar se o usuário está logado e buscar suas informações
    if 'usuario_id' in session:
        usuario = usuarios_collection.find_one({"_id": ObjectId(session['usuario_id'])})
    else:
        usuario = None
        
    first_login = session.get('first_login', False)
    success = session.pop('success', False)
    
    # Buscar todos os eventos aprovados
    eventos_aprovados = eventos_collection.find({"aprovado": True})   
        
     # Buscar eventos próximos de vencer
    eventos_proximos_de_vencer = eventos_collection.find({
        "aprovado": True,
        "fim_apostas": {"$gte": now}
    }).sort("fim_apostas", 1).limit(5)  # Pegar os 5 eventos mais próximos de terminar 
    
     # Buscar eventos mais apostados (exemplo de campo 'num_apostas')
    eventos_mais_apostados = eventos_collection.find({
        "aprovado": True
    }).sort("num_apostas", pymongo.ASCENDING).limit(5)  # Pegar os 5 mais apostados   

    # Passar o saldo e nome do usuário junto com os eventos para o template
    return render_template('main/index.html', 
                           eventos=eventos_aprovados, 
                           eventos_proximos_de_vencer=eventos_proximos_de_vencer, 
                           eventos_mais_apostados=eventos_mais_apostados, 
                           now=now,
                           usuario = usuario,
                           first_login=first_login, 
                           success=success)

@main_bp.route('/addNewEvent', methods=['GET', 'POST'])
def new_event():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        valor_cota = request.form.get('valor_cota')
        categoria = request.form.get('categoria')
        
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
            "categoria": categoria,
            "aprovado": False, # Evento começa como não aprovado
            "num_apostas": 0  # Inicializando o contador de apostas
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

@main_bp.route('/minha_carteira')
def minha_carteira():
    if 'usuario_id' in session:
        auto_open = session.get('auto_open', False)  # Verifica se auto_open está ativo
        session['auto_open'] = False  # Reseta auto_open para garantir que não fique ativo para sempre
        print(f"Valor de auto_open: {auto_open}")
        
        usuario = usuarios_collection.find_one({"_id": ObjectId(session['usuario_id'])})
        transacoes = transactions_collection.find({"user_id": ObjectId(session['usuario_id'])})
        if usuario:
            return render_template('main/minha_carteira.html', usuario=usuario, transacoes=transacoes, auto_open=auto_open)
    else:
        flash("Você precisa estar logado para acessar sua carteira.")
        return redirect(url_for('main.index'))

    
def calcular_taxa(valor_saque):
    if valor_saque <= 100:
        return valor_saque * 0.04  # 4%
    elif 101 <= valor_saque <= 1000:
        return valor_saque * 0.03  # 3%
    elif 1001 <= valor_saque <= 5000:
        return valor_saque * 0.02  # 2%
    elif 5001 <= valor_saque <= 100000:
        return valor_saque * 0.01  # 1%
    else:
        return 0.0  # Acima de R$101.000,00 isento de taxa

def registrar_transacao(user_id, tipo, valor, detalhes, taxa=0.0):
    transacao = {
        "user_id": ObjectId(user_id),
        "tipo": tipo,
        "valor": valor,
        "data": datetime.utcnow(),
        "detalhes": detalhes,
        "taxa_aplicada": taxa
    }
    transactions_collection.insert_one(transacao)  
    

@main_bp.route('/sacar_saldo', methods=['POST'])
def sacar_saldo():
    if 'usuario_id' in session:
        user_id = session['usuario_id']
        valor_saque = float(request.form.get('withdrawAmount', 0))
        usuario = usuarios_collection.find_one({"_id": ObjectId(user_id)})

        if usuario and usuario.get('wallet_balance', 0) >= valor_saque:
            taxa = calcular_taxa(valor_saque)  # Calcular taxa com base no valor
            valor_total_com_taxa = valor_saque + taxa

            if usuario['wallet_balance'] >= valor_total_com_taxa:
                # Deduzir o valor do saque e a taxa da carteira
                usuarios_collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$inc": {"wallet_balance": -valor_total_com_taxa}}
                )
                registrar_transacao(user_id, "Saque", valor_saque, "Saque de saldo", taxa)
                flash(f"Saque de R${valor_saque} realizado com sucesso! Taxa aplicada: R${taxa}.")
            else:
                flash("Saldo insuficiente para realizar o saque.")
        else:
            flash("Saldo insuficiente para realizar o saque.")
        return redirect(url_for('main.minha_carteira'))

    flash('Você precisa estar logado para sacar saldo.')
    return redirect(url_for('main.index'))



@main_bp.route('/adicionar_saldo', methods=['POST'])
def adicionar_saldo():
    if 'usuario_id' in session:
        user_id = session['usuario_id']
        valor = float(request.form.get('amount', 0))

        # Atualizar o saldo da carteira no banco de dados
        usuarios_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"wallet_balance": valor}}
        )
        registrar_transacao(user_id, "Deposito", valor, "Adicionar saldo")
        flash('Saldo adicionado com sucesso!')
        return redirect(url_for('main.minha_carteira'))
    
    flash('Você precisa estar logado para adicionar saldo.')
    return redirect(url_for('main.index'))


@main_bp.route('/buscar_eventos')
def buscar_eventos():
    query = request.args.get('search_query')
    eventos_encontrados = eventos_collection.find({
        "titulo": {"$regex": query, "$options": "i"},
        "aprovado": True
    })
    now = datetime.utcnow()
    
    return render_template('main/eventos_encontrados.html', eventos=eventos_encontrados, now = now)

@main_bp.route('/eventos/categoria/<nome_categoria>')
def eventos_por_categoria(nome_categoria):
    now = datetime.utcnow()

    # Buscar eventos da categoria de forma case-insensitive
    eventos_categoria = eventos_collection.find({
        "aprovado": True,
        "categoria": {"$regex": f"^{nome_categoria}$", "$options": "i"}  # Busca case-insensitive
    })

    return render_template('main/eventos_categoria.html', eventos=eventos_categoria, now=now, categoria=nome_categoria)

