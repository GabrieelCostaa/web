from flask import render_template, redirect, url_for, request, flash, Blueprint

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin':
            flash('Login realizado com sucesso!')
            return redirect(url_for('main.index'))
        else:
            flash('Credenciais inválidas.')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    flash('Você foi deslogado.')
    return redirect(url_for('auth.login'))
