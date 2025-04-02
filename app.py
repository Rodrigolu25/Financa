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

class Salario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    dia_pagamento = db.Column(db.Integer, nullable=False)
    origem = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.String(200))
    ativo = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.Date, default=datetime.utcnow)

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
            'ganhos': db.session.query(func.sum(Ganho.valor)).filter(Ganho.ativo == True).scalar() or 0,
            'salarios': db.session.query(func.sum(Ganho.valor)).filter(
                Ganho.ativo == True,
                Ganho.origem.like('Salário%')
            ).scalar() or 0,
            'despesas': db.session.query(func.sum(Despesa.valor)).filter(Despesa.ativo == True).scalar() or 0,
            'cartao': db.session.query(func.sum(CartaoCredito.valor)).filter(CartaoCredito.ativo == True).scalar() or 0,
            'donativos': db.session.query(func.sum(Donativo.valor)).filter(Donativo.ativo == True).scalar() or 0
        }
        totals['saldo'] = totals['ganhos'] - totals['despesas'] - totals['cartao'] - totals['donativos']
        
        transactions = []
        for model in [Ganho, Despesa, CartaoCredito, Donativo]:
            transactions.extend(db.session.query(model).filter(model.ativo == True).order_by(model.data.desc()).limit(5).all())
        
        transactions.sort(key=lambda x: x.data, reverse=True)
        salaries = Salario.query.filter_by(ativo=True).all()
        
        return render_template('dashboard.html',
                            total_ganhos=totals['ganhos'],
                            total_salarios=totals['salarios'],
                            total_despesas=totals['despesas'],
                            total_cartao=totals['cartao'],
                            total_donativos=totals['donativos'],
                            saldo=totals['saldo'],
                            movimentacoes=transactions[:5],
                            salarios=salaries,
                            now=datetime.now())
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return render_template('dashboard.html',
                            total_ganhos=0,
                            total_salarios=0,
                            total_despesas=0,
                            total_cartao=0,
                            total_donativos=0,
                            saldo=0,
                            movimentacoes=[],
                            salarios=[],
                            now=datetime.now())

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar_movimentacao():
    categories = CategoriaDespesa.query.filter_by(ativo=True).order_by(CategoriaDespesa.nome).all()
    
    if request.method == 'POST':
        try:
            tipo = request.form['tipo']
            valor = float(request.form['valor'])
            data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
            descricao = request.form.get('descricao', '')
            
            if tipo == 'ganho':
                origem = request.form['origem']
                db.session.add(Ganho(valor=valor, data=data, origem=origem, descricao=descricao, ativo=True))
            elif tipo == 'despesa':
                categoria = request.form['categoria']
                
                if categoria == 'Outros' and 'nova_categoria' in request.form and request.form['nova_categoria'].strip():
                    nova_categoria = request.form['nova_categoria'].strip()
                    existing = CategoriaDespesa.query.filter_by(nome=nova_categoria).first()
                    if existing:
                        if not existing.ativo:
                            existing.ativo = True
                            db.session.commit()
                        categoria = nova_categoria
                    else:
                        new_cat = CategoriaDespesa(nome=nova_categoria)
                        db.session.add(new_cat)
                        db.session.commit()
                        categoria = nova_categoria
                
                db.session.add(Despesa(valor=valor, data=data, categoria=categoria, descricao=descricao, ativo=True))
            elif tipo == 'cartao':
                parcela = request.form['parcela']
                db.session.add(CartaoCredito(valor=valor, data=data, parcela=parcela, descricao=descricao, ativo=True))
            elif tipo == 'donativo':
                instituicao = request.form['instituicao']
                db.session.add(Donativo(valor=valor, data=data, instituicao=instituicao, descricao=descricao, ativo=True))
            
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
    
    return render_template('adicionar_movimentacao.html', categorias=categories, now=datetime.now())

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
        
        return render_template('extrato.html', movimentacoes=movimentacoes, now=datetime.now())
    except Exception as e:
        flash(f'Erro ao carregar extrato: {str(e)}', 'danger')
        return render_template('extrato.html', movimentacoes=[], now=datetime.now())

