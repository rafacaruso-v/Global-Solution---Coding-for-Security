"""AlertaChuva SP - ponto de entrada da aplicação Flask."""
import threading
import mysql.connector
from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

import config
from erros import ErroFonteExterna, ErroHTTP, ErroValidacao
from logger import registrar
from routes import api
from receptor_udp import iniciar_receptor

MENSAGENS_HTTP = {
    400: "Requisição inválida.", 404: "Recurso não encontrado.",
    405: "Método não permitido.", 413: "Corpo da requisição grande demais.",
    415: "Tipo de conteúdo não suportado.",
}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


def criar_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024
    app.json.ensure_ascii = False
    app.register_blueprint(api)

    @app.get("/")
    def pagina_inicial():
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(ErroHTTP)
    def _erro_http(e):
        return jsonify({"erro": e.mensagem}), e.status

    @app.errorhandler(ErroValidacao)
    def _erro_validacao(e):
        registrar("validacao", "rejeitada", ",".join(sorted(e.erros)))
        return jsonify({"erro": "Dados inválidos.", "campos": e.erros}), 422

    @app.errorhandler(ErroFonteExterna)
    def _erro_fonte(e):
        return jsonify({"erro": "Serviço de previsão indisponível no momento."}), 502

    @app.errorhandler(mysql.connector.Error)
    def _erro_banco(e):
        registrar("banco_de_dados", "falha", type(e).__name__)
        return jsonify({"erro": "Serviço temporariamente indisponível."}), 503

    @app.errorhandler(HTTPException)
    def _erro_werkzeug(e):
        return jsonify({"erro": MENSAGENS_HTTP.get(e.code, "Requisição inválida.")}), e.code

    @app.errorhandler(Exception)
    def _erro_inesperado(e):
        registrar("erro_interno", "falha", f"{type(e).__name__}: {e}")
        return jsonify({"erro": "Erro interno. Tente novamente mais tarde."}), 500

    @app.after_request
    def _cabecalhos(resposta):
        resposta.headers["Content-Security-Policy"] = CSP
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers.setdefault("Cache-Control", "no-store")
        return resposta

    registrar("aplicacao", "iniciada", f"porta={config.FLASK_PORT}")
    return app


if __name__ == "__main__":
    t = threading.Thread(target=iniciar_receptor, daemon=True)
    t.start()
    criar_app().run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)