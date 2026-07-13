import socket
import subprocess
import platform
import threading
import time
import re
from datetime import datetime
import requests
# Sessão HTTP reutilizável
http_session = requests.Session()
def _check_icmp(host, timeout):
    """
    Teste ICMP.
    Retorna o tempo real informado pelo ping.
    """
    is_windows = platform.system().lower() == "windows"
    if is_windows:
        cmd = [
            "ping",
            "-n",
            "1",
            "-w",
            str(int(timeout * 1000)),
            host
        ]
    else:
        cmd = [
            "ping",
            "-c",
            "1",
            "-W",
            str(max(1, int(timeout))),
            host
        ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout + 1
        )
        if result.returncode != 0:
            return False, None
        output = result.stdout
        match = re.search(
            r"(?:tempo|time)[=<]?\s*([\d\.]+)\s*ms",
            output,
            re.IGNORECASE
        )
        if match:
            return True, float(match.group(1))
        if re.search(
            r"(?:tempo|time)<1ms",
            output,
            re.IGNORECASE
        ):
            return True, 1.0
        return True, None
    except (
        subprocess.TimeoutExpired,
        OSError
    ):
        return False, None
def _check_tcp(host, port, timeout):
    """
    Mede somente abertura da conexão TCP.
    """
    inicio = time.perf_counter()
    try:
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        sock.settimeout(timeout)
        sock.connect(
            (host, port)
        )
        sock.close()
        tempo = (
            time.perf_counter() - inicio
        ) * 1000
        return True, tempo
    except (
        socket.timeout,
        OSError
    ):
        return False, None
def _check_http(url, timeout, verify_ssl=True):
    """
    Teste HTTP otimizado.
    """
    inicio = time.perf_counter()
    try:
        resposta = http_session.head(
            url,
            timeout=(
                timeout,
                timeout
            ),
            verify=verify_ssl,
            allow_redirects=False
        )
        tempo = (
            time.perf_counter() - inicio
        ) * 1000
        # Considera serviço ativo
        # mesmo com erro de aplicação
        ok = resposta.status_code < 500
        return ok, tempo
    except requests.RequestException:
        return False, None
def check_service(service, timeout):
    tipo = service.tipo
    if tipo == "icmp":
        return _check_icmp(
            service.host,
            timeout
        )
    if tipo == "tcp":
        porta = service.porta or 80
        return _check_tcp(
            service.host,
            porta,
            timeout
        )
    if tipo in ("http", "https"):
        host = service.host
        if not host.startswith(
            ("http://", "https://")
        ):
            protocolo = (
                "https"
                if tipo == "https"
                else "http"
            )
            porta = (
                f":{service.porta}"
                if service.porta
                else ""
            )
            host = (
                f"{protocolo}://"
                f"{host}"
                f"{porta}"
            )
        return _check_http(
            host,
            timeout
        )
    return False, None
def _classify_status(ok, tempo_ms, degraded_threshold_ms):
    if not ok:
        return "vermelho"
    if (
        tempo_ms is not None
        and tempo_ms > degraded_threshold_ms
    ):
        return "amarelo"
    return "verde"
def run_check_cycle(app):
    from app import db
    from app.models import Service, Historico
    with app.app_context():
        timeout = app.config["CHECK_TIMEOUT"]
        degraded_threshold = (
            app.config["DEGRADED_THRESHOLD_MS"]
        )
        services = Service.query.all()
        for service in services:
            ok, tempo_ms = check_service(
                service,
                timeout
            )
            status = _classify_status(
                ok,
                tempo_ms,
                degraded_threshold
            )
            service.status = status
            service.ping = (
                round(tempo_ms, 2)
                if tempo_ms is not None
                else None
            )
            service.ultima_verificacao = (
                datetime.utcnow()
            )
            db.session.add(
                Historico(
                    service_id=service.id,
                    status=status,
                    tempo_resposta=service.ping
                )
            )
        db.session.commit()
def _monitor_loop(app):
    interval = app.config["MONITOR_INTERVAL"]
    while True:
        try:
            run_check_cycle(app)
        except Exception as exc:
            app.logger.exception(
                f"Erro no monitoramento: {exc}"
            )
        time.sleep(interval)
def start_monitor(app):
    thread = threading.Thread(
        target=_monitor_loop,
        args=(app,),
        daemon=True
    )
    thread.start()
    return thread
