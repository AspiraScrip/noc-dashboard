import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

    # Intervalo (segundos) entre verificações do monitor em segundo plano
    MONITOR_INTERVAL = int(os.environ.get("MONITOR_INTERVAL", "10"))
    # Timeout (segundos) para cada verificação (ping/tcp/http)
    CHECK_TIMEOUT = int(os.environ.get("CHECK_TIMEOUT", "3"))
    # Tempo de resposta (ms) acima do qual o serviço é considerado "degradado" (amarelo)
    DEGRADED_THRESHOLD_MS = int(os.environ.get("DEGRADED_THRESHOLD_MS", "500"))

    # Banco de dados: SQLite por padrão (dev), PostgreSQL em produção via DATABASE_URL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'noc.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
