"""Log em arquivo: data/hora | ação | resultado | detalhe.

Nunca registramos dados pessoais, tokens ou chaves. Quebras de linha são removidas
para impedir "injeção de log" (linhas falsas inseridas por entrada maliciosa).
"""
import logging
import os
import re
from logging.handlers import RotatingFileHandler

import config

_logger = None


def _obter():
    global _logger
    if _logger is None:
        pasta = os.path.dirname(config.LOG_FILE)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        lg = logging.getLogger("alerta_chuva")
        lg.setLevel(logging.INFO)
        lg.propagate = False
        handler = RotatingFileHandler(config.LOG_FILE, maxBytes=1_000_000,
                                      backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
        lg.addHandler(handler)
        _logger = lg
    return _logger


def registrar(acao, resultado, detalhe=""):
    detalhe = re.sub(r"[\r\n\t]+", " ", str(detalhe))[:200]
    try:
        _obter().info("%s | %s | %s", acao, resultado, detalhe)
    except OSError:
        pass  # falha ao gravar o log não pode derrubar a API
