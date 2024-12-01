import pymongo  # Utilizado para interação com o banco de dados MongoDB
from flask import render_template, request, redirect, url_for, flash, session  # Ferramentas do Flask para manipular requisições, templates e sessões
from app.database import eventos_collection, usuarios_collection, transactions_collection  # Conexão com as coleções do banco de dados
from . import main_bp  # Registro do Blueprint para separar rotas
from datetime import datetime  # Utilizado para trabalhar com datas e horários
from bson import ObjectId  # Permite manipulação de IDs do MongoDB
import smtplib  # Ferramenta para envio de e-mails
from email.mime.text import MIMEText  # Criação de mensagens de e-mail no formato texto

@main_bp.route('/')
def index():
    """
    Página inicial do sistema.
    - Lista eventos aprovados, próximos de vencer e mais apostados.
    - Verifica se o usuário está logado para personalizar a experiência.
    """
    now = datetime.now()
    # Verificar se o usuário está logado e buscar suas informações
    if 'usuario_id' in session:
        usuario = usuarios_collection.find_one({"_id": ObjectId(session['usuario_id'])})
    else:
        usuario = None
        
    first_login = session.get('first_login', False)
    success = session.pop('success', False)
    
    # Buscar todos os eventos aprovados
    eventos_aprovados = eventos_collection.find({"aprovado": True, "finalizado": False})   
        
     # Buscar eventos próximos de vencer
    eventos_proximos_de_vencer = eventos_collection.find({
        "finalizado": False,
        "aprovado": True,
        "fim_apostas": {"$gte": now}
    }).sort("fim_apostas", 1).limit(5)  # Pegar os 5 eventos mais próximos de terminar 
    
     # Buscar eventos mais apostados (exemplo de campo 'num_apostas')
    eventos_mais_apostados = eventos_collection.find({
        "finalizado": False,
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
    """
    Rota para criação de um novo evento.
    - Apenas usuários logados podem acessar.
    - Validações para os campos de formulário e criação no banco de dados.
    """
    if 'usuario_id' in session:
        if request.method == 'POST':
            titulo = request.form.get('titulo')
            descricao = request.form.get('descricao')
            valor_cota_str = request.form.get('valor_cota')
            valor_cota_str = valor_cota_str.replace(',', '.')
            try:
                valor_cota = float(valor_cota_str)
                if valor_cota <= 0:
                    raise ValueError("O valor da cota deve ser maior que zero.")
            except (TypeError, ValueError) as e:
                flash(f"Valor da cota inválido: {e}", "danger")
                return redirect(url_for('main.new_event'))
            
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
            
            # Adiciona o ID do usuário que criou o evento
            usuario_id = session.get('usuario_id')

            novo_evento = {
                "titulo": titulo,
                "descricao": descricao,
                "valor_cota": valor_cota,
                "inicio_apostas": inicio_apostas,
                "fim_apostas": fim_apostas,
                "data_evento": data_evento,
                "categoria": categoria,
                "aprovado": False, # Evento começa como não aprovado
                "reprovado": False,
                "num_apostas": 0,  # Inicializando o contador de apostas
                "finalizado": False,
                "usuario_id": ObjectId(usuario_id)
            }

            eventos_collection.insert_one(novo_evento)

            flash('Evento criado com sucesso! Aguarde a aprovação do moderador.')
            return redirect(url_for('main.index'))
        
        return render_template('main/addNewEvent.html')


@main_bp.route('/eventos_pendentes')
def listar_eventos_pendentes():
    """
    Rota exclusiva para moderadores.
    - Lista eventos que aguardam aprovação.
    """
    # Verifica se o usuário é um moderador
    if not session.get('moderador'):
        flash("Acesso negado. Você não tem permissão para acessar esta página.")
        return redirect(url_for('main.index'))

    # Buscar todos os eventos pendentes de aprovação
    eventos_pendentes = eventos_collection.find({"aprovado": False, "reprovado": False})
    
    if 'usuario_id' in session:
        usuario = usuarios_collection.find_one({"_id": ObjectId(session['usuario_id'])})
    else:
        usuario = None

    return render_template('main/eventos_pendentes.html', eventos=eventos_pendentes, usuario=usuario)

def enviar_email_reprovacao(email_destinatario, titulo_evento, motivo_reprovacao):
    """
    Envia um e-mail ao criador do evento informando sobre sua reprovação.
    """
    remetente = "casino_pucc@gmail.com"
    assunto = f"Evento '{titulo_evento}' Reprovado"
    corpo_email = f"Seu evento '{titulo_evento}' foi reprovado pelo seguinte motivo: {motivo_reprovacao}."

    msg = MIMEText(corpo_email)
    msg['Subject'] = assunto
    msg['From'] = remetente
    msg['To'] = email_destinatario

    # Configuração do servidor SMTP sem autenticação e sem TLS
    smtp = smtplib.SMTP('smtp.freesmtpservers.com', 25) ## https://www.wpoven.com/tools/free-smtp-server-for-testing -- teste
    smtp.sendmail(remetente, email_destinatario, msg.as_string())
    smtp.quit()

@main_bp.route('/aprovar_evento/<evento_id>', methods=['POST'])
def aprovar_evento(evento_id):
    """
    Rota para aprovação de eventos.
    - Exclusiva para moderadores.
    - Atualiza o status do evento no banco de dados.
    """
    # Verifica se o usuário é um moderador
    if not session.get('moderador'):
        flash("Acesso negado. Você não tem permissão para acessar esta página.")
        return redirect(url_for('main.index'))
    # Aprova o evento
    eventos_collection.update_one({"_id": ObjectId(evento_id)}, {"$set": {"aprovado": True}})
    flash('Evento aprovado com sucesso!')
    return redirect(url_for('main.index'))

@main_bp.route('/reprovar_evento/<evento_id>', methods=['POST'])
def reprovar_evento(evento_id):
    """
    Rota para reprovar um evento.
    - Exclusiva para moderadores.
    - Atualiza o evento com o motivo da reprovação e envia um e-mail ao criador.
    """
    if not session.get('moderador'):
        flash("Acesso negado. Você não tem permissão para acessar esta página.")
        return redirect(url_for('main.index'))
    
    if 'usuario_id' in session:
        # Pega o motivo da reprovação
        motivo_reprovacao = request.form.get('motivo_reprovacao', '')
        
        # Atualiza o campo 'motivo_reprovacao' do evento no banco de dados e Marcar o evento como reprovado
        eventos_collection.update_one(
            {"_id": ObjectId(evento_id)},
            {"$set": {"motivo_reprovacao": motivo_reprovacao, "reprovado": True}},
        )
        # Enviar email para o criador do evento
        evento = eventos_collection.find_one({"_id": ObjectId(evento_id)})
        usuario_criador = usuarios_collection.find_one({"_id": ObjectId(evento['usuario_id'])})
        email_criador = usuario_criador['email']

        # enviar o email de reprovação
        enviar_email_reprovacao(email_criador, evento['titulo'], motivo_reprovacao)

        flash("Evento reprovado e email enviado para o criador.", "danger")
        return '', 204  # Retorna sucesso, sem conteúdo
    else:
        flash("Você precisa estar logado para reprovar um evento.", "danger")
        return redirect(url_for('main.index'))
    

@main_bp.route('/minha_carteira')
def minha_carteira():
    """
    Rota para exibição da carteira do usuário.
    - Lista saldo e transações do usuário logado.
    """
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
    """
    Calcula a taxa de saque baseada no valor solicitado.
    - Valores menores possuem taxas mais altas.
    """
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
    """
    Registra uma transação no histórico do usuário.
    - Inclui informações como tipo, valor e taxa aplicada.
    """
    transacao = {
        "user_id": ObjectId(user_id),
        "tipo": tipo,
        "valor": valor,
        "data": datetime.now(),
        "detalhes": detalhes,
        "taxa_aplicada": taxa
    }
    transactions_collection.insert_one(transacao)  
    

@main_bp.route('/sacar_saldo', methods=['POST'])
def sacar_saldo():
    """
    Processa o saque de saldo pelo usuário.
    - Verifica saldo suficiente e aplica taxa.
    - Deduz valor da carteira e registra a transação.
    """
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
    """
    Permite que o usuário adicione saldo à sua carteira.
    - Atualiza o saldo e registra a transação.
    """
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
    """
    Permite buscar eventos pelo título.
    - Filtra eventos aprovados e ainda em andamento que contenham o termo buscado.
    """
    query = request.args.get('search_query')
    eventos_encontrados = eventos_collection.find({
        "titulo": {"$regex": query, "$options": "i"},
        "aprovado": True,
        "finalizado": False  
    })
    now = datetime.now()
    
    if 'usuario_id' in session:
        usuario = usuarios_collection.find_one({"_id": ObjectId(session['usuario_id'])})
    else:
        usuario = None
    
    return render_template('main/eventos_encontrados.html', eventos=eventos_encontrados, now = now, usuario = usuario)

@main_bp.route('/eventos/categoria/<nome_categoria>')
def eventos_por_categoria(nome_categoria):
    """
    Exibe eventos por categoria.
    - Busca eventos ativos e aprovados da categoria especificada.
    """
    
    now = datetime.now()
    # Buscar eventos da categoria de forma case-insensitive
    eventos_categoria = eventos_collection.find({
        "aprovado": True,
        "finalizado": False,
        "categoria": {"$regex": f"^{nome_categoria}$", "$options": "i"}  # Busca case-insensitive
    })
    
    if 'usuario_id' in session:
        usuario = usuarios_collection.find_one({"_id": ObjectId(session['usuario_id'])})
    else:
        usuario = None

    return render_template('main/eventos_categoria.html', eventos=eventos_categoria, now=now, categoria=nome_categoria, usuario = usuario)


@main_bp.route('/apostar/<evento_id>', methods=['GET'])
def exibir_apostar(evento_id):
    """
    Exibe a página da aposta para o evento selecionado.
    - Verifica se o usuário está logado.
    - Carrega os detalhes do evento.
    """
    # Verifique se o usuário está logado
    if 'usuario_id' in session:
        # Obtenha detalhes do evento
        evento = eventos_collection.find_one({"_id": ObjectId(evento_id)})
        if evento:
            return render_template('main/apostar.html', evento=evento)  ## Pegar o id do evento e passar para apostar.html
                                                                        ## index.html -> exibir_Aposta -> apostar.html -> processar_aposta
        else:
            flash("Evento não encontrado.", "danger")
            return redirect(url_for('main.index'))
    else:
        flash("Você precisa estar logado para fazer uma aposta.", "danger")
        return redirect(url_for('main.index'))

    
@main_bp.route('/apostar/<evento_id>', methods=['POST', 'GET'])
def processar_aposta(evento_id):
    """
    Processa uma aposta no evento.
    - Deduz o valor da aposta do saldo do usuário.
    - Registra a aposta no banco de dados.
    - Registra transação de aposta
    """
    if 'usuario_id' in session:
        quantidade_cotas = int(request.form['quantidade_cotas'])
        opcao_aposta = request.form['opcao_aposta']

        # Busca o evento e o usuário no banco de dados
        evento = eventos_collection.find_one({"_id": ObjectId(evento_id)})
        usuario = usuarios_collection.find_one({"_id": ObjectId(session['usuario_id'])})

        if evento and usuario:    
            valor_cota = float(evento['valor_cota'])
            valor_total = valor_cota * quantidade_cotas
            saldo_atual = usuario['wallet_balance']

            # Verifica se o usuário tem saldo suficiente
            if saldo_atual >= valor_total:
                # Atualiza o saldo do usuário
                novo_saldo = saldo_atual - valor_total
                
                usuarios_collection.update_one(
                    {"_id": ObjectId(session['usuario_id'])},
                    {"$set": {"wallet_balance": novo_saldo}}
                )
                eventos_collection.update_one(
                    {"_id": ObjectId(evento_id)},
                    {"$inc": {"num_apostas": 1}}
                )    
                # Registra a aposta no histórico de transações
                aposta = {
                    "user_id": ObjectId(session['usuario_id']),
                    "evento_id": ObjectId(evento_id),
                    "tipo": "Aposta",
                    "quantidade_cotas": quantidade_cotas,
                    "valor": valor_total,
                    "opcao": opcao_aposta,
                    "data": datetime.now(),
                    "status": "pendente"
                }
                transactions_collection.insert_one(aposta)

                flash("Aposta realizada com sucesso!", "success")
            else:
                flash("Saldo insuficiente. Por favor, adicione mais saldo.", "danger")
                return redirect(url_for('main.minha_carteira'))

        return redirect(url_for('main.index'))
    else:
        flash("Você precisa estar logado para fazer uma aposta.", "danger")
        return redirect(url_for('main.index'))
    
    
@main_bp.route('/finalizar_evento/<evento_id>', methods=['POST'])
def finalizar_evento(evento_id):
    """
    Finaliza um evento e distribui os prêmios.
    - Exclusivo para moderadores.
    - Calcula os ganhos e credita os vencedores.
    - Evento é atualizado para finalizado no banco de dados
    """
    if 'moderador' in session and session['moderador']:  # Verifica se é moderador
        resultado_evento = request.form.get('resultado')  # SIM ou NÃO
        evento = eventos_collection.find_one({"_id": ObjectId(evento_id)})

        if not evento:
            flash('Evento não encontrado.', 'danger')
            return redirect(url_for('main.index'))

        # Atualiza o status do evento para finalizado
        eventos_collection.update_one({"_id": ObjectId(evento_id)}, {"$set": {"finalizado": True, "resultado": resultado_evento}})
        
        # Recupera as apostas do evento
        apostas = transactions_collection.find({"evento_id": ObjectId(evento_id), "tipo": "Aposta"})
        total_perdedores = 0
        vencedores = []
        perdedores = []

        for aposta in apostas:
            if aposta['opcao'] == resultado_evento:
                vencedores.append(aposta)
            else:
                perdedores.append(aposta)
                total_perdedores += aposta['valor']
        
        # Distribui os valores dos perdedores entre os vencedores
        total_apostado_vencedores = sum([aposta['valor'] for aposta in vencedores])

        if total_apostado_vencedores > 0:
            for vencedor in vencedores:
                proporcao = vencedor['valor'] / total_apostado_vencedores
                valor_creditado = proporcao * total_perdedores

                # Credita o valor no saldo do vencedor
                usuarios_collection.update_one(
                    {"_id": ObjectId(vencedor['user_id'])},
                    {"$inc": {"wallet_balance": valor_creditado + vencedor['valor']}}  # Valor apostado + prêmio
                )
                
                # Registra a transação de lucro no histórico do usuário
                transactions_collection.insert_one({
                    "user_id": aposta['user_id'],
                    "evento_id": ObjectId(evento_id),
                    "tipo": "Lucro",
                    "valor": valor_creditado,
                    "detalhes": f"Lucro do evento {evento['titulo']}",
                    "data": datetime.now(),
                    "status": "concluída"
                })

        # Atualiza o status de todas as apostas do evento para "finalizada"
        transactions_collection.update_many(
            {"evento_id": ObjectId(evento_id), "tipo": "Aposta"},
            {"$set": {"status": "finalizada"}}
        )

        flash('Evento finalizado e valores distribuídos com sucesso!', 'success')
        return redirect(url_for('main.index'))
    else:
        flash('Acesso negado. Apenas moderadores podem finalizar eventos.', 'danger')
        return redirect(url_for('main.index'))
