# NOC · Monitor de Serviços (Dashboard)

Sistema web para monitorar serviços por **ICMP (ping)**, **TCP (porta)** ou
**HTTP/HTTPS**. Cada serviço é um cartão com imagem personalizada, status em
tempo real (verde/amarelo/vermelho) e posição livre no painel — arraste e
solte para organizar, a posição fica salva.

## Funcionalidades

- Cadastro de serviços com upload de imagem
- Monitoramento em segundo plano (ICMP, TCP, HTTP/HTTPS)
- Dashboard em tempo real (polling a cada 5s, sem precisar recarregar)
- Cartões arrastáveis (drag-and-drop) com posição salva automaticamente
- Histórico de verificações por serviço
- Login (Flask-Login)
- Pronto para rodar em Docker, com PostgreSQL em produção e SQLite em dev

## Arquitetura

- **Frontend:** HTML5, CSS, JavaScript, [Interact.js](https://interactjs.io) (drag-and-drop)
- **Backend:** Python (Flask) + SQLAlchemy
- **Banco de dados:** SQLite (dev) / PostgreSQL (produção)

```
noc-dashboard/
├── app/
│   ├── __init__.py       # app factory, inicializa DB, login e monitor
│   ├── models.py         # User, Service, Historico
│   ├── auth.py           # login/logout
│   ├── routes.py         # dashboard, cadastro, histórico
│   ├── api.py            # /api/status, /api/servicos/<id>/posicao
│   ├── monitor.py        # thread de verificação ICMP/TCP/HTTP
│   ├── static/{css,js,uploads}/
│   └── templates/
├── config.py
├── run.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Como rodar localmente (SQLite)

```bash
cd noc-dashboard
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run.py
```

Acesse **http://localhost:5000** — login inicial: `admin` / `admin123`
(troque a senha depois de entrar, criando outro usuário se preferir; não há
tela de gestão de usuários nesta versão — pode ser criado via shell:
`flask shell` → `User(...)`).

## Como rodar com Docker (produção, com PostgreSQL)

```bash
docker compose up --build
```

Isso sobe o container da aplicação (Gunicorn) e um PostgreSQL. O
monitoramento ICMP dentro do container usa a capability `NET_RAW`
(já configurada no `docker-compose.yml`).

Acesse **http://localhost:5000**.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | (dev) | Chave de sessão do Flask |
| `DATABASE_URL` | SQLite local | String de conexão (use PostgreSQL em produção) |
| `MONITOR_INTERVAL` | `10` | Segundos entre ciclos de verificação |
| `CHECK_TIMEOUT` | `3` | Timeout (s) de cada verificação |
| `DEGRADED_THRESHOLD_MS` | `500` | Latência acima da qual o serviço fica "amarelo" |

## Fases do projeto (conforme escopo original)

1. ✅ Estrutura Flask
2. ✅ Banco de dados (SQLAlchemy: `services`, `historico`, `users`)
3. ✅ Cadastro de serviços (com upload de imagem)
4. ✅ Dashboard (cartões em tempo real)
5. ✅ Monitoramento (ICMP / TCP / HTTP / HTTPS em thread de segundo plano)
6. ✅ Drag-and-drop (Interact.js + persistência de posição via API)
7. ✅ Histórico (por serviço, últimos 200 registros)
8. ✅ Login (Flask-Login)
9. ✅ Docker (Dockerfile + docker-compose com PostgreSQL)

## Notas de segurança / próximos passos sugeridos

- Trocar a senha padrão do usuário `admin` assim que possível.
- Definir `SECRET_KEY` forte via variável de ambiente em produção.
- Adicionar HTTPS (reverse proxy como Nginx/Traefik) na frente do Gunicorn.
- Se for expor publicamente, considerar rate limiting no login.
