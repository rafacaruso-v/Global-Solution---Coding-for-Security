"""Exceções de domínio. As mensagens aqui são seguras para chegar ao cliente."""


class ErroHTTP(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


class ErroValidacao(Exception):
    def __init__(self, erros):
        super().__init__("Dados inválidos.")
        self.erros = erros


class ErroFonteExterna(Exception):
    """A fonte externa de dados (Open-Meteo) falhou ou respondeu algo inesperado."""
