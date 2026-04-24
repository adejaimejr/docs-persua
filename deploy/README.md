# Deploy em producao (Dokploy), docs.persua.com.br

Runbook passo-a-passo pra subir a Base de Conhecimento Persua em producao no dominio `docs.persua.com.br` via Dokploy, **reusando os servicos Postgres + Redis ja existentes no Swarm**.

## Arquitetura final

```
DNS docs.persua.com.br -> VPS Dokploy
                            |
                            +-- Traefik (file provider, /root/swarm/.../dynamic/)
                                |
                                +-- container docmost (Application, porta 3000)
                                       |
                                       +-- TCP -> postgres_postgres:5432 (db dedicado: docmost)
                                       +-- TCP -> redis_redis:6379 (DB 4 reservado)
                                       (mesma rede network_swarm_public)
```

## Pre-requisitos

- Dokploy rodando, Traefik v3 ativo
- Postgres no Swarm: servico `postgres_postgres`, porta 5432
- Redis no Swarm: servico `redis_redis`, porta 6379, DB 4 livre, senha conhecida
- Acesso DNS do dominio `persua.com.br`
- Repo no GitHub: `https://github.com/adejaimejr/docs-persua` (main)

## Passo 1, Configurar DNS

No painel DNS:

```
Tipo: A
Host: docs
Valor: <IP_DO_VPS_DOKPLOY>
TTL: 300
```

> Se usa Cloudflare com proxy laranja, SSL mode = **Full** no painel CF (senao da redirect loop).

Validar: `dig docs.persua.com.br +short` retorna o IP.

## Passo 2, Preparar o Postgres

O Docmost precisa de database + user dedicado pra nao misturar com outros apps.

1. Conectar no Postgres como superuser:
   ```bash
   # Pelo servidor do Swarm
   docker exec -it $(docker ps -q -f name=postgres_postgres) psql -U postgres
   ```

2. Gerar senha forte localmente:
   ```bash
   openssl rand -base64 24
   ```
   Anotar (vai no DATABASE_URL).

3. Editar `sql/setup-postgres.sql`, trocar `<SENHA_FORTE_AQUI>` pela senha gerada.

4. Colar o SQL no psql conectado ao postgres_postgres.

5. Validar:
   ```sql
   \l docmost   -- deve listar a database
   \du docmost  -- deve listar o user
   ```

## Passo 3, Gerar APP_SECRET

```bash
openssl rand -hex 32
```

Anotar (vai no APP_SECRET do Dokploy).

## Passo 4, Pegar a senha do Redis

A senha do `redis_redis` ja existe no Swarm. No Dokploy:
- Apps -> redis_redis -> Environment -> copiar valor de `REDIS_PASSWORD` (ou similar)

Anotar.

## Passo 5, Criar Application no Dokploy

> IMPORTANTE: criar como **Application** (nao Docker Compose). So precisa do Dockerfile, db e redis sao externos.

Na UI Dokploy (`https://deploy-docker.i92tecnologia.com.br`):

1. **Create Application**
2. **Provider:** GitHub
   - Repository: `adejaimejr/docs-persua`
   - Branch: `main`
   - Build Path: `/` (raiz do repo)
   - Trigger Type: On Push (autodeploy)
3. **Build Type:** **Dockerfile** (nao Nixpacks)
   - Dockerfile path: `Dockerfile`
4. **Environment** (aba separada):
   ```
   APP_URL=https://docs.persua.com.br
   APP_SECRET=<valor-do-passo-3>
   DATABASE_URL=postgresql://docmost:<senha-do-passo-2>@postgres_postgres:5432/docmost?schema=public
   REDIS_URL=redis://default:<senha-do-passo-4>@redis_redis:6379/4
   ```
5. **Domains:**
   - Host: `docs.persua.com.br`
   - HTTPS: enabled
   - Certificate: Let's Encrypt
   - Container Port: `3000`
6. **Network:**
   - Garantir que o container vai conectar na rede `network_swarm_public` (default no Dokploy)
7. **Deploy**

