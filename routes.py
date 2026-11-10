"""Rotas da API REST (/api). Cada ação relevante gera uma linha no log."""
import secrets
import time
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request

import config
import db
import udp_alertas
import validar
import previsao
from erros import ErroHTTP, ErroValidacao
from logger import registrar
from seguranca import comparar, gerar_token, hash_token, limitar

api = Blueprint("api", __name__, url_prefix="/api")

MENSAGENS_ALERTA = {
    "atencao": "Chuva forte prevista. Evite áreas de alagamento e acompanhe a Defesa Civil (199).",
    "alerta": "Risco de alagamento. Evite sair, proteja seus pertences e acompanhe a Defesa Civil (199).",
    "critico": "Risco crítico. Em área de risco, siga a Defesa Civil (199) e procure um local seguro.",
}


# ---------- utilidades ----------
def _json_seguro(linha, ocultar=()):
    """Converte Decimal/datetime e remove campos internos (como token_hash)."""
    saida = {}
    for chave, valor in linha.items():
        if chave in ocultar:
            continue
        if isinstance(valor, Decimal):
            valor = float(valor)
        elif isinstance(valor, datetime):
            valor = valor.isoformat(timespec="seconds")
        saida[chave] = valor
    return saida


def _corpo_json():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        raise ErroHTTP(400, "Envie um corpo JSON válido (objeto).")
    return dados


def _exigir_admin():
    chave = request.headers.get("X-API-Key")
    if not chave:
        raise ErroHTTP(401, "Credencial necessária.")
    if not comparar(chave, config.ADMIN_API_KEY):
        registrar("autenticacao", "negada", request.path)
        raise ErroHTTP(403, "Acesso negado.")


def _exigir_credencial_presente():
    if not request.headers.get("X-API-Key") and not request.headers.get("X-Token"):
        raise ErroHTTP(401, "Credencial necessária.")


def _exigir_dono_ou_admin(inscricao):
    if request.headers.get("X-API-Key"):
        _exigir_admin()
        return
    token = request.headers.get("X-Token", "")
    if not comparar(hash_token(token), inscricao["token_hash"]):
        registrar("autenticacao", "negada", request.path)
        raise ErroHTTP(403, "Acesso negado.")


def _area_ou_422(area_id):
    area = db.obter_area(area_id)
    if area is None:
        raise ErroValidacao({"area_id": "Área inexistente."})
    return area


def _inscricao_ou_404(insc_id):
    inscricao = db.obter_inscricao(insc_id)
    if inscricao is None:
        raise ErroHTTP(404, "Inscrição não encontrada.")
    return inscricao


# ---------- áreas e risco (GET públicos) ----------
@api.get("/areas")
def listar_areas():
    return jsonify([_json_seguro(a) for a in db.listar_areas()]), 200


@api.get("/risco")
@limitar(30)
def consultar_risco():
    area_id = validar.validar_id_texto(request.args.get("area_id", ""))
    area = db.obter_area(area_id)
    if area is None:
        raise ErroHTTP(404, "Área não encontrada.")
    leitura = previsao.avaliar_risco(area["latitude"], area["longitude"])
    leitura["area"] = area["nome"]
    registrar("consultar_risco", "ok", f"area={area_id} nivel={leitura['nivel']}")
    return jsonify(leitura), 200


# ---------- inscrições: CRUD ----------
@api.post("/inscricoes")
@limitar(10)
def criar_inscricao():
    dados = validar.validar_inscricao(_corpo_json(), criacao=True)
    _area_ou_422(dados["area_id"])
    token = gerar_token()
    novo_id = db.criar_inscricao(dados["apelido"], dados["area_id"],
                                 dados["nivel_minimo"], hash_token(token))
    registrar("criar_inscricao", "criada", f"id={novo_id} area={dados['area_id']}")
    resposta = {**dados, "id": novo_id, "token": token,
                "aviso": "Guarde o token: ele é exibido apenas agora e permite editar ou cancelar."}
    resposta.pop("consentimento", None)
    return jsonify(resposta), 201


@api.get("/inscricoes")
def listar_inscricoes():
    _exigir_admin()
    area_param = request.args.get("area_id")
    area_id = validar.validar_id_texto(area_param) if area_param is not None else None
    linhas = db.listar_inscricoes(area_id)
    registrar("listar_inscricoes", "ok", f"total={len(linhas)}")
    return jsonify([_json_seguro(l, ocultar=("token_hash",)) for l in linhas]), 200


