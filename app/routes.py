import os
import uuid
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app
)
from flask_login import login_required
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

from app import db
from app.models import Service, Historico, Connection

main_bp = Blueprint("main", __name__)

# Dimensão máxima (px) para o lado maior da imagem do cartão. Isso evita que
# fotos enviadas em resolução alta (celular, câmera etc.) quebrem o layout
# dos cartões e deixem a página pesada para carregar.
MAX_IMAGE_DIM = 512


def _allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def _save_image(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not _allowed_file(file_storage.filename):
        flash("Formato de imagem não suportado. Use png, jpg, jpeg, gif ou webp.", "warning")
        return None

    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    try:
        # Valida que o arquivo é realmente uma imagem (não só a extensão).
        image = Image.open(file_storage.stream)
        image.verify()
        file_storage.stream.seek(0)
        image = Image.open(file_storage.stream)

        # JPEG não suporta canal alpha/paleta.
        if ext in ("jpg", "jpeg") and image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Redimensiona mantendo a proporção — resolve imagens gigantes
        # quebrando o design dos cartões e da tabela de serviços.
        image.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM), Image.LANCZOS)
        image.save(path)
    except UnidentifiedImageError:
        flash("O arquivo enviado não parece ser uma imagem válida.", "warning")
        return None

    return filename


def _next_grid_position():
    """Calcula uma posição em grade para o próximo cartão, evitando que
    novos serviços nasçam empilhados uns sobre os outros."""
    CARD_WIDTH = 210
    CARD_HEIGHT = 125
    COLUMNS = 5
    MARGIN = 20

    count = Service.query.count()
    col = count % COLUMNS
    row = count // COLUMNS

    pos_x = MARGIN + col * CARD_WIDTH
    pos_y = MARGIN + row * CARD_HEIGHT
    return pos_x, pos_y


@main_bp.route("/")
@login_required
def dashboard():
    services = Service.query.order_by(Service.nome).all()
    connections = [c.to_dict() for c in Connection.query.all()]
    return render_template("dashboard.html", services=services, connections=connections)


@main_bp.route("/servicos")
@login_required
def servicos_lista():
    services = Service.query.order_by(Service.nome).all()
    return render_template("servicos.html", services=services)


@main_bp.route("/servicos/novo", methods=["GET", "POST"])
@login_required
def servico_novo():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        host = request.form.get("host", "").strip()
        tipo = request.form.get("tipo", "icmp")
        porta = request.form.get("porta") or None

        if not nome or not host:
            flash("Nome e host/IP são obrigatórios.", "danger")
            return render_template("servico_form.html", service=None)

        if tipo in ("tcp",) and not porta:
            flash("Informe a porta para monitoramento TCP.", "danger")
            return render_template("servico_form.html", service=None)

        imagem = _save_image(request.files.get("imagem"))
        pos_x, pos_y = _next_grid_position()

        service = Service(
            nome=nome,
            host=host,
            tipo=tipo,
            porta=int(porta) if porta else None,
            imagem=imagem,
            pos_x=pos_x,
            pos_y=pos_y,
        )
        db.session.add(service)
        db.session.commit()
        flash(f"Serviço '{nome}' cadastrado com sucesso.", "success")
        return redirect(url_for("main.servicos_lista"))

    return render_template("servico_form.html", service=None)


@main_bp.route("/servicos/<int:service_id>/editar", methods=["GET", "POST"])
@login_required
def servico_editar(service_id):
    service = Service.query.get_or_404(service_id)

    if request.method == "POST":
        service.nome = request.form.get("nome", "").strip()
        service.host = request.form.get("host", "").strip()
        service.tipo = request.form.get("tipo", "icmp")
        porta = request.form.get("porta") or None
        service.porta = int(porta) if porta else None

        nova_imagem = _save_image(request.files.get("imagem"))
        if nova_imagem:
            service.imagem = nova_imagem

        db.session.commit()
        flash("Serviço atualizado com sucesso.", "success")
        return redirect(url_for("main.servicos_lista"))

    return render_template("servico_form.html", service=service)


@main_bp.route("/servicos/<int:service_id>/excluir", methods=["POST"])
@login_required
def servico_excluir(service_id):
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash(f"Serviço '{service.nome}' removido.", "info")
    return redirect(url_for("main.servicos_lista"))


@main_bp.route("/historico/<int:service_id>")
@login_required
def historico(service_id):
    service = Service.query.get_or_404(service_id)
    registros = (
        Historico.query.filter_by(service_id=service_id)
        .order_by(Historico.data.desc())
        .limit(200)
        .all()
    )
    return render_template("historico.html", service=service, registros=registros)
