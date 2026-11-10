"""Utilitários de segurança: tokens, comparação em tempo constante e limite de requisições."""
import hashlib
import hmac
import secrets
import threading
import time
from collections import deque
from functools import wraps

from flask import jsonify, request

from logger import registrar


def gerar_token():
    return secrets.token_urlsafe(24)


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def comparar(a, b):
    """Comparação em tempo constante (evita ataque de temporização)."""
    return hmac.compare_digest(str(a).encode("utf-8"), str(b).encode("utf-8"))


class LimitadorJanela:
    """Limite de requisições por chave numa janela deslizante (em memória)."""

    def __init__(self):
        self._acessos = {}
        self._lock = threading.Lock()

    def permitir(self, chave, maximo, janela, agora=None):
        agora = time.monotonic() if agora is None else agora
        with self._lock:
            fila = self._acessos.setdefault(chave, deque())
            while fila and agora - fila[0] >= janela:
                fila.popleft()
            if len(fila) >= maximo:
                return False
            fila.append(agora)
            if len(self._acessos) > 5000:  # limpeza para não crescer sem limite
                for k in [k for k, v in self._acessos.items() if not v or agora - v[-1] >= janela]:
                    del self._acessos[k]
            return True


_limitador = LimitadorJanela()


def limitar(maximo, janela=60):
    def decorador(funcao):
        @wraps(funcao)
        def interno(*args, **kwargs):
            chave = (funcao.__name__, request.remote_addr)
            if not _limitador.permitir(chave, maximo, janela):
                registrar("limite_requisicoes", "bloqueado", request.path)
                resposta = jsonify({"erro": "Muitas requisições. Tente novamente em instantes."})
                resposta.status_code = 429
                resposta.headers["Retry-After"] = str(janela)
                return resposta
            return funcao(*args, **kwargs)
        return interno
    return decorador