@app.route('/relatorios')
def relatorios():
    return render_template('relatorios.html', now=datetime.now())

@app.route('/relatorio_mensal', methods=['GET', 'POST'])
def relatorio_mensal():
    if request.method == 'POST':
        try:
            mes = int(request.form['mes'])
            ano = int(request.form['ano'])
            
            # Total de ganhos (incluindo salários)
            ganhos = db.session.query(func.sum(Ganho.valor))\
                .filter(
                    extract('month', Ganho.data) == mes,
                    extract('year', Ganho.data) == ano,
                    Ganho.ativo == True
                ).scalar() or 0
            
            # Total de salários
            salarios = db.session.query(func.sum(Ganho.valor))\
                .filter(
                    extract('month', Ganho.data) == mes,
                    extract('year', Ganho.data) == ano,
                    Ganho.ativo == True,
                    Ganho.origem.like('Salário%')
                ).scalar() or 0
            
            # Outras consultas
            despesas = db.session.query(func.sum(Despesa.valor))\
                .filter(
                    extract('month', Despesa.data) == mes,
                    extract('year', Despesa.data) == ano,
                    Despesa.ativo == True
                ).scalar() or 0
            
            cartao = db.session.query(func.sum(CartaoCredito.valor))\
                .filter(
                    extract('month', CartaoCredito.data) == mes,
                    extract('year', CartaoCredito.data) == ano,
                    CartaoCredito.ativo == True
                ).scalar() or 0
            
            donativos = db.session.query(func.sum(Donativo.valor))\
                .filter(
                    extract('month', Donativo.data) == mes,
                    extract('year', Donativo.data) == ano,
                    Donativo.ativo == True
                ).scalar() or 0
            
            saldo = ganhos - despesas - cartao - donativos
            
            return render_template('relatorio_mensal.html',
                                mes=mes,
                                ano=ano,
                                ganhos=ganhos,
                                salarios=salarios,
                                despesas=despesas,
                                cartao=cartao,
                                donativos=donativos,
                                saldo=saldo,
                                get_month_name=get_month_name,
                                now=datetime.now())
        
        except Exception as e:
            flash(f'Erro ao gerar relatório: {str(e)}', 'danger')
            return redirect(url_for('relatorio_mensal'))
    
    return render_template('selecionar_mes_ano.html', tipo='mensal', now=datetime.now())

