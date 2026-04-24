# Deploy em producao (Dokploy), docs.persua.com.br

Runbook passo-a-passo pra subir a Base de Conhecimento Persua em producao no dominio `docs.persua.com.br` via Dokploy.

## Pre-requisitos

- Dokploy instalado e rodando num VPS (com Traefik ativo)
- Acesso DNS do dominio `persua.com.br` (Registro.br, Cloudflare, etc)
- Git repo do projeto Persua acessivel pelo Dokploy (GitHub, GitLab, Gitea)
- ZIP master gerado em `_tools/docmost/import-packages/base-de-conhecimento-master.zip` (60MB)

## Passo 1. Configurar DNS

No painel do seu provedor DNS, criar registro apontando `docs.persua.com.br` pro IP do VPS Dokploy:

```
Tipo: A
Host: docs
Valor: <IP_DO_VPS_DOKPLOY>
TTL: 300 (ou o minimo permitido)
```

Aguardar propagacao (~5-30 min). Validar com:
```bash
dig docs.persua.com.br +short
```

## Passo 2. Gerar secrets

No seu terminal local, gerar os dois secrets que vao no Dokploy:

```bash
# APP_SECRET (sessions, tokens)
openssl rand -hex 32

# POSTGRES_PASSWORD
openssl rand -base64 24
```

Guardar ambos num gerenciador de senhas (1Password, Bitwarden). Vai precisar no proximo passo.

## Passo 3. Criar aplicacao no Dokploy

Na UI do Dokploy:

1. **Dashboard > Create Application**
2. Tipo: **Docker Compose**
3. **Name**: `docmost-persua` (ou similar)
4. **Source**: Git
   - Repository: seu repo do Persua
   - Branch: `main` (ou a que voce usa)
   - Build Path: `_tools/docmost/`
5. **Compose file**: `docker-compose.prod.yml`
6. Save

## Passo 4. Configurar env vars

Na aba **Environment** do app:

```
APP_URL=https://docs.persua.com.br
APP_SECRET=<valor gerado no passo 2>
POSTGRES_PASSWORD=<valor gerado no passo 2>
```

**Nao** commitar esses valores no repo. Eles vivem so no Dokploy.

## Passo 5. Configurar dominio

Na aba **Domains** do app:

