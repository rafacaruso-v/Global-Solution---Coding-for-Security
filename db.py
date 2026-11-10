"""Acesso ao MySQL com SQL puro (sem ORM). Toda consulta é parametrizada (%s)."""
from contextlib import contextmanager
from datetime import datetime

import mysql.connector

import config

@contextmanager
def conexao():
    cnx = mysql.connector.connect(
        host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER,
        password=config.DB_PASSWORD, database=config.DB_NAME,
        charset="utf8mb4", connection_timeout=5,
    )
    try:
        yield cnx
        cnx.commit()
    except Exception:
        cnx.rollback()
        raise
    finally:
        cnx.close()


def _consultar(sql, params=(), um=False):
    with conexao() as cnx:
        cur = cnx.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            return cur.fetchone() if um else cur.fetchall()
        finally:
            cur.close()


def _executar(sql, params=()):
    with conexao() as cnx:
        cur = cnx.cursor()
        try:
            cur.execute(sql, params)
            return cur.lastrowid
        finally:
            cur.close()


# ---------- áreas ----------
def listar_areas():
    return _consultar("SELECT id, nome, latitude, longitude FROM areas ORDER BY nome")


def obter_area(area_id):
    return _consultar("SELECT id, nome, latitude, longitude FROM areas WHERE id = %s",
                      (area_id,), um=True)


# ---------- inscrições (CRUD) ----------
_SELECT_INSCRICAO = (
    "SELECT i.id, i.apelido, i.area_id, a.nome AS area_nome, i.nivel_minimo, "
    "i.token_hash, i.criado_em "
    "FROM inscricoes i JOIN areas a ON a.id = i.area_id "
)


def criar_inscricao(apelido, area_id, nivel_minimo, token_hash):
    return _executar(
        "INSERT INTO inscricoes (apelido, area_id, nivel_minimo, token_hash, consentimento_em) "
        "VALUES (%s, %s, %s, %s, %s)",
        (apelido, area_id, nivel_minimo, token_hash, datetime.now()),
    )


def obter_inscricao(insc_id):
    return _consultar(_SELECT_INSCRICAO + "WHERE i.id = %s", (insc_id,), um=True)


def listar_inscricoes(area_id=None):
    if area_id is None:
        return _consultar(_SELECT_INSCRICAO + "ORDER BY i.id")
    return _consultar(_SELECT_INSCRICAO + "WHERE i.area_id = %s ORDER BY i.id", (area_id,))


def atualizar_inscricao(insc_id, apelido, area_id, nivel_minimo):
    _executar(
        "UPDATE inscricoes SET apelido = %s, area_id = %s, nivel_minimo = %s WHERE id = %s",
        (apelido, area_id, nivel_minimo, insc_id),
    )


def excluir_inscricao(insc_id):
    _executar("DELETE FROM inscricoes WHERE id = %s", (insc_id,))


def contar_destinatarios(area_id, niveis_aceitos):
    """Conta inscritos da área cujo nível mínimo está entre `niveis_aceitos`."""
    if not niveis_aceitos:
        return 0
    marcadores = ", ".join(["%s"] * len(niveis_aceitos))  # só "%s": valores seguem parametrizados
    linha = _consultar(
        "SELECT COUNT(*) AS total FROM inscricoes "
        f"WHERE area_id = %s AND nivel_minimo IN ({marcadores})",
        (area_id, *niveis_aceitos), um=True,
    )
    return int(linha["total"])


# ---------- alertas ----------
def registrar_alerta(area_id, nivel, chuva_24h, pico_1h, destinatarios, entregue, simulado):
    return _executar(
        "INSERT INTO alertas (area_id, nivel, chuva_24h_mm, chuva_pico_1h_mm, "
        "destinatarios, entregue, simulado) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (area_id, nivel, chuva_24h, pico_1h, destinatarios, int(entregue), int(simulado)),
    )


def listar_alertas(limite=20):
    return _consultar(
        "SELECT al.id, a.nome AS area_nome, al.nivel, al.chuva_24h_mm, al.chuva_pico_1h_mm, "
        "al.destinatarios, al.entregue, al.simulado, al.criado_em "
        "FROM alertas al JOIN areas a ON a.id = al.area_id ORDER BY al.id DESC LIMIT %s",
        (limite,),
    )
