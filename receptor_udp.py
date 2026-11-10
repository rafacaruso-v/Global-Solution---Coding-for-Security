import socket
import time

import config
import udp_alertas

ROTULOS = {"atencao": "ATENÇÃO", "alerta": "ALERTA", "critico": "CRÍTICO"}


def iniciar_receptor():
    vistos = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((config.UDP_HOST, config.UDP_PORT))
        print(f"Receptor UDP aguardando alertas em {config.UDP_HOST}:{config.UDP_PORT} (Ctrl+C para sair)")
        try:
            while True:
                dados, origem = sock.recvfrom(2048)
                agora = time.time()
                vistos = {k: t for k, t in vistos.items() if agora - t < udp_alertas.TOLERANCIA_SEGUNDOS}
                try:
                    corpo = udp_alertas.abrir_envelope(dados, config.ALERTA_SEGREDO)
                    if corpo["id"] in vistos:
                        raise ValueError("alerta repetido")
                except (ValueError, KeyError, TypeError) as exc:
                    print(f"[descartado] datagrama rejeitado ({type(exc).__name__})")
                    continue
                vistos[corpo["id"]] = agora
                sock.sendto(b"ACK", origem)
                rotulo = ROTULOS.get(corpo.get("nivel"), "?")
                simulado = " (SIMULADO)" if corpo.get("simulado") else ""
                print(f"\n=== {rotulo}{simulado}\n{corpo.get('area')} ===")
                print(corpo.get("mensagem"))
                print(f"Chuva prevista: {corpo.get('chuva_24h_mm')} mm em 24 h "
                      f"(pico {corpo.get('chuva_pico_1h_mm')} mm/h) | pessoas avisadas: {corpo.get('destinatarios')}")
        except KeyboardInterrupt:
            print("\nEncerrado.")


if __name__ == "__main__":
    iniciar_receptor()