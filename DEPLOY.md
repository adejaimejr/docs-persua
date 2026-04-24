# DEPLOY — Contexto de Infraestrutura Persua (Dokploy)

> **Status:** versao inicial, para dar contexto a qualquer IA em conversas sobre deploys.
> Ajustar conforme a gente aprender na pratica e concluir o primeiro deploy.

Este documento descreve a infraestrutura real onde a Base de Conhecimento Persua (Docmost) vai rodar em producao. Serve como contexto persistente pra qualquer IA que ajudar com deploys dessa ou de outras aplicacoes.

---

## Contexto: Deploy de Aplicativo no Dokploy (Docker Swarm + Traefik v3)

### Infraestrutura

- **Docker Swarm** com **Traefik v3.3.3** como reverse proxy
- **Dokploy** gerencia apps via file provider do Traefik
- **Arquivos de roteamento** em: `/root/swarm/stacks/applications/dokploy/data/traefik/dynamic/`
- **Rede publica do Swarm:** `network_swarm_public`
- **Certificate resolvers disponiveis:**
  - `letsencryptresolver` (padrao)
  - `letsencrypt` (alias para apps Dokploy)
- **Dokploy UI:** `https://deploy-docker.i92tecnologia.com.br`

---

### Passo 1, Criar o app no Dokploy UI

1. Acessar `https://deploy-docker.i92tecnologia.com.br`
2. Criar novo projeto/app
3. Conectar repositorio GitHub
4. Escolher **Build Type**:
   - **Dockerfile** → se o repo tem Dockerfile (preferivel para controle de porta)
   - **Nixpacks** → se nao tem Dockerfile (porta padrao sera 5000)

---

### Passo 2, Configurar dominio no Dokploy UI

Na aba **Domains** do app:

- **Host:** `dominio.com.br`
- **HTTPS:** ativado
- **Certificate:** Let's Encrypt
- **Container Port:** informar a porta CORRETA do app (ver tabela abaixo)

---

### Passo 3, Identificar a porta correta

| Build Type | Porta padrao |
|---|---|
| Nixpacks | 5000 |
| Dockerfile com nginx | 80 |
| Dockerfile com node/express | a do `EXPOSE` no Dockerfile |

Para confirmar a porta apos o deploy:

```bash
docker exec $(docker ps -q -f name=traefik) \
  wget -qO- http://<nome-servico>:<porta> 2>&1 | head -3
```

Se retornar HTML = porta correta. Se der "Connection refused" = tentar outra porta.

---

### Passo 4, Corrigir o arquivo de roteamento gerado

O Dokploy gera um arquivo `.yml` em `/etc/dokploy/traefik/dynamic/` que **frequentemente precisa de correcao**.

Apos o deploy:

```bash
cat /root/swarm/stacks/applications/dokploy/data/traefik/dynamic/<nome-app>*.yml
```

#### Problemas comuns e correcoes

**Problema 1 — Porta errada**
O Dokploy gera porta 5000 mas o app usa 80 (ou vice-versa).

**Problema 2 — certResolver errado**
O Dokploy gera `letsencrypt` mas pode precisar de `letsencryptresolver` dependendo da configuracao.

**Problema 3 — www nao funciona**
A sintaxe correta no Traefik v3 para multiplos hosts e:

```yaml
rule: "Host(`dominio.com.br`) || Host(`www.dominio.com.br`)"
```

NAO usar: `` Host(`dominio.com.br`, `www.dominio.com.br`) `` , essa e sintaxe v2 e nao funciona.

**Problema 4 — Redirect loop (ERR_TOO_MANY_REDIRECTS)**
Remover o router `web` com `redirect-to-https` do arquivo: o redirect ja e feito globalmente pelo Traefik.

---

### Passo 5, Template correto do arquivo de roteamento

```bash
cat > /root/swarm/stacks/applications/dokploy/data/traefik/dynamic/<nome-app>.yml << 'EOF'
http:
  routers:
    <nome-app>-router-websecure:
      rule: "Host(`dominio.com.br`) || Host(`www.dominio.com.br`)"
      service: <nome-app>-service
      middlewares: []
      entryPoints:
        - websecure
      tls:
        certResolver: letsencryptresolver

  services:
    <nome-app>-service:
      loadBalancer:
        servers:
          - url: http://<nome-app>:<porta>
        passHostHeader: true
EOF
```

O Traefik recarrega automaticamente, nao precisa reiniciar nada.

---

### Passo 6, Verificar se funcionou

```bash
# Router sendo lido pelo Traefik?
docker exec $(docker ps -q -f name=traefik) \
  wget -qO- http://localhost:8080/api/http/routers | \
  python3 -m json.tool | grep -A3 "<nome-app>"

# Site respondendo?
curl -sk https://dominio.com.br | head -3
curl -sk https://www.dominio.com.br | head -3
```

---

### Atencao, Cloudflare

- Se o dominio tem **proxy Cloudflare ativo (nuvem laranja)**: SSL mode deve ser **Full** no painel Cloudflare, caso contrario havera redirect loop.
- Se o dominio esta com **DNS only (nuvem cinza)**: funciona direto com Let's Encrypt sem configuracao adicional.

