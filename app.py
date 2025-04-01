from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func
import os
import sys

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'financas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'sua_chave_secreta_aqui'

db = SQLAlchemy(app)

# Modelos
class Ganho(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    origem = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

class Despesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

class CartaoCredito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    parcela = db.Column(db.String(20), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

class Donativo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    instituicao = db.Column(db.String(100), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

# Cria banco de dados
with app.app_context():
    db.create_all()

@app.route('/')
def dashboard():
    try:
        totais = {
            'ganhos': db.session.query(func.sum(Ganho.valor)).filter(Ganho.ativo == True).scalar() or 0,
            'despesas': db.session.query(func.sum(Despesa.valor)).filter(Despesa.ativo == True).scalar() or 0,
            'cartao': db.session.query(func.sum(CartaoCredito.valor)).filter(CartaoCredito.ativo == True).scalar() or 0,
            'donativos': db.session.query(func.sum(Donativo.valor)).filter(Donativo.ativo == True).scalar() or 0
        }
        totais['saldo'] = totais['ganhos'] - totais['despesas'] - totais['cartao'] - totais['donativos']
        
        movimentacoes = []
        for model in [Ganho, Despesa, CartaoCredito, Donativo]:
            movimentacoes.extend(db.session.query(model).filter(model.ativo == True).order_by(model.data.desc()).limit(5).all())
        
        movimentacoes.sort(key=lambda x: x.data, reverse=True)
        
        return render_template('dashboard.html',
                            total_ganhos=totais['ganhos'],
                            total_despesas=totais['despesas'],
                            total_cartao=totais['cartao'],
                            total_donativos=totais['donativos'],
                            saldo=totais['saldo'],
                            movimentacoes=movimentacoes[:5])
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return render_template('dashboard.html',
                            total_ganhos=0,
                            total_despesas=0,
                            total_cartao=0,
                            total_donativos=0,
                            saldo=0,
                            movimentacoes=[])

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar_movimentacao():
    if request.method == 'POST':
        try:
            tipo = request.form['tipo']
            valor = float(request.form['valor'])
            data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
            
            if tipo == 'ganho':
                origem = request.form['origem']
                db.session.add(Ganho(valor=valor, data=data, origem=origem, ativo=True))
            elif tipo == 'despesa':
                categoria = request.form['categoria']
                db.session.add(Despesa(valor=valor, data=data, categoria=categoria, ativo=True))
            elif tipo == 'cartao':
                parcela = request.form['parcela']
                db.session.add(CartaoCredito(valor=valor, data=data, parcela=parcela, ativo=True))
            elif tipo == 'donativo':
                instituicao = request.form['instituicao']
                db.session.add(Donativo(valor=valor, data=data, instituicao=instituicao, ativo=True))
            
            db.session.commit()
            flash('Movimentação registrada com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        
        except ValueError:
            flash('Valor inválido! Use números para o valor.', 'danger')
        except KeyError as e:
            flash(f'Campo obrigatório faltando: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar: {str(e)}', 'danger')
    
    return render_template('adicionar_movimentacao.html')

@app.route('/extrato')
def extrato():
    try:
        tipo = request.args.get('tipo', 'todos')
        movimentacoes = []
        
        if tipo in ['todos', 'ganhos']:
            movimentacoes.extend(Ganho.query.filter(Ganho.ativo == True).order_by(Ganho.data.desc()).all())
        if tipo in ['todos', 'despesas']:
            movimentacoes.extend(Despesa.query.filter(Despesa.ativo == True).order_by(Despesa.data.desc()).all())
        if tipo in ['todos', 'cartao']:
            movimentacoes.extend(CartaoCredito.query.filter(CartaoCredito.ativo == True).order_by(CartaoCredito.data.desc()).all())
        if tipo in ['todos', 'donativos']:
            movimentacoes.extend(Donativo.query.filter(Donativo.ativo == True).order_by(Donativo.data.desc()).all())
        
        return render_template('extrato.html', movimentacoes=movimentacoes)
    except Exception as e:
        flash(f'Erro ao carregar extrato: {str(e)}', 'danger')
        return render_template('extrato.html', movimentacoes=[])

@app.route('/excluir/<tipo>/<int:id>', methods=['POST'])
def excluir_movimentacao(tipo, id):
    try:
        model = {
            'ganho': Ganho,
            'despesa': Despesa,
            'cartao': CartaoCredito,
            'donativo': Donativo
        }.get(tipo)
        
        if not model:
            return jsonify({'success': False, 'message': 'Tipo inválido'}), 400
        
        registro = db.session.get(model, id)
        if registro:
            registro.ativo = False
            db.session.commit()
            return jsonify({'success': True, 'message': 'Registro excluído com sucesso'})
        return jsonify({'success': False, 'message': 'Registro não encontrado'}), 404
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=False)
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        sys.exit(0)