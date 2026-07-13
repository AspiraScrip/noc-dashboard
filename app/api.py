from flask import Blueprint, jsonify, request
from flask_login import login_required

from app import db
from app.models import Service, Connection

api_bp = Blueprint("api", __name__)


@api_bp.route("/status")
@login_required
def status():
    """Retorna o status atual de todos os serviços e as conexões entre eles
    (usado pelo polling do dashboard)."""
    services = Service.query.all()
    connections = Connection.query.all()
    return jsonify({
        "services": [s.to_dict() for s in services],
        "connections": [c.to_dict() for c in connections],
    })


@api_bp.route("/servicos/<int:service_id>/posicao", methods=["POST"])
@login_required
def salvar_posicao(service_id):
    """Salva a posição (x, y) de um cartão após o usuário arrastá-lo."""
    service = Service.query.get_or_404(service_id)
    data = request.get_json(silent=True) or {}

    try:
        pos_x = int(data.get("pos_x"))
        pos_y = int(data.get("pos_y"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erro": "pos_x e pos_y devem ser números."}), 400

    service.pos_x = pos_x
    service.pos_y = pos_y
    db.session.commit()

    return jsonify({"ok": True})


@api_bp.route("/servicos/<int:service_id>/historico")
@login_required
def historico_json(service_id):
    service = Service.query.get_or_404(service_id)
    registros = service.historico.limit(100).all()
    return jsonify([h.to_dict() for h in registros])


@api_bp.route("/conexoes", methods=["GET"])
@login_required
def listar_conexoes():
    conexoes = Connection.query.all()
    return jsonify([c.to_dict() for c in conexoes])


@api_bp.route("/conexoes", methods=["POST"])
@login_required
def criar_conexao():
    """Cria uma ligação (linha) entre dois serviços."""
    data = request.get_json(silent=True) or {}

    try:
        origem_id = int(data.get("origem_id"))
        destino_id = int(data.get("destino_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erro": "origem_id e destino_id são obrigatórios."}), 400

    if origem_id == destino_id:
        return jsonify({"ok": False, "erro": "Não é possível conectar um serviço a ele mesmo."}), 400

    if not Service.query.get(origem_id) or not Service.query.get(destino_id):
        return jsonify({"ok": False, "erro": "Serviço não encontrado."}), 404

    existente = Connection.query.filter(
        db.or_(
            db.and_(Connection.origem_id == origem_id, Connection.destino_id == destino_id),
            db.and_(Connection.origem_id == destino_id, Connection.destino_id == origem_id),
        )
    ).first()
    if existente:
        return jsonify({"ok": False, "erro": "Esses serviços já estão conectados."}), 409

    conexao = Connection(origem_id=origem_id, destino_id=destino_id)
    db.session.add(conexao)
    db.session.commit()

    return jsonify({"ok": True, "conexao": conexao.to_dict()}), 201


@api_bp.route("/conexoes/<int:connection_id>", methods=["DELETE"])
@login_required
def excluir_conexao(connection_id):
    conexao = Connection.query.get_or_404(connection_id)
    db.session.delete(conexao)
    db.session.commit()
    return jsonify({"ok": True})
