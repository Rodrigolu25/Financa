from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Ganho(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200))
    data = db.Column(db.Date, nullable=False)
    origem = db.Column(db.String(50))  # Ex: Restaurante Fixo, iFood
    
    def __repr__(self):
        return f'<Ganho {self.descricao} - R${self.valor}>'

class Despesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200))
    data = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(50))  # Ex: Alimentação, Transporte
    
    def __repr__(self):
        return f'<Despesa {self.descricao} - R${self.valor}>'

class CartaoCredito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200))
    data = db.Column(db.Date, nullable=False)
    parcela = db.Column(db.String(20))  # Ex: 1/3, À vista
    
    def __repr__(self):
        return f'<Cartao {self.descricao} - R${self.valor}>'

class Donativo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200))
    data = db.Column(db.Date, nullable=False)
    instituicao = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<Donativo {self.instituicao} - R${self.valor}>'