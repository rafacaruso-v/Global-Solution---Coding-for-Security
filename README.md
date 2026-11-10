# AlertaChuva SP (Feito com IA)

Protótipo **CitizenTech** (Global Solution FIAP): aviso de chuva forte para moradores de
áreas sujeitas a alagamento e enxurrada na cidade de São Paulo. O cidadão consulta o risco
da sua região, se inscreve (com consentimento) e recebe um alerta curto quando a previsão
atinge o nível que ele escolheu.


## O que o projeto entrega

| Requisito | Onde está |
|---|---|
| API REST Flask (GET, POST, PUT, DELETE, status corretos) | `routes.py` (`/api/inscricoes`) |
| MySQL com CRUD em Python, sem ORM, consultas parametrizadas | `db.py`, `schema.sql` |
| Fonte externa com `requests` + JSON | `previsao.py` (Open-Meteo, gratuita, sem chave) |
| Interface web mínima (HTML/CSS/JS) consumindo a API | `static/` |
| Log em arquivo (data/hora, ação, resultado) | `logger.py` → `logs/alerta_chuva.log` |
| Módulo à escolha: **sockets UDP** | `udp_alertas.py` (envio) e `receptor_udp.py` (receptor) |
| Funções, módulos e tratamento de exceções | todos os `.py`; handlers em `app.py` |
| Segurança e LGPD | seção abaixo e `RELATORIO.md` |

## Como executar do zero

**Pré-requisitos:** Python 3.10+, MySQL 8.0+ e acesso à internet (para a Open-Meteo).

```bash     
pip install -r requirements.txt
```

# 2) Banco de dados (como administrador do MySQL)
mysql -u root -p < schema.sql
mysql -u root -p -e "CREATE USER 'root'@'localhost';
                     GRANT SELECT, INSERT, UPDATE, DELETE ON alerta_chuva.* TO 'root'@'localhost';"

# 3) Edite o .env com a senha do seu MySQL

Depois, apenas rode o seguinte comando:

```bash
python app.py
```

Abra **http://127.0.0.1:5000**.

### Roteiro de demonstração (2 minutos)
1. Escolha uma região e veja o nível de risco calculado com a previsão real.
2. Em "Receber alertas", preencha apelido, região, marque o consentimento e envie. Guarde o código de gestão exibido.
3. Abra "Painel do operador", informe a `ADMIN_API_KEY`, escolha a mesma área e a fonte **"Simular nível Alerta"** (num dia sem chuva a previsão real é "baixo" e nada é enviado) e clique em **Enviar alerta por UDP**.
4. O Terminal mostra o alerta recebido e a interface exibe "entregue e confirmado".
5. Volte ao formulário: altere o nível ou clique em **Cancelar inscrição** (apaga os dados).

## Endpoints

| Método e rota | Quem usa | Credencial | Sucesso | Erros possíveis |
|---|---|---|---|---|
| `GET /api/areas` | público | nenhuma | 200 | |
| `GET /api/risco?area_id=N` | público | nenhuma | 200 | 404, 422, 429, 502 |
| `POST /api/inscricoes` | cidadão | nenhuma (devolve `token`) | **201** | 400, 422, 429 |
| `GET /api/inscricoes` | operador | `X-API-Key` | 200 | 401, 403 |
| `GET /api/inscricoes/<id>` | dono ou operador | `X-Token` ou `X-API-Key` | 200 | 401, 403, 404 |
| `PUT /api/inscricoes/<id>` | dono ou operador | `X-Token` ou `X-API-Key` | 200 | 400, 401, 403, 404, 422 |
| `DELETE /api/inscricoes/<id>` | dono ou operador | `X-Token` ou `X-API-Key` | **204** | 401, 403, 404 |
| `POST /api/alertas/disparar` | operador | `X-API-Key` | 201 (ou 200 se nada foi enviado) | 401, 403, 404, 422 |
| `GET /api/alertas` | operador | `X-API-Key` | 200 | 401, 403 |

Códigos: `400` JSON inválido · `401` sem credencial · `403` credencial errada · `404` não existe ·
`413` corpo grande · `422` dados inválidos · `429` limite de requisições · `502` fonte externa fora ·
`503` banco indisponível.


## Como o risco é calculado

A Open-Meteo devolve a chuva prevista hora a hora (mm). Somamos as próximas 24 h e olhamos o pico de 1 h:

| Nível | Chuva em 24 h | ou pico em 1 h |
|---|---|---|
| Baixo | abaixo de 30 mm | abaixo de 10 mm |
| Atenção | 30 mm ou mais | 10 mm/h ou mais |
| Alerta | 60 mm ou mais | 25 mm/h ou mais |
| Crítico | 100 mm ou mais | 40 mm/h ou mais |

**Os limiares são ilustrativos** Alertas oficiais vêm da Defesa Civil, CEMADEN e INMET.

## Segurança e LGPD (resumo)

- **Consultas parametrizadas** (`%s`) em todo o `db.py`; nenhum SQL é montado com texto do usuário.
- **Validação de toda entrada** por lista de permissão (`validar.py`): tipos estritos, regex de apelido, campos extras rejeitados, corpo limitado a 4 KB.
- **Mensagens de erro genéricas**: stack trace, SQL e dados de conexão nunca chegam ao cliente (`app.py`).
- **Autorização**: o token do cidadão é guardado só como hash SHA-256; comparações em tempo constante; operador usa `X-API-Key`.
- **Limite de requisições** por IP, cabeçalhos de segurança (CSP, `nosniff`, `X-Frame-Options`) e alertas UDP assinados com HMAC.
- **Coleta mínima**: apelido, área (não o endereço), nível desejado e data do consentimento. Sem nome, CPF, telefone ou localização exata. O cancelamento apaga tudo. O log não registra dados pessoais, tokens ou chaves.
- Use **apenas dados fictícios ou abertos**. As áreas do `schema.sql` são pontos de demonstração com coordenadas aproximadas, não o mapeamento oficial de áreas de risco.


Cobrem validação (incluindo entradas maliciosas), classificação de risco, falhas da fonte externa,
assinatura/expiração dos alertas UDP e o limitador de requisições.

A API completa (CRUD, autorização, disparo UDP e interface) foi verificada contra um servidor **MySQL 8.0** real.

## Estrutura

```
app.py            aplicação Flask, handlers de erro e cabeçalhos de segurança
routes.py         endpoints REST
db.py             CRUD em SQL puro (mysql-connector-python)
previsao.py        consumo da Open-Meteo + classificação de risco
udp_alertas.py    sockets UDP: envelope assinado, envio com ACK
receptor_udp.py   receptor UDP de demonstração
validar.py     validação de entrada
seguranca.py      tokens, comparação segura, limitador de requisições
logger.py         log em arquivo
config.py         leitura do .env
schema.sql        tabelas e áreas de demonstração
static/           interface web (index.html, style.css, app.js)
```

## Problemas comuns

- **`Variáveis obrigatórias ausentes no .env`**: preencha `DB_USER`, `DB_PASSWORD`, `ADMIN_API_KEY` e `ALERTA_SEGREDO`.
- **503 "Serviço temporariamente indisponível"**: o MySQL não está acessível ou usuário/senha do `.env` não conferem (veja `logs/alerta_chuva.log`).
- **502 "Serviço de previsão indisponível"**: sem internet ou Open-Meteo fora do ar.
- **"O receptor não confirmou"**: confira se `ALERTA_SEGREDO` e `UDP_PORT` são iguais nos dois lados.