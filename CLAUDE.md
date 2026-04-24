# Docmost, Tutoriais Persua

Stack local de help center dos tutoriais da Persua, rodando em Docker.

## O que e
- Docmost self-host (community edition) com patches: PT-BR default, sem "Powered by", lang="pt-BR", title custom, logo Persua, favicon Persua, sidebar larga
- Custom image: `persua-docmost:pt-br` (built from Dockerfile aqui)
- URL local: http://localhost:3000
- Dados em Docker volumes: `docmost_data`, `db_data`, `redis_data`

## Arquivos chave
- `docker-compose.yml`, stack completo (Docmost + Postgres + Redis)
- `Dockerfile`, aplica patches no bundle compilado do Docmost (obrigatorios + opcionais reversiveis)
- `brand/`, assets da marca Persua copiados pra dentro do container (logo + favicon)
- `scripts/build_master_zip.py`, gerador idempotente do ZIP master (roda quando quiser)
- `cache/flw-raw/`, markdown bruto puxado do MCP docs.flw.chat (NAO editar, cache da fonte da verdade)
- `drafts/`, rascunhos adaptados pra Persua em Markdown (processavel, regeneravel)
- `drafts/assets/<slug>/`, imagens baixadas via MCP, placeholders pra serem substituidos por screenshots Persua
- `import-packages/`, ZIPs prontos pra import no Docmost (Settings > Import)
- `tasks.md`, backlog e progresso dos tutoriais
- `sessions.md`, log narrativo das sessoes de trabalho
- `memory.md`, decisoes duraveis e gotchas

## Fluxo de trabalho (importante)
1. Usar MCP `documentacao-ref` (puxa de flw.chat, mesmo white-label Helena)
2. Salvar bruto em `cache/flw-raw/<slug>.md` (nunca mais puxar de novo)
3. Adaptar conteudo pra Persua em `drafts/<slug>.md`: marcadores `[PRINT XX → arraste: ...]`, callouts `:::info/success/warning`, link Meta docs oficial
4. Baixar imagens via curl pra `drafts/assets/<slug>/print-XX.png`
5. Capturar tela equivalente na Persua e dropar em `drafts/assets/<slug>/_persua/print-XX.png` (mesmo nome)
6. Rodar `python3 scripts/build_master_zip.py` pra regenerar o ZIP master (usa overlay `_persua/` automaticamente)
7. Usuario importa UMA VEZ o ZIP master, depois copia conteudo do draft e cola em paginas existentes (evita duplicacao)

## Overlay `_persua/` (de-para de imagens)
- Pra cada `<slug>/print-XX.png`, se existir `<slug>/_persua/print-XX.png`, o build usa a Persua
- Senao usa a flw e lista como "pendente de captura" no relatorio do build
- MCP re-pull nao toca em `_persua/`, as capturas sobrevivem
- Ver `memory.md` secao "Overlay _persua/" pra detalhes

## Comandos uteis
```bash
# Status da stack
docker compose ps

# Logs ao vivo
docker compose logs -f docmost

# Regenerar ZIP master (zero custo MCP, roda a qualquer momento)
python3 scripts/build_master_zip.py

# Rebuild da imagem Docker (aplicar patches novos do Dockerfile)
docker compose build --no-cache docmost
docker compose up -d docmost

# Atualizar Docmost para nova versao
docker pull docmost/docmost:latest
docker compose build --no-cache docmost
docker compose up -d docmost

# Parar sem apagar dados
docker compose stop
```

## Contexto externo
- Ver `persua/CLAUDE.md` (raiz) para regras globais de documentacao da Persua
- MCP `documentacao-ref` pode desconectar entre sessoes. Reconectar com: `claude mcp add documentacao-ref --scope user --transport http https://docs.flw.chat/~gitbook/mcp`

## Deploy em producao
- Destino: `docs.persua.com.br` via Dokploy (Docker Compose + Traefik)
- Ver `deploy/README.md` pra runbook passo-a-passo
- Arquivos: `docker-compose.prod.yml`, `.env.prod.example`, `Dockerfile` (reusado)
- Diferencas vs dev: sem portas expostas, env vars parametrizados, labels Traefik, rede externa dokploy-network
- Redirect raiz -> share: patch no Dockerfile com shareId hardcoded (passo 10 do runbook)

## Limitacoes conhecidas
- API Keys, SSO, Audit log, IA chat, verificacao de paginas: bloqueadas (features da EE, NAO destravar)
- Links internos entre paginas: slug gerado dinamicamente, nao da pra pre-definir no markdown
- Sem analytics nativo: considerar Plausible/Umami via CSS injection se virar prioridade

## Antes de comecar qualquer sessao
1. Ler este CLAUDE.md
2. Ler `tasks.md` para ver o que falta
3. Ler `sessions.md` ultimas 2-3 entradas para pegar contexto recente
4. Ler `memory.md` para evitar repetir erros
5. Verificar se MCP `documentacao-ref` esta conectado (tende a desconectar entre sessoes)
