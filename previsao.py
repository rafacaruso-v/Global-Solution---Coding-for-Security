"""Fonte externa: previsão de chuva da Open-Meteo (https://open-meteo.com), via requests + JSON.

Os limiares abaixo são ILUSTRATIVOS (protótipo). Alertas oficiais vêm da Defesa Civil,
do CEMADEN e do INMET.
"""
from datetime import datetime, timezone

import requests

import config
from erros import ErroFonteExterna
from logger import registrar
from validar import NIVEIS

# nível: (chuva acumulada em 24 h em mm, pico em 1 h em mm). Basta atingir um dos dois.
LIMIARES = {"critico": (100.0, 40.0), "alerta": (60.0, 25.0), "atencao": (30.0, 10.0)}
_SIMULADOS = {"atencao": (35.0, 12.0), "alerta": (65.0, 27.0), "critico": (110.0, 42.0)}


def classificar(precipitacao_horaria):
    valores = []
    for v in list(precipitacao_horaria)[:24]:
        ok = isinstance(v, (int, float)) and not isinstance(v, bool)
        valores.append(max(float(v), 0.0) if ok else 0.0)  # null/inválido vira 0
    total = round(sum(valores), 1)
    pico = round(max(valores, default=0.0), 1)
    nivel = "baixo"
    for nome in ("critico", "alerta", "atencao"):
        lim_total, lim_pico = LIMIARES[nome]
        if total >= lim_total or pico >= lim_pico:
            nivel = nome
            break
    return {"nivel": nivel, "total_24h_mm": total, "pico_1h_mm": pico}


def niveis_ate(nivel):
    """Níveis de inscrição que devem receber um alerta deste nível."""
    return [n for n in NIVEIS[1:NIVEIS.index(nivel) + 1]]


def leitura_simulada(nivel):
    total, pico = _SIMULADOS[nivel]
    return {"nivel": nivel, "total_24h_mm": total, "pico_1h_mm": pico}


def obter_precipitacao_horaria(latitude, longitude):
    params = {
        "latitude": float(latitude), "longitude": float(longitude),
        "hourly": "precipitation", "forecast_hours": 24, "timezone": "America/Sao_Paulo",
    }
    try:
        resposta = requests.get(config.OPEN_METEO_URL, params=params, timeout=config.HTTP_TIMEOUT)
        resposta.raise_for_status()
        horaria = resposta.json()["hourly"]["precipitation"]
        if not isinstance(horaria, list) or not horaria:
            raise ValueError("resposta sem dados")
        return horaria
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        registrar("fonte_externa_open_meteo", "falha", type(exc).__name__)
        raise ErroFonteExterna("Fonte de previsão indisponível.") from exc


def avaliar_risco(latitude, longitude):
    leitura = classificar(obter_precipitacao_horaria(latitude, longitude))
    leitura["fonte"] = "Open-Meteo"
    leitura["consultado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return leitura