## Passo 6, Validar build + roteamento

Apos o Deploy:

1. **Logs:** acompanhar pela aba Logs do Dokploy. Primeiro boot: ~60s pras migrations Postgres rodarem.
2. **Verificar arquivo de roteamento Traefik:**
   ```bash
   ls /root/swarm/stacks/applications/dokploy/data/traefik/dynamic/ | grep docs
   cat /root/swarm/stacks/applications/dokploy/data/traefik/dynamic/<docs-persua>*.yml
   ```
3. **Conferir e corrigir** (Dokploy frequentemente erra esses pontos):
   - Porta deve ser `3000` (nao 5000)
   - certResolver deve ser `letsencryptresolver` (nao `letsencrypt`)
   - Se quiser `www`, usa: `Host(\`docs.persua.com.br\`) || Host(\`www.docs.persua.com.br\`)`
   - Sem router `web` duplicado se Cloudflare proxy ativo

   Template correto:
   ```yaml
   http:
     routers:
       docs-persua-router-websecure:
         rule: "Host(`docs.persua.com.br`)"
         service: docs-persua-service
         middlewares: []
         entryPoints:
           - websecure
         tls:
           certResolver: letsencryptresolver
     services:
       docs-persua-service:
         loadBalancer:
           servers:
             - url: http://docs-persua:3000
           passHostHeader: true
   ```
   Traefik recarrega automaticamente.

4. **Verificar via curl:**
   ```bash
   curl -I https://docs.persua.com.br
   # Deve retornar 200 ou 302 com SSL valido
   ```

## Passo 7, Primeiro acesso

Acessar `https://docs.persua.com.br`. Setup inicial do Docmost:

1. Preencher dados do workspace ("Persua Base de Conhecimento")
2. Criar usuario admin (email + senha forte)
3. Aguardar redirecionamento pro dashboard

## Passo 8, Importar ZIP master

1. Localmente, gerar o ZIP atualizado:
   ```bash
   cd _tools/docmost
   python3 scripts/build_master_zip.py
   ```
   Saida: `import-packages/base-de-conhecimento-master.zip` (60 MB)
2. Em `https://docs.persua.com.br`:
   - **Settings > Import**
   - Format: **Markdown**
   - Upload do ZIP
   - Aguardar (~1-3 min processando 528 imagens)
3. Validar que a raiz "Base de Conhecimento" aparece com 156 paginas

## Passo 9, Compartilhar publicamente

1. Clicar na raiz **"Base de Conhecimento"** no tree
2. Botao **Compartilhar** (canto superior direito)
3. Ativar:
   - **Link publico**
   - **Incluir subpaginas**
4. Copiar a URL gerada. Formato: `https://docs.persua.com.br/share/<shareId>/p/base-de-conhecimento`
5. Anotar `<shareId>` (ex: `uo3o2qp17f`)

Validar: abrir num browser anonimo. Deve exibir a KB sem pedir login.

## Passo 10 (opcional), Redirect raiz `/` -> share publico

Por default, `https://docs.persua.com.br/` abre tela de login. Pra docs publicas, redirecionar a raiz pro share. Duas opcoes:

### Opcao A, Patch no Dockerfile (recomendado, simples)

Editar `Dockerfile`, adicionar antes da ultima linha:

```dockerfile
# Redirect raiz / -> URL publica do share
RUN sed -i 's|</head>|<script>if(location.pathname==="/"\&\&!location.search)location.replace("/share/<SHARE_ID>/p/base-de-conhecimento");</script></head>|' /app/apps/client/dist/index.html
```

(Substituir `<SHARE_ID>` pelo valor do passo 9.)

Commit + push, Dokploy faz autodeploy. Agora `docs.persua.com.br/` redireciona pro share, mas `docs.persua.com.br/share/...` continua normal.

### Opcao B, Middleware no arquivo Traefik dinamico (mais limpo)

Editar `/root/swarm/stacks/applications/dokploy/data/traefik/dynamic/<docs-persua>.yml` adicionando middleware `redirectregex`:

