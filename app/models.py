from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # icmp | tcp | http | https
    porta = db.Column(db.Integer, nullable=True)
    imagem = db.Column(db.String(255), nullable=True)  # nome do arquivo em static/uploads

    status = db.Column(db.String(10), default="cinza")  # verde | amarelo | vermelho | cinza
    ping = db.Column(db.Float, nullable=True)  # tempo de resposta em ms
    pos_x = db.Column(db.Integer, default=20)
    pos_y = db.Column(db.Integer, default=20)
    ultima_verificacao = db.Column(db.DateTime, nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    historico = db.relationship(
        "Historico", backref="service", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Historico.data.desc()"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "host": self.host,
            "tipo": self.tipo,
            "porta": self.porta,
            "imagem": self.imagem,
            "status": self.status,
            "ping": self.ping,
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "ultima_verificacao": (
                self.ultima_verificacao.strftime("%d/%m/%Y %H:%M:%S")
                if self.ultima_verificacao else None
            ),
        }


class Historico(db.Model):
    __tablename__ = "historico"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    tempo_resposta = db.Column(db.Float, nullable=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "tempo_resposta": self.tempo_resposta,
            "data": self.data.strftime("%d/%m/%Y %H:%M:%S"),
        }
