"""Configuração central. Todas as credenciais vêm de variáveis de ambiente (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _inteiro(nome, padrao):
    try:
        return int(os.getenv(nome, padrao))
    except ValueError:
        raise RuntimeError(f"A variável {nome} deve ser um número inteiro.")


def _decimal(nome, padrao):
    try:
        return float(os.getenv(nome, padrao))
    except ValueError:
        raise RuntimeError(f"A variável {nome} deve ser um número.")


DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = _inteiro("DB_PORT", 3306)
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "alerta_chuva")

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
ALERTA_SEGREDO = os.getenv("ALERTA_SEGREDO", "")

UDP_HOST = os.getenv("UDP_HOST", "127.0.0.1")
UDP_PORT = _inteiro("UDP_PORT", 9999)
UDP_TIMEOUT = _decimal("UDP_TIMEOUT", 2)

OPEN_METEO_URL = os.getenv("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
HTTP_TIMEOUT = _decimal("HTTP_TIMEOUT", 6)

FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = _inteiro("FLASK_PORT", 5000)
LOG_FILE = os.getenv("LOG_FILE", "logs/alerta_chuva.log")

_SEGREDOS = ("ADMIN_API_KEY", "ALERTA_SEGREDO")