@app.route('/relatorio_anual', methods=['GET', 'POST'])
def relatorio_anual():
    if request.method == 'POST':
        try:
            ano = int(request.form['ano'])
            
            # Ganhos totais por mês
            ganhos_mensais = db.session.query(
                extract('month', Ganho.data).label('mes'),
                func.sum(Ganho.valor).label('total')
            ).filter(
                extract('year', Ganho.data) == ano,
                Ganho.ativo == True
            ).group_by('mes').order_by('mes').all()
            
            # Salários por mês
            salarios_mensais = db.session.query(
                extract('month', Ganho.data).label('mes'),
                func.sum(Ganho.valor).label('total')
            ).filter(
                extract('year', Ganho.data) == ano,
                Ganho.ativo == True,
                Ganho.origem.like('Salário%')
            ).group_by('mes').order_by('mes').all()
            
            # Outras consultas
            despesas_mensais = db.session.query(
                extract('month', Despesa.data).label('mes'),
                func.sum(Despesa.valor).label('total')
            ).filter(
                extract('year', Despesa.data) == ano,
                Despesa.ativo == True
            ).group_by('mes').order_by('mes').all()
            
            cartao_mensal = db.session.query(
                extract('month', CartaoCredito.data).label('mes'),
                func.sum(CartaoCredito.valor).label('total')
            ).filter(
                extract('year', CartaoCredito.data) == ano,
                CartaoCredito.ativo == True
            ).group_by('mes').order_by('mes').all()
            
            donativos_mensal = db.session.query(
                extract('month', Donativo.data).label('mes'),
                func.sum(Donativo.valor).label('total')
            ).filter(
                extract('year', Donativo.data) == ano,
                Donativo.ativo == True
            ).group_by('mes').order_by('mes').all()
            
            # Totais anuais
            total_ganhos = sum([g.total for g in ganhos_mensais])
            total_salarios = sum([s.total for s in salarios_mensais])
            total_despesas = sum([d.total for d in despesas_mensais])
            total_cartao = sum([c.total for c in cartao_mensal])
            total_donativos = sum([d.total for d in donativos_mensal])
            saldo_anual = total_ganhos - total_despesas - total_cartao - total_donativos
            
            return render_template('relatorio_anual.html',
                                ano=ano,
                                ganhos_mensais=ganhos_mensais,
                                salarios_mensais=salarios_mensais,
                                despesas_mensais=despesas_mensais,
                                cartao_mensal=cartao_mensal,
                                donativos_mensal=donativos_mensal,
                                total_ganhos=total_ganhos,
                                total_salarios=total_salarios,
                                total_despesas=total_despesas,
                                total_cartao=total_cartao,
                                total_donativos=total_donativos,
                                saldo_anual=saldo_anual,
                                get_month_name=get_month_name,
                                now=datetime.now())
        
        except Exception as e:
            flash(f'Erro ao gerar relatório: {str(e)}', 'danger')
            return redirect(url_for('relatorio_anual'))
    
    return render_template('selecionar_ano.html', tipo='anual', now=datetime.now())

@app.route('/salario', methods=['GET', 'POST'])
def gerenciar_salario():
    if request.method == 'POST':
        try:
            novo_salario = Salario(
                valor=float(request.form['valor']),
                dia_pagamento=int(request.form['dia_pagamento']),
                origem=request.form['origem'],
                descricao=request.form.get('descricao', ''),
                ativo=True
            )
            db.session.add(novo_salario)
            db.session.commit()
            flash('Salário cadastrado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar salário: {str(e)}', 'danger')
    
    salarios = Salario.query.filter_by(ativo=True).order_by(Salario.data_cadastro.desc()).all()
    return render_template('salario.html', salarios=salarios, now=datetime.now())

@app.route('/registrar_pagamento_salario/<int:id>')
def registrar_pagamento_salario(id):
    salario = db.session.get(Salario, id)
    if not salario:
        flash('Salário não encontrado!', 'danger')
        return redirect(url_for('gerenciar_salario'))
    
    hoje = date.today()
    try:
        novo_ganho = Ganho(
            valor=salario.valor,
            data=hoje,
            origem=f"Salário {salario.origem}",
            descricao=f"Pagamento mensal - {hoje.strftime('%m/%Y')}",
            ativo=True
        )
        db.session.add(novo_ganho)
        db.session.commit()
        flash('Pagamento de salário registrado como ganho!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar pagamento: {str(e)}', 'danger')
    
    return redirect(url_for('gerenciar_salario'))

@app.route('/excluir_salario/<int:id>')
def excluir_salario(id):
    salario = db.session.get(Salario, id)
    if salario:
        salario.ativo = False
        db.session.commit()
        flash('Salário removido com sucesso!', 'success')
    else:
        flash('Salário não encontrado!', 'danger')
    return redirect(url_for('gerenciar_salario'))

@app.route('/excluir/<tipo>/<int:id>', methods=['POST'])
def excluir_movimentacao(tipo, id):
    try:
        model = {
            'ganho': Ganho,
            'despesa': Despesa,
            'cartao': CartaoCredito,
            'donativo': Donativo,
            'salario': Salario
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
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))