---

### Atencao, Redeploy

Toda vez que fizer redeploy no Dokploy, o arquivo `.yml` e sobrescrito com os valores padrao incorretos. Sempre verificar e corrigir apos redeploy:

1. Porta correta
2. `certResolver` correto
3. `www` incluido na rule
4. Sem router `web` duplicado (se Cloudflare proxy ativo)

---

## Contexto especifico da Base de Conhecimento Persua (Docmost)

### Deploy alvo
- **Dominio:** `docs.persua.com.br`
- **App:** Docmost self-host (community edition) + Postgres + Redis
- **Build Type no Dokploy:** **Dockerfile** (tem Dockerfile customizado com patches PT-BR, logo, CSS)
- **Container Port esperado:** `3000` (definido no compose, default do Docmost)

### Stack de containers
1. **docmost** (principal), porta interna `3000`, imagem custom `persua-docmost:pt-br` (build do Dockerfile local)
2. **db** (Postgres 16-alpine), porta interna `5432`, rede interna
3. **redis** (Redis 7.2-alpine), porta interna `6379`, rede interna

### Arquivos relevantes no repo (`_tools/docmost/`)
- `Dockerfile`: aplica patches PT-BR, logo Persua, CSS custom, favicon, rowHeight do react-arborist
- `docker-compose.yml`: versao dev local (`localhost:3000`)
- `docker-compose.prod.yml`: versao prod (TBD, possivelmente desnecessaria se Dokploy usar file provider ao inves de labels)
- `.env.prod.example`: template de env vars (`APP_URL`, `APP_SECRET`, `POSTGRES_PASSWORD`)
- `deploy/README.md`: runbook genial de 11 passos (escrito antes de saber da arquitetura Swarm + file provider, pode precisar de update)

### Env vars obrigatorias
```
APP_URL=https://docs.persua.com.br
APP_SECRET=<openssl rand -hex 32>
POSTGRES_PASSWORD=<openssl rand -base64 24>
```

### Dados a importar pos-deploy
- ZIP master em `_tools/docmost/import-packages/base-de-conhecimento-master.zip` (60 MB)
- 156 paginas, 528 imagens
- Importar via `Settings > Import > Markdown` apos criar workspace admin

### Gotchas especificos do Docmost
- **Primeiro boot**: ~60s pra rodar migrations Postgres
- **Share publico**: precisa ativar "Link publico" + "Incluir subpaginas" na raiz
- **URLs de share**: `https://docs.persua.com.br/share/<shareId>/p/<pageSlug>`
- **APP_SECRET**: trocar invalida sessoes. Producao comeca limpa, zero problema
- **FILE_IMPORT_SIZE_LIMIT**: 200MB default, ZIP de 60MB OK
- **Build no Dokploy**: precisa rodar o Dockerfile custom (senao perde os patches de marca)

### Redirect raiz (docs.persua.com.br/) pro share publico
Por default, `/` abre tela de login do Docmost. Pra funcionar como help center publico, duas opcoes:

**Opcao A, Patch no Dockerfile** (mais simples):
```dockerfile
RUN sed -i 's|</head>|<script>if(location.pathname==="/"\&\&!location.search)location.replace("/share/<SHARE_ID>/p/base-de-conhecimento");</script></head>|' /app/apps/client/dist/index.html
```

**Opcao B, Middleware no arquivo de roteamento Traefik** (mais limpo, se Dokploy usar file provider):
```yaml
http:
  middlewares:
    docs-root-redirect:
      redirectregex:
        regex: "^https://docs\\.persua\\.com\\.br/?$"
        replacement: "https://docs.persua.com.br/share/<SHARE_ID>/p/base-de-conhecimento"
        permanent: true
```

Ambas requerem deploy em 2 fases: primeiro sobe, cria share, anota `<SHARE_ID>`, depois aplica o redirect.

---

## Licoes aprendidas (a atualizar)

<!-- A cada deploy, adicionar aqui gotchas novos que forem descobertos -->

### Deploy da Base de Conhecimento Persua
- [ ] A fazer: primeiro deploy de teste
- [ ] Conferir se Dokploy usa labels Traefik do compose ou gera arquivo file provider (provavelmente file provider, pelo padrao descrito)
- [ ] Confirmar container port que o Dokploy detecta/requer na UI
- [ ] Validar se build do Dockerfile funciona (patches de marca aplicados)
- [ ] Documentar o path real do arquivo `.yml` gerado pelo Dokploy pro docmost
- [ ] Decidir redirect raiz (Opcao A vs B) apos ver como Dokploy gera o arquivo

---

## Referencias

- **Docmost community edition:** https://docmost.com/docs/self-hosting/docker-compose
- **Dokploy docs:** https://docs.dokploy.com/
- **Traefik v3 file provider:** https://doc.traefik.io/traefik/providers/file/
- **Repo Persua:** `_tools/docmost/` na raiz do projeto Persua
