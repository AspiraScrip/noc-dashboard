import socket
import subprocess
import platform
import threading
import time
from datetime import datetime

import requests


def _check_icmp(host, timeout):
    """Verifica disponibilidade via ping do sistema operacional.
    Retorna (ok: bool, tempo_ms: float|None).
    """
    is_windows = platform.system().lower() == "windows"
    count_flag = "-n" if is_windows else "-c"
    timeout_flag = "-w" if is_windows else "-W"
    timeout_value = str(int(timeout * 1000)) if is_windows else str(int(timeout))

    cmd = ["ping", count_flag, "1", timeout_flag, timeout_value, host]

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout + 2,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        ok = result.returncode == 0
        return ok, elapsed_ms if ok else None
    except (subprocess.TimeoutExpired, OSError):
        return False, None


def _check_tcp(host, port, timeout):
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed_ms = (time.monotonic() - start) * 1000
            return True, elapsed_ms
    except (socket.timeout, OSError):
        return False, None


def _check_http(url, timeout, verify_ssl=True):
    start = time.monotonic()
    try:
        resp = requests.get(url, timeout=timeout, verify=verify_ssl, allow_redirects=True)
        elapsed_ms = (time.monotonic() - start) * 1000
        ok = resp.status_code < 400
        return ok, elapsed_ms
    except requests.RequestException:
        return False, None


def check_service(service, timeout):
    """Executa a verificação apropriada de acordo com o tipo do serviço."""
    tipo = service.tipo

    if tipo == "icmp":
        return _check_icmp(service.host, timeout)

    if tipo == "tcp":
        porta = service.porta or 80
        return _check_tcp(service.host, porta, timeout)

    if tipo in ("http", "https"):
        host = service.host
        if not host.startswith("http://") and not host.startswith("https://"):
            scheme = "https" if tipo == "https" else "http"
            porta_str = f":{service.porta}" if service.porta else ""
            host = f"{scheme}://{host}{porta_str}"
        return _check_http(host, timeout)

    return False, None


def _classify_status(ok, tempo_ms, degraded_threshold_ms):
    if not ok:
        return "vermelho"
    if tempo_ms is not None and tempo_ms > degraded_threshold_ms:
        return "amarelo"
    return "verde"


def run_check_cycle(app):
    """Uma passada de verificação por todos os serviços cadastrados."""
    from app import db
    from app.models import Service, Historico

    with app.app_context():
        timeout = app.config["CHECK_TIMEOUT"]
        degraded_threshold = app.config["DEGRADED_THRESHOLD_MS"]

        services = Service.query.all()
        for service in services:
            ok, tempo_ms = check_service(service, timeout)
            status = _classify_status(ok, tempo_ms, degraded_threshold)

            service.status = status
            service.ping = round(tempo_ms, 1) if tempo_ms is not None else None
            service.ultima_verificacao = datetime.utcnow()

            db.session.add(Historico(
                service_id=service.id,
                status=status,
                tempo_resposta=service.ping,
            ))

        db.session.commit()


def _monitor_loop(app):
    interval = app.config["MONITOR_INTERVAL"]
    while True:
        try:
            run_check_cycle(app)
        except Exception as exc:  # nunca deixar a thread morrer por um erro pontual
            app.logger.error(f"Erro no ciclo de monitoramento: {exc}")
        time.sleep(interval)


def start_monitor(app):
    thread = threading.Thread(target=_monitor_loop, args=(app,), daemon=True)
    thread.start()
    return thread
