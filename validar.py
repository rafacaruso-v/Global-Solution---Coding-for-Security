"""Validação de TODA entrada, por lista de permissão (só passa o que é esperado)."""
import re

from erros import ErroValidacao

NIVEIS = ("baixo", "atencao", "alerta", "critico")
NIVEIS_INSCRICAO = NIVEIS[1:]  

APELIDO_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9][A-Za-zÀ-ÖØ-öø-ÿ0-9 ._-]{1,39}$")
_INT_MAX = 2_147_483_647


def inteiro_positivo(valor):
    return isinstance(valor, int) and not isinstance(valor, bool) and 0 < valor <= _INT_MAX


def validar_id_texto(texto, campo="area_id"):
    """Valida parâmetro de URL/query (sempre chega como texto)."""
    if not isinstance(texto, str) or not texto.isascii() or not texto.isdigit() or len(texto) > 10:
        raise ErroValidacao({campo: "Informe um número inteiro positivo."})
    valor = int(texto)
    if not inteiro_positivo(valor):
        raise ErroValidacao({campo: "Informe um número inteiro positivo."})
    return valor


def _checar_campos_extras(dados, permitidos, erros):
    if set(dados) - permitidos:
        erros["campos_extras"] = "Há campos não permitidos."


def validar_inscricao(dados, criacao):
    """POST exige consentimento; PUT exige todos os campos editáveis."""
    permitidos = {"apelido", "area_id", "nivel_minimo"}
    if criacao:
        permitidos.add("consentimento")
    erros = {}
    _checar_campos_extras(dados, permitidos, erros)

    apelido = dados.get("apelido")
    if not isinstance(apelido, str) or not APELIDO_RE.match(apelido.strip()):
        erros["apelido"] = "Use de 2 a 40 caracteres: letras, números, espaço, ponto, hífen ou sublinhado."
    else:
        apelido = apelido.strip()

    if not inteiro_positivo(dados.get("area_id")):
        erros["area_id"] = "Escolha uma área válida."

    nivel = dados.get("nivel_minimo", "atencao" if criacao else None)
    if nivel not in NIVEIS_INSCRICAO:
        erros["nivel_minimo"] = "Escolha: " + ", ".join(NIVEIS_INSCRICAO) + "."

    if criacao and dados.get("consentimento") is not True:
        erros["consentimento"] = "O consentimento é obrigatório para receber alertas."

    if erros:
        raise ErroValidacao(erros)
    return {"apelido": apelido, "area_id": dados["area_id"], "nivel_minimo": nivel}


def validar_disparo(dados):
    erros = {}
    _checar_campos_extras(dados, {"area_id", "simulacao"}, erros)
    if not inteiro_positivo(dados.get("area_id")):
        erros["area_id"] = "Escolha uma área válida."
    simulacao = dados.get("simulacao")
    if simulacao is not None and simulacao not in NIVEIS_INSCRICAO:
        erros["simulacao"] = "Use: " + ", ".join(NIVEIS_INSCRICAO) + "."
    if erros:
        raise ErroValidacao(erros)
    return {"area_id": dados["area_id"], "simulacao": simulacao}
