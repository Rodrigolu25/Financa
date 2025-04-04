from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy import func, extract
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///financas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)

# Models
class Ganho(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    origem = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    descricao = db.Column(db.String(200))

class Despesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    descricao = db.Column(db.String(200))

class CartaoCredito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    parcela = db.Column(db.String(20), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    descricao = db.Column(db.String(200))

class Donativo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    instituicao = db.Column(db.String(100), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    descricao = db.Column(db.String(200))

class CategoriaDespesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, default=True)

with app.app_context():
    db.create_all()
    default_categories = ['Alimentação', 'Transporte', 'Moradia', 'Lazer', 'Saúde', 'Outros']
    for cat in default_categories:
        if not CategoriaDespesa.query.filter_by(nome=cat).first():
            db.session.add(CategoriaDespesa(nome=cat))
    db.session.commit()

def get_month_name(month_num):
    months = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
              'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    return months[month_num - 1]

@app.route('/')
def dashboard():
    try:
        totals = {
            'ganhos': float(db.session.query(func.sum(Ganho.valor)).filter(Ganho.ativo == True).scalar() or 0),
            'despesas': float(db.session.query(func.sum(Despesa.valor))
                         .filter(Despesa.ativo == True)
                         .scalar() or 0),
            'cartao': float(db.session.query(func.sum(CartaoCredito.valor))
                          .filter(CartaoCredito.ativo == True)
                          .scalar() or 0),
            'donativos': float(db.session.query(func.sum(Donativo.valor))
                         .filter(Donativo.ativo == True)
                         .scalar() or 0)
        }
        totals['saldo'] = totals['ganhos'] - totals['despesas'] - totals['cartao'] - totals['donativos']

        transactions = []
        for model in [Ganho, Despesa, CartaoCredito, Donativo]:
            try:
                transactions.extend(model.query.filter(model.ativo == True)
                                  .order_by(model.data.desc())
                                  .limit(5)
                                  .all())
            except:
                continue

        transactions.sort(key=lambda x: x.data if x.data else date.min, reverse=True)

        return render_template('dashboard.html',
                            total_ganhos=totals['ganhos'],
                            total_despesas=totals['despesas'],
                            total_cartao=totals['cartao'],
                            total_donativos=totals['donativos'],
                            saldo=totals['saldo'],
                            movimentacoes=transactions[:5],
                            now=datetime.now())
    
    except Exception as e:
        app.logger.error(f'Erro no dashboard: {str(e)}', exc_info=True)
        flash('Ocorreu um erro ao carregar os dados. Tente novamente.', 'danger')
        return render_template('dashboard.html',
                            total_ganhos=0,
                            total_despesas=0,
                            total_cartao=0,
                            total_donativos=0,
                            saldo=0,
                            movimentacoes=[],
                            now=datetime.now())

if __name__ == '__main__':
    app.run(debug=True)
