from flask import Blueprint, jsonify, request
from flask_login import login_required

from app import db
from app.models import Service

api_bp = Blueprint("api", __name__)


@api_bp.route("/status")
@login_required
def status():
    """Retorna o status atual de todos os serviços (usado pelo polling do dashboard)."""
    services = Service.query.all()
    return jsonify([s.to_dict() for s in services])


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