- **Host**: `docs.persua.com.br`
- **HTTPS**: enabled (Let's Encrypt)
- **Port**: 3000 (opcional, ja tem no label Traefik)

Dokploy detecta os labels Traefik do compose e faz o roteamento automatico. SSL e emitido pelo Let's Encrypt via Traefik apos o DNS resolver.

## Passo 6. Deploy inicial

Click **Deploy**. Dokploy vai:

1. Clonar o repo
2. Rodar `docker compose -f docker-compose.prod.yml build`
3. Aplicar o Dockerfile (patches PT-BR, logo Persua, CSS custom, etc)
4. Subir os 3 servicos (docmost, db, redis)
5. Traefik detecta o container e roteia `docs.persua.com.br` pra porta 3000 interna
6. Let's Encrypt emite o SSL (~30-60s apos deploy)

Logs: acompanhar pela aba **Logs** do Dokploy.

## Passo 7. Primeiro acesso

Acessar `https://docs.persua.com.br`. Na primeira vez, Docmost mostra o setup inicial:

1. Preencher dados do workspace (nome: "Persua Base de Conhecimento")
2. Criar usuario admin (email + senha forte)
3. Aguardar redirecionamento pro dashboard

## Passo 8. Importar ZIP master

1. Acessar **Settings > Import** (icone de engrenagem)
2. Selecionar **Markdown**
3. Upload do arquivo local: `_tools/docmost/import-packages/base-de-conhecimento-master.zip`
4. Aguardar (~1-3 min pro upload + processamento das 528 imagens)
5. A raiz "Base de Conhecimento" aparece no tree com 156 paginas

## Passo 9. Compartilhar publicamente

1. Clicar na raiz **"Base de Conhecimento"** no tree
2. Botao **Compartilhar** (canto superior direito)
3. Ativar **"Link publico"** e **"Incluir subpaginas"**
4. Copiar a URL gerada. Formato: `https://docs.persua.com.br/share/<shareId>/p/base-de-conhecimento-<sufixo>`
5. Anotar o `<shareId>` (ex: `uo3o2qp17f`) pro proximo passo

Validar abrindo num browser anonimo (incognito): deve exibir a KB sem pedir login.

## Passo 10 (opcional). Redirect raiz -> share

Por padrao, `https://docs.persua.com.br/` abre a tela de login. Pra fazer redirecionar pra URL do share publico, tem duas opcoes:

### Opcao A. Patch no Dockerfile (recomendada)

Adicionar no final do `Dockerfile`:

```dockerfile
# Redirect raiz / -> URL publica do share
ENV PERSUA_SHARE_ID=<SHARE_ID_DO_PASSO_9>
RUN sed -i 's|</head>|<script>if(location.pathname==="/"\&\&!location.search)location.replace("/share/<SHARE_ID_DO_PASSO_9>/p/base-de-conhecimento");</script></head>|' /app/apps/client/dist/index.html
```

(Substituir `<SHARE_ID_DO_PASSO_9>` pelo valor real.)

Commit + redeploy no Dokploy. Agora `docs.persua.com.br/` redireciona pro share, mas `docs.persua.com.br/share/.../p/...` continua funcionando normalmente.

### Opcao B. Traefik middleware

No `docker-compose.prod.yml`, adicionar labels no servico docmost:

```yaml
- "traefik.http.routers.docmost-persua-root.rule=Host(`docs.persua.com.br`) && Path(`/`)"
- "traefik.http.routers.docmost-persua-root.entrypoints=websecure"
- "traefik.http.routers.docmost-persua-root.tls=true"
- "traefik.http.routers.docmost-persua-root.middlewares=root-to-share"
- "traefik.http.middlewares.root-to-share.redirectregex.regex=^https://docs.persua.com.br/?$$"
- "traefik.http.middlewares.root-to-share.redirectregex.replacement=https://docs.persua.com.br/share/<SHARE_ID>/p/base-de-conhecimento"
- "traefik.http.middlewares.root-to-share.redirectregex.permanent=true"
```

Mais limpo (zero mudanca na imagem), mas mais verboso.

## Passo 11. Validacao end-to-end

Checklist pos-deploy:

- [ ] `curl -I https://docs.persua.com.br` retorna 200 + SSL valido
- [ ] Logo Persua aparece no header
- [ ] Favicon da aba e o icone Persua (testar no tab do browser)
- [ ] Sidebar 320px, titulos quebram em 2 linhas sem sobrepor
- [ ] Dark mode funciona (clicar sol/lua no canto direito)
- [ ] Busca `Ctrl+K` encontra paginas
- [ ] Imagens carregam na pagina "Conexao WhatsApp Cloud API"
- [ ] Apos patch redirect: `https://docs.persua.com.br/` redireciona pro share root

## Pos-launch, backlog

- Backup cron do Postgres (pg_dump diario pro S3 ou rclone)
- Analytics (Plausible ou Umami via CSS injection no Dockerfile)
- Paleta de cores Persua aplicada no tema (aguarda aprovacao dos chiefs)
- Monitoramento uptime (UptimeRobot, BetterStack)
- Popular progressivamente o overlay `_persua/` com telas reais da Persua (atualmente 9/528, restam 519)

## Atualizar conteudo em producao

Fluxo pra publicar mudancas apos deploy inicial:

1. Localmente: editar drafts, capturar telas no `_persua/`, rodar `python3 scripts/build_master_zip.py`
2. Em producao: deletar a raiz "Base de Conhecimento" no Docmost (cascade apaga tudo)
3. Settings > Import > upload do ZIP master atualizado
4. Gerar novo share publico (pode manter o mesmo ID se der sorte, ou atualizar o redirect da opcao A/B com o novo ID)

Alternativa: editar pagina a pagina manualmente no editor Docmost. Melhor pra ajustes pontuais, pior pra lote.

## Troubleshooting

### SSL nao emite
- Validar que DNS resolveu: `dig docs.persua.com.br +short`
- Conferir logs do Traefik no Dokploy (aba Monitoring ou logs do container traefik)
- Tentar forcar renovacao: delete + recria o app

### Docmost nao sobe
- Logs do container: Dokploy aba **Logs** do app
- Primeiro boot demora ~60s pra rodar migrations do Postgres
- Erro `APP_SECRET missing`: verificar env vars no Dokploy

### Imagens nao carregam apos import
- Validar que o ZIP tem as imagens em `assets/<slug>/print-XX.png`
- `unzip -l base-de-conhecimento-master.zip | grep .png | wc -l` no local antes do upload
- Verificar tamanho do upload vs `FILE_IMPORT_SIZE_LIMIT` (200MB default)

### Share publico pede login
- Confirmar que o toggle "Link publico" esta ativo na tela de compartilhamento
- Se a raiz tem subpaginas, ativar "Incluir subpaginas" tambem
- Testar em janela anonima

## Referencias

- `docker-compose.prod.yml` na raiz do `_tools/docmost/`
- `.env.prod.example` (template de secrets)
- `Dockerfile` (patches de marca, aplicado no build)
- `memory.md` (gotchas tecnicos, setup notes)
- `scripts/build_master_zip.py` (regera o ZIP quando atualizar drafts)
