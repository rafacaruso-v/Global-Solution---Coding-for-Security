"""Módulo de sockets UDP: envia alertas a dispositivos comunitários (sirene, painel, celular).

Por que UDP? Datagramas pequenos e sem conexão funcionam melhor em redes fracas ou
instáveis. Como UDP não garante entrega nem autoria, o alerta vai ASSINADO (HMAC-SHA256),
leva carimbo de tempo e id único, e o receptor responde ACK.
"""
import hashlib
import hmac
import json
import socket
import time

MAX_BYTES = 1200         
TOLERANCIA_SEGUNDOS = 300 


def assinar(texto, segredo):
    return hmac.new(segredo.encode("utf-8"), texto.encode("utf-8"), hashlib.sha256).hexdigest()


def montar_envelope(corpo, segredo):
    texto = json.dumps(corpo, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    dados = json.dumps({"c": texto, "s": assinar(texto, segredo)},
                       ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(dados) > MAX_BYTES:
        raise ValueError("Alerta grande demais para um datagrama UDP.")
    return dados


def abrir_envelope(dados, segredo, agora=None, tolerancia=TOLERANCIA_SEGUNDOS):
    """Valida assinatura e validade. Levanta ValueError se algo estiver errado."""
    envelope = json.loads(dados.decode("utf-8"))
    texto, assinatura = envelope["c"], envelope["s"]
    if not isinstance(texto, str) or not isinstance(assinatura, str):
        raise ValueError("envelope inválido")
    if not hmac.compare_digest(assinar(texto, segredo), assinatura):
        raise ValueError("assinatura inválida")
    corpo = json.loads(texto)
    agora = time.time() if agora is None else agora
    if abs(agora - corpo["ts"]) > tolerancia:
        raise ValueError("alerta expirado")
    return corpo


def enviar_alerta(corpo, host, porta, segredo, timeout=2.0):
    """Envia o datagrama e espera o ACK. Retorna {'enviado': bool, 'confirmado': bool}."""
    try:
        dados = montar_envelope(corpo, segredo)
    except ValueError:
        return {"enviado": False, "confirmado": False}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(dados, (host, porta))
            try:
                resposta, origem = sock.recvfrom(64)
            except (socket.timeout, OSError):
                return {"enviado": True, "confirmado": False}  # enviado, mas sem ACK
            return {"enviado": True, "confirmado": resposta == b"ACK" and origem[0] == host}
    except OSError:
        return {"enviado": False, "confirmado": False}