@api.get("/inscricoes/<int:insc_id>")
def obter_inscricao(insc_id):
    _exigir_credencial_presente()
    inscricao = _inscricao_ou_404(insc_id)
    _exigir_dono_ou_admin(inscricao)
    return jsonify(_json_seguro(inscricao, ocultar=("token_hash",))), 200


@api.put("/inscricoes/<int:insc_id>")
def atualizar_inscricao(insc_id):
    _exigir_credencial_presente()
    inscricao = _inscricao_ou_404(insc_id)
    _exigir_dono_ou_admin(inscricao)
    dados = validar.validar_inscricao(_corpo_json(), criacao=False)
    _area_ou_422(dados["area_id"])
    db.atualizar_inscricao(insc_id, dados["apelido"], dados["area_id"], dados["nivel_minimo"])
    registrar("atualizar_inscricao", "atualizada", f"id={insc_id}")
    atual = db.obter_inscricao(insc_id)
    return jsonify(_json_seguro(atual, ocultar=("token_hash",))), 200


@api.delete("/inscricoes/<int:insc_id>")
def excluir_inscricao(insc_id):
    _exigir_credencial_presente()
    inscricao = _inscricao_ou_404(insc_id)
    _exigir_dono_ou_admin(inscricao)
    db.excluir_inscricao(insc_id)
    registrar("excluir_inscricao", "excluida", f"id={insc_id}")
    return "", 204


# ---------- alertas (operador) + módulo UDP ----------
@api.post("/alertas/disparar")
@limitar(20)
def disparar_alerta():
    _exigir_admin()
    dados = validar.validar_disparo(_corpo_json())
    area = db.obter_area(dados["area_id"])
    if area is None:
        raise ErroHTTP(404, "Área não encontrada.")

    simulado = dados["simulacao"] is not None
    leitura = (previsao.leitura_simulada(dados["simulacao"]) if simulado
               else previsao.avaliar_risco(area["latitude"], area["longitude"]))
    nivel = leitura["nivel"]

    if nivel == "baixo":
        registrar("disparar_alerta", "nao_enviado", f"area={area['id']} risco=baixo")
        return jsonify({"enviado": False, "nivel": nivel,
                        "motivo": "Risco baixo: nenhum alerta necessário."}), 200

    destinatarios = db.contar_destinatarios(area["id"], previsao.niveis_ate(nivel))
    if destinatarios == 0:
        registrar("disparar_alerta", "nao_enviado", f"area={area['id']} sem_inscritos")
        return jsonify({"enviado": False, "nivel": nivel,
                        "motivo": "Nenhuma inscrição aceita este nível nesta área."}), 200

    corpo = {
        "id": secrets.token_hex(8), "ts": int(time.time()), "area": area["nome"], "nivel": nivel,
        "chuva_24h_mm": leitura["total_24h_mm"], "chuva_pico_1h_mm": leitura["pico_1h_mm"],
        "destinatarios": destinatarios, "simulado": simulado,
        "mensagem": MENSAGENS_ALERTA[nivel] + " (protótipo, não substitui alertas oficiais)",
    }
    envio = udp_alertas.enviar_alerta(corpo, config.UDP_HOST, config.UDP_PORT,
                                      config.ALERTA_SEGREDO, config.UDP_TIMEOUT)
    alerta_id = db.registrar_alerta(area["id"], nivel, leitura["total_24h_mm"],
                                    leitura["pico_1h_mm"], destinatarios,
                                    envio["confirmado"], simulado)
    registrar("disparar_alerta", "confirmado" if envio["confirmado"] else "sem_confirmacao",
              f"alerta={alerta_id} area={area['id']} nivel={nivel} simulado={simulado}")
    return jsonify({"enviado": envio["enviado"], "confirmado": envio["confirmado"],
                    "alerta_id": alerta_id, "nivel": nivel, "destinatarios": destinatarios,
                    "simulado": simulado}), 201


@api.get("/alertas")
def listar_alertas():
    _exigir_admin()
    return jsonify([_json_seguro(a) for a in db.listar_alertas()]), 200