```yaml
http:
  middlewares:
    docs-root-redirect:
      redirectregex:
        regex: "^https://docs\\.persua\\.com\\.br/?$"
        replacement: "https://docs.persua.com.br/share/<SHARE_ID>/p/base-de-conhecimento"
        permanent: true

  routers:
    docs-persua-router-websecure:
      rule: "Host(`docs.persua.com.br`)"
      service: docs-persua-service
      middlewares:
        - docs-root-redirect
      entryPoints:
        - websecure
      tls:
        certResolver: letsencryptresolver

  services:
    docs-persua-service:
      loadBalancer:
        servers:
          - url: http://docs-persua:3000
        passHostHeader: true
```

Cuidado: arquivo e sobrescrito a cada redeploy do Dokploy. Precisa reaplicar.

## Passo 11, Validacao end-to-end

Checklist pos-deploy:

- [ ] `curl -I https://docs.persua.com.br` retorna 200/302 + SSL valido
- [ ] Logo Persua aparece no header
- [ ] Favicon da aba e o icone Persua
- [ ] Sidebar 320px, titulos quebram em 2 linhas sem sobrepor
- [ ] Dark mode funciona
- [ ] Busca `Ctrl+K` encontra paginas
- [ ] Imagens carregam na pagina "Conexao WhatsApp Cloud API"
- [ ] Apos patch redirect: `https://docs.persua.com.br/` redireciona pro share root

## Pos-launch, backlog

- Backup cron do Postgres `docmost` db (pg_dump diario pro S3)
- Analytics (Plausible ou Umami)
- Cores da marca Persua aplicadas no tema (aprovacao chiefs)
- Monitoramento uptime (UptimeRobot, BetterStack)
- Capturar progressivamente as 519 telas Persua restantes no overlay `_persua/`

## Atualizar conteudo em producao

```bash
# 1. Localmente, editar drafts/capturar telas em _persua/
cd _tools/docmost
python3 scripts/build_master_zip.py
git add . && git commit -m "update: nova versao da KB"
git push

# Dokploy faz autodeploy se Trigger Type = On Push (nao precisa porque o ZIP nao e do build)

# 2. Em producao, deletar a raiz "Base de Conhecimento" no Docmost UI
# 3. Settings > Import > upload do ZIP master atualizado
# 4. Recompartilhar (mesmo shareId pode ser preservado se for editar a raiz)
```

## Troubleshooting

### SSL nao emite
- DNS resolveu? `dig docs.persua.com.br +short`
- Cloudflare proxy ativo? SSL mode = Full no CF
- Traefik logs no Dokploy

### Container nao sobe
- Logs do app no Dokploy
- DATABASE_URL/REDIS_URL acessiveis? Testar dentro de outro container na mesma rede:
  ```bash
  docker run --rm --network network_swarm_public alpine \
    sh -c 'apk add postgresql-client && psql postgresql://docmost:SENHA@postgres_postgres:5432/docmost -c "SELECT 1;"'
  ```
- APP_SECRET vazio? Erro tipico de sessoes

### Build do Dockerfile demora ou trava
- Dokploy precisa de RAM (recomendado 4GB+, ver alerta na UI)
- Cache: ativar Clean Cache so se for problema persistente

### Imagens nao carregam apos import
- ZIP tem imagens? `unzip -l base-de-conhecimento-master.zip | grep .png | wc -l`
- FILE_IMPORT_SIZE_LIMIT default 200MB, OK pra ZIP de 60MB

### Share publico pede login
- Toggle "Link publico" ativo? "Incluir subpaginas"?
- Testar em janela anonima

## Referencias

- `Dockerfile` — patches de marca (PT-BR, logo, CSS, favicon)
- `.env.prod.example` — template de env vars
- `sql/setup-postgres.sql` — SQL pra preparar Postgres antes do deploy
- `DEPLOY.md` — contexto de infraestrutura
- `memory.md` — gotchas tecnicos do Docmost
- `scripts/build_master_zip.py` — regera o ZIP de import
