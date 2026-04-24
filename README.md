# docs-persua

Base de Conhecimento da **Persua**, self-hosted via [Docmost](https://docmost.com) com patches de marca e deploy em Dokploy.

**URL de producao:** https://docs.persua.com.br

---

## O que esse repo tem

Tudo o que o Dokploy precisa pra fazer build + deploy da Base de Conhecimento. Inclui tambem scripts de manutencao de conteudo (converter docs da fonte pra drafts Persua, gerar ZIP master pra import).

```
docs-persua/
├── Dockerfile              # Build custom: patches PT-BR, logo, CSS, favicon
├── docker-compose.yml      # APENAS dev local (http://localhost:3000)
├── .env.prod.example       # Template de secrets, preencher no Dokploy UI
├── brand/                  # Assets de marca (logo, favicon, CSS custom)
│   ├── persua-logo.png
│   ├── persua-logo-dark.png
│   ├── persua-icon.png
│   └── persua-custom.css
├── sql/
│   └── setup-postgres.sql  # SQL pra criar db+user no Postgres compartilhado
├── scripts/                # Python, manutencao de conteudo
│   ├── build_master_zip.py
│   └── convert_flw_to_persua.py
├── drafts/                 # Conteudo adaptado pra Persua (piloto + overlay _persua/)
├── deploy/
│   └── README.md           # Runbook de deploy passo-a-passo
├── DEPLOY.md               # Contexto de infraestrutura pro Dokploy
├── CLAUDE.md               # Contexto pra IAs que trabalham no projeto
├── memory.md               # Decisoes tecnicas + gotchas
├── sessions.md             # Log narrativo das sessoes de trabalho
└── tasks.md                # Backlog + historico
```

## Arquitetura de producao

**Application + Dockerfile** no Dokploy (NAO Compose). Reusa Postgres e Redis ja existentes no Swarm:

```
docs.persua.com.br -> Traefik -> docs-persua (container, porta 3000)
                                      |
                                      +-- TCP -> postgres_postgres:5432 (db dedicado)
                                      +-- TCP -> redis_redis:6379/4 (DB 4 reservada)
```

---

## Deploy rapido

Veja o runbook completo em [`deploy/README.md`](deploy/README.md). Resumo:

1. **DNS:** `docs.persua.com.br` apontando pro VPS Dokploy
2. **Gerar secrets:** `openssl rand -hex 32` (APP_SECRET) + `openssl rand -base64 24` (POSTGRES_PASSWORD)
3. **Dokploy UI:** novo app, conectar esse repo, preencher env vars, definir dominio
4. **Aguardar deploy + SSL** (~2 min)
5. **Primeiro acesso:** criar workspace admin
6. **Importar ZIP master:** `Settings > Import > Markdown` (ZIP gerado localmente via `scripts/build_master_zip.py`)
7. **Compartilhar raiz** publicamente com "Incluir subpaginas"

Ver [`DEPLOY.md`](DEPLOY.md) pro contexto da infraestrutura.

---

## Desenvolvimento local

```bash
# Clonar
git clone https://github.com/adejaimejr/docs-persua.git
cd docs-persua

# Subir Docmost local
docker compose up -d

# Abrir no navegador
open http://localhost:3000
```

O container local usa o mesmo Dockerfile de producao, entao todos os patches de marca aparecem igual.

---

## Atualizar conteudo

```bash
# 1. Se mudou drafts, regera o ZIP master
python3 scripts/build_master_zip.py

# 2. Apaga a raiz "Base de Conhecimento" no Docmost de producao (Settings UI)
# 3. Importa o novo ZIP master (Settings > Import > Markdown)
```

---

## Licenca

[AGPL-3.0](https://github.com/docmost/docmost/blob/main/LICENSE) (herdada do Docmost).

---

## Links

- **Docmost:** https://docmost.com
- **Dokploy:** https://dokploy.com
- **Projeto Persua (workspace interno):** privado
