# Sessions Log, Docmost Tutoriais

Log narrativo de cada sessao de trabalho. Entrada mais recente no topo.

---

## 2026-04-23, Sessao 8, Logo dark mode + spacing do sidebar (consulta chiefs)

**Contexto:** Sessao 7 fixou a barra e o logo. User aprovou, pediu 2 coisas:
1. Logo dark quando modo dark estiver ativo
2. Sidebar com titulos longos quebrando em 2 linhas, sem espacamento correto entre items

**Consulta aos chiefs (paralela):**
- Design Chief: diagnostico + CSS de spacing (32px min-height, padding-block 5px, align-items flex-start, margin-block 1px entre items). Padrao Notion/Linear/Mintlify
- Brand Chief: emojis como icones OK pra Persua (conversacional/brasileiro/PME). SVG custom seria corporate demais. Hierarquia atual funciona. Dark mode risco zero com emojis (OS renderiza e adapta).

**Fixes aplicados:**
1. **Logo dark**:
   - `Logo_fundo_transparente_escuro.png` (23KB) copiado pra `brand/persua-logo-dark.png`
   - CSS troca via `[data-mantine-color-scheme="dark"] body::before { background-image: url(dark) }`
   - Fallback via `@media (prefers-color-scheme: dark) [data-mantine-color-scheme="auto"]`
   - Dockerfile copia o PNG dark pra `/app/apps/client/dist/persua-logo-dark.png`
2. **Spacing sidebar**:
   - `min-height:32px + padding-block:5px + margin-block:1px` nos items da tree
   - `align-items:flex-start` no container, `align-self:flex-start` nos filhos, pra alinhar icone no TOPO com texto multi-linha (nao centralizar)
   - `line-height:1.35` (subiu de 1.3 pra dar micro-respiro interno)
3. Cache bust pra `?v=4`

**Proximo passo:**
- User hard refresh (Cmd+Shift+R), valida:
  - Logo escura em dark mode, clara em light mode
  - Titulos longos (QR Code Coexistencia, Verificar Portfolio, etc) tem respiro entre items
  - Icones alinhados no topo quando texto quebra em 2 linhas
- Se OK, popular Tier 1 via MCP

---

## 2026-04-24, Sessao 12, Deploy ao vivo em docs.persua.com.br

**Status:** Base de Conhecimento Persua publicada e funcionando em producao.

**URL publica:** https://docs.persua.com.br/share/o8yw2uvuas/p/base-de-conhecimento-zKTcPfquod
**URL com redirect raiz:** https://docs.persua.com.br/ (cai direto na KB via JS redirect)

### Fluxo de deploy executado

1. **Repo dedicado** github.com/adejaimejr/docs-persua criado e populado (29 arquivos, 1MB versionado)
2. **Aplicacao no Dokploy** criada como Application + Dockerfile (NAO Compose)
3. **Postgres compartilhado** (`postgres_postgres`): db `docmost` + user dedicado, senha hex
4. **Redis compartilhado** (`redis_redis`): DB 4 reservado, senha do Swarm
5. **Build OK** apos rebuild (patches PT-BR, logo, CSS, dark logo, redirect)
6. **SSL emitido** via Let's Encrypt automatico (Traefik)

### Problemas encontrados e fix

1. **DATABASE_URL inválida**: senha base64 com `+/=` quebra o parser. Fix: `openssl rand -hex 24` em vez de `-base64`.

2. **Storage volatil no primeiro import**: container processou import com volume nao montado. Resultado: 156 paginas no DB mas zero arquivos no `/app/data/storage`. Fix: adicionar volume `docs-persua-data` em `/app/data/storage`, esperar container estabilizar, deletar raiz, reimportar.

3. **Service status `2/1 replicas`** depois de update: causava task pending com erro "max replicas per node exceed". Fix: `docker service update --replicas-max-per-node 0 docs-persua-rccr3e`.

4. **Storage local em multi-node Swarm**: volume nomeado e local ao node. Fix: `docker service update --constraint-add 'node.hostname==manager1' docs-persua-rccr3e`.

### Reimport bem sucedido

Apos volume montado e container estavel:
- 20:06 → upload do ZIP (60MB)
- 20:08 → 531 imagens processadas, 67.8MB final no volume
- 20:09 → todas as imagens carregando no share publico

### Redirect raiz configurado

Patch `sed` adicionado no Dockerfile injetando `<script>` que faz `location.replace("/share/<id>/p/base-de-conhecimento-<sufixo>")` quando o pathname for `/`.

Script auxiliar criado: `scripts/update-share-id.sh <URL>` automatiza a troca do shareId no Dockerfile a cada reimport.

### Workflow de updates escolhido pelo CEO

**Caminho 2 (atualizar via ZIP)** decidido como padrao:
1. Edita drafts + dropa imagens em `_persua/` localmente
2. `python3 scripts/build_master_zip.py` gera novo ZIP
3. Git commit + push (mantem repo sincronizado)
4. No Docmost UI: deleta raiz + esvazia lixeira + Settings > Import
5. Recompartilha publicamente, pega novo shareId
6. `./scripts/update-share-id.sh <URL_DO_NOVO_SHARE>`
7. Git commit + push -> Dokploy autodeploy do redirect

### Proximo passo (sessao 13+)

User vai capturar varias telas Persua e atualizar overlay `_persua/`. Sessao seguinte vai assistir o fluxo de batch update + reimport + redirect.

### Arquivos atualizados/criados

- `Dockerfile` (linha de redirect raiz)
- `DEPLOY.md` (documentacao completa do deploy + workflow + gotchas)
- `scripts/update-share-id.sh` (helper pra atualizar shareId)

---

## 2026-04-24, Sessao 11, Setup de deploy em producao (Dokploy + docs.persua.com.br)

**Contexto:** CEO decidiu o dominio `docs.persua.com.br` (aprovado: padrao help center). Ja tem Dokploy rodando em VPS. Quer subir producao com o ZIP master ja pronto (60 MB, 156 paginas, 528 imagens).

**Decisoes tomadas (em planning mode):**
- Comecar limpo em producao, reimportar ZIP master
- Docs publicas (padrao help center)
- Dokploy ja instalado, so deployar

**Arquivos criados:**

1. `docker-compose.prod.yml` - versao prod do compose:
   - Remove `ports: 3000:3000` (acesso so via Traefik)
   - Env vars: `APP_URL`, `APP_SECRET`, `POSTGRES_PASSWORD` parametrizados
   - Labels Traefik: Host, entrypoints, certresolver letsencrypt, redirect HTTP -> HTTPS
   - Rede externa `dokploy-network` (auto-criada pelo Dokploy)
   - Rede interna `docmost-internal` pra db+redis isolados

2. `.env.prod.example` - template de env vars:
   - Comandos pra gerar secrets fortes (`openssl rand -hex 32`, `openssl rand -base64 24`)
   - Instrucoes de preencher no Dokploy UI, NAO commitar real

3. `deploy/README.md` - runbook completo de 11 passos:
   - DNS, gerar secrets, criar app Dokploy, env vars, dominio+SSL
   - Primeiro acesso, importar ZIP, compartilhar publicamente
   - Opcao de redirect raiz -> share (Dockerfile patch ou Traefik middleware)
   - Validacao end-to-end + troubleshooting + fluxo de update

**Decisoes tecnicas:**
- URLs de share: padrao Docmost `/share/<id>/p/<slug>` mantido. Dominio custom ja e o suficiente pra parecer "docs.persua.com.br/..."
- Redirect raiz opcional em 2 fases: primeiro deploy sem, anota shareId, segundo deploy com patch
- Backup/analytics no backlog pos-launch, nao bloqueiam deploy inicial
- POSTGRES_PASSWORD via env var em AMBOS a db E o DATABASE_URL (gotcha chave)

**Proximo passo:**
- User configura DNS `docs.persua.com.br` no provedor
- User gera secrets locally (`openssl`)
- User cria app no Dokploy seguindo o runbook
- Apos deploy, reporta pra eu ajudar com eventuais problemas de SSL/build

---

## 2026-04-24, Sessao 10, Fix imagens truncadas e CRM populado

**Contexto:** User notou que "Novo Agente" e outras paginas estavam sem imagens apos import do ZIP.

**Bug descoberto:** agents do download massivo (sessoes 8-9) receberam respostas TRUNCADAS do MCP `documentacao-ref` pra ~45 paginas. Arquivos no cache/flw-raw tinham o texto mas ZERO tags `<figure>` ou `![`.

**Fix:**
1. Grep identificou 45 candidatos (tem passos mas 0 imagens)
2. Agent re-baixou todos via MCP em batches paralelos: 42 voltaram com imagens, 3 sao legitimamente text-only
3. `convert_flw_to_persua.py` rodou novamente: 540/545 imagens baixadas (99%)
4. ZIP regenerado: de 293 pra 528 imagens, 37.6MB pra 60MB

**Tambem nessa sessao:** populacao do CRM (que estava empty).
- Discovery focado em `/guide/documentacao/crm/*` (path que nao tinha explorado antes, achava que era so `/guide/crm-1`)
- 14 paginas novas descobertas: Contato (4), Carteiras (4), Paineis de Vendas (6)
- +1 complementar de Relatorios: "Como exportar mensagens"
- TREE + SLUG_MAP expandidos
- ZIP de 138 pra 156 paginas

**Proximo passo:** user reimporta ZIP no Docmost, valida que imagens aparecem.

---

## 2026-04-24, Sessao 9, Download massivo e conversao flw -> Persua (de 48 pra 138 paginas)

**Contexto:** User pediu pra baixar todo o conteudo da fonte sem deixar nada pra tras. Passamos da fase de esqueleto/piloto pra fase de popular TODO o conteudo.

**Fases executadas:**

### 1. Discovery do sitemap (~90 URLs)
- MCP `documentacao-ref` explorado a partir dos roots: `/guide`, `/guide/atalhos/faq`, `/guide/documentacao/*`
- Mapeadas 11 secoes macro: Comece Aqui, Conexao WhatsApp, Portfolio, Perfil WAB, Pagamentos Meta, Atendimento, CRM, Apps, Relatorios, Ajustes, FAQ
- Descobertas sub-secoes complexas: Apps tem 11 sub-parents (Campanha, Chatbot, Sequencia, Pagamentos, Agentes IA, Mensagens Agendadas, Chat Interno, Grupos WhatsApp, Tempo Seguranca, Distribuicao, Transcricao)

### 2. Download massivo paralelo
- Dois agents rodando em paralelo:
  - Agent A: FAQ atalhos (21) + Atendimento (21) + Ajustes (13) = 55 paginas
  - Agent B: Apps (33) + Relatorios (3) + FAQ standalone (6) + overlap = 45 paginas
- Total: 100 paginas baixadas (+ piloto existente = 101)
- Zero erros nos agents (100% sucesso)
- Cache salvo em `cache/flw-raw/<slug>.md`

### 3. Script de conversao flw -> Persua
- Criado `scripts/convert_flw_to_persua.py`
- Transformacoes:
  - `{% hint style="X" %}` -> `:::X ... :::` (callouts nativos Docmost)
  - `{% content-ref %}` -> removido (navegacao interna flw nao se traduz)
  - `{% embed url %}` -> removido (videos drive/youtube)
  - `<figure><img src="">` -> `![](path)` (markdown puro)
  - Trocas de marca: "a plataforma" -> "a Persua", preservando "Hunion"
  - Imagens: extract URLs, baixa via urllib pra `drafts/assets/<slug>/print-NN.png`
- Bugs corrigidos durante:
  - URLs do GitBook com `\(1\)` escapados: regex nao capturava corretamente
  - HTTP 400 no download: precisa re-encode path (`(` -> `%28`) via `urllib.parse.quote`
  - `<figure>` HTML nao capturado pelo regex de markdown image

### 4. TREE expandido
- De 48 paginas para 138 paginas
- SLUG_MAP com 100+ entradas mapeando titulos Persua -> slugs de drafts
- Build agora detecta automaticamente: se existe `drafts/<slug>.md`, usa como conteudo; senao placeholder
- 105 paginas populadas com draft, 0 placeholders (exceto paginas parent de secao que geram cards automaticos)

### 5. ZIP master regenerado
- Tamanho: 33 MB (era 1 MB no esqueleto)
- 138 paginas + 245 imagens
- Overlay _persua/: 9 Persua / 236 flw pendentes (3% Persua) — esperado, so o piloto tem capturas Persua

**Decisoes tecnicas:**
- Preferiu delegar download massivo a 2 agents paralelos em vez de fazer inline (economia de context)
- Conversao sintatica automatica (regex-based) em vez de reescrita manual Persua-voz page-by-page, pra ganhar escala (101 paginas seriam semanas de trabalho manual)
- Manter drafts em `drafts/<slug>.md` como fonte unica, nao mover pra outra estrutura
- SLUG_MAP explicito em vez de slugify automatico, pra lidar com titulos Persua que divergem dos slugs flw (ex: "Acessando a Plataforma pela Web" vs slug "acessando-pela-web")

**Proximo passo:**
- User reimporta o ZIP master no Docmost (deleta raiz, importa de novo)
- Validacao visual das 138 paginas
- Captura progressiva de telas Persua no overlay `_persua/` por tutorial
- A cada batch de imagens, regenera ZIP e reimporta (ou substitui inline)

---

## 2026-04-23, Sessao 8, Dark logo + fix real do menu (classes e rowHeight)

**Contexto:** User reportou dois problemas:
1. Dark mode nao troca o logo (fica a versao clara sobre fundo escuro, ilegivel)
2. Menu sidebar continua com sobreposicao entre rows quando titulo quebra em 2 linhas

**Causa raiz dos problemas:**

*Menu (principal descoberta):*
- CSS das tentativas anteriores usava `[class*="TreeNode"]`, `[class*="treeNode"]`, `[class*="page-tree"]` - **essas classes NAO existem no Docmost**
- Classes reais sao scoped CSS modules com `_` minusculo: `_row_tofwf_69`, `_node_tofwf_14`, `_treeNode_1500s_10`
- Por isso nenhuma das tentativas anteriores de ajustar o menu surtiu efeito
- Alem disso, react-arborist configura rowHeight INLINE em JS (`rowHeight:30`) que nem `!important` em CSS bate (porque o JS calcula `top: index * 30` pra cada row absolutamente posicionada)

*Dark logo:*
- Nenhuma CSS de dark mode existia ainda
- Arquivo dark ja disponivel em `persua/_assets/brand/Logo_fundo_transparente_escuro.png` (23KB)

**Fixes aplicados:**

1. **Dockerfile patch: rowHeight:30 → rowHeight:48** via sed no bundle JS
   - Adicionado ao mesmo `RUN find ... -exec sed` dos patches obrigatorios
   - 48px cabe 2 linhas com line-height 1.25 sem sobreposicao
2. **Classes CSS corrigidas** pra `[class*="_row_tofwf"]`, `[class*="_node_tofwf"]`, `[class*="_treeNode_"]`
3. **Override `white-space: nowrap`** no row (Docmost tinha nowrap por default)
4. **align-items: center** no node pra icone ficar vertical-centro com texto de 2 linhas
5. **Dark logo**: copiado de `persua/_assets/brand/` pra `brand/persua-logo-dark.png`
   - Dockerfile `COPY` pra `/app/apps/client/dist/persua-logo-dark.png`
   - CSS com `[data-mantine-color-scheme="dark"]` pra trocar o background-image
   - Fallback `@media (prefers-color-scheme: dark)` pra modo auto
6. Cache bust CSS: `?v=5`

**Descoberta tecnica importante:** rodar `grep -iE 'treenode|_row|_node'` no CSS bundle do Docmost pra achar as classes reais dos CSS modules scopados. Classes com prefixo `_` (underscore minusculo) + hash aleatorio.

**Proximo passo:**
- User hard refresh, valida em light e dark mode
- Testa scroll (garante que sobreposicao sumiu em ambos)
- Se OK, popular Tier 1 via MCP (Acessando Web, Acessando App, Primeiro atendimento)

---

## 2026-04-23, Sessao 7, Fix scroll do logo (position:fixed no lugar de absolute)

**Contexto:** Sessao 6 colocou o logo com `position:absolute` relativo ao header + `position:relative !important` no header + `padding-left:120px` no primeiro filho. Funcionou no estado nao-scrollado, mas na hora de scrollar:
1. Icones do canto direito sumiam (padding empurrava o flex interno pra fora do viewport)
2. Layout se quebrava visualmente

**Causa raiz (descoberta):**
- `position:relative !important` no header sobrescrevia o `position:fixed` default do Mantine, fazendo o header scrollar com o conteudo
- `padding-left:120px` no `> *` funcionava so em repouso, mas como o flex interno tem width:100%, os icones do lado direito vazavam pra fora do viewport
- A combinacao quebrava o comportamento sticky e empurrava icones pra fora

**Fix aplicado:**
1. `position:fixed` DIRETO no `::before` do logo
   - Pinado no viewport (`top:14px; left:22px`), independente do scroll/layout do header
   - `z-index:500` pra sobrepor qualquer coisa
   - Adicionei tambem `body::before` como fallback (redundante mas garante se `.mantine-AppShell-header` nao existir em alguma pagina)
2. Removido `position:relative !important` do header (respeita Mantine)
3. Substituido `padding-left:120px` no `> *` por `margin-left:110px` SO no `:first-child`
   - Nao vaza pra fora do viewport
   - Reserva espaco visual so pra area do logo
4. Cache bust atualizado pra `?v=3`

**Proximo passo:**
- User hard refresh (Cmd+Shift+R), valida scroll tanto em repouso quanto scrollado
- Icones do header devem ficar visiveis em ambos os estados
- Se OK, popular Tier 1 via MCP

---

## 2026-04-23, Sessao 6, Fix layout quebrado do logo no header

**Contexto:** Sessao 5 entregou logo Persua no header via `::before` em `.mantine-AppShell-header`. User reportou layout quebrado: logo aparecia numa linha propria ACIMA do top bar, ocupando espaco vertical extra.

**Causa raiz (descoberta):**
- `.mantine-AppShell-header` (class Mantine `m_3b16f56b`) e **apenas wrapper de altura fixa**, NAO e flex container
- Docmost coloca um `<div>` flex DENTRO do header
- `::before` com `display:block` vira bloco ACIMA desse filho (nao e flex item, porque o pai nao e flex)
- Resultado: logo empilha verticalmente em cima, empurrando o top bar pra baixo

**Fixes aplicados:**
1. **Refatorado CSS pra arquivo externo**: `brand/persua-custom.css`
   - Mais legivel, sem escape de aspas/quebras no Dockerfile
   - Dockerfile so faz `COPY` do arquivo e injeta `<link>` no index.html
   - Versionamento via `?v=N` no link pra bustar cache
2. **Logo com `position:absolute` no lugar de `display:block`**:
   - `position:relative` no `.mantine-AppShell-header` (pai)
   - `position:absolute; top:50%; left:16px; transform:translateY(-50%)` no `::before`
   - `z-index:2; pointer-events:none` pra nao bloquear cliques
   - Tira o pseudo-elemento do fluxo normal, nao disputa espaco com flex interno
3. **Padding-left 120px no primeiro filho do header** pra evitar sobreposicao com breadcrumb
4. **Media query 768px**: logo menor (72x22) + padding reduzido pra mobile

**Decisoes:**
- Preferiu arquivo CSS externo em vez de manter inline no Dockerfile (mais facil de editar)
- Mantida reversibilidade: pra desativar, remove o `<link>` injetado no Dockerfile
- Cache bust via `?v=2` no query string, incrementar ao editar CSS

**Proximo passo:**
- User faz hard refresh (Cmd+Shift+R) pra confirmar logo no lugar certo
- Se OK, popular Tier 1 via MCP (Acesso Web, Acesso App, Primeiro Atendimento)

---

## 2026-04-23, Sessao 5, Brand no header (logo + favicon) e ajustes finais

**Contexto:** Sessao 4 entregou esqueleto importado com voz Persua na home, mas usuario reportou que:
1. Titulos da sidebar continuavam sendo truncados (o CSS com seletor `.mantine-AppShell-navbar` nao pegava na share page publica)
2. Texto placeholder "PERSUA" ficou quebrado visualmente (pseudo-elemento `::before` com conteudo textual conflitou com header layout)

**Fixes aplicados nessa sessao:**
1. **CSS expandido com seletores agressivos** pra pegar sidebar da share page sem saber class exata:
   - Multiplos selectors: `.mantine-AppShell-navbar`, `aside.mantine-AppShell-aside`, `aside[class*="sidebar"]`, `nav[class*="sidebar"]`
   - Forcar text-wrap (`white-space:normal` + `word-break:break-word`) em `TreeNode`, `treeNode`, `page-tree` — quebra em 2 linhas em vez de truncar
2. **Logo Persua real no header** em vez do texto quebrado:
   - Copiado `Logo_fundo_transparente.png` pra `_tools/docmost/brand/persua-logo.png`
   - Copiado `icone_persua.png` pra `_tools/docmost/brand/persua-icon.png`
   - Dockerfile `COPY` coloca os PNGs em `/app/apps/client/dist/`
   - CSS usa `background-image:url("/persua-logo.png")` no pseudo-elemento do header
   - Favicon substituido via `sed` no index.html (favicon-32 e favicon-16 apontam pra /persua-icon.png)

**Decisoes:**
- Logo em PNG (14KB) em vez do SVG (140KB) do Logo.svg original, SVG era muito pesado pra carregar em header
- Icon usado tambem como favicon, mantem coerencia de marca
- CSS de text-wrap em sidebar mantido agressivo (multiplos seletores) pra cobrir possiveis renames de classes em updates futuros do Docmost

**Pendencias do usuario antes da proxima sessao:**
1. Hard refresh (Cmd+Shift+R) nas abas abertas do Docmost
2. Validar visualmente:
   - Logo aparece no header esquerdo?
   - Favicon da aba mudou pro icone Persua?
   - Sidebar tem 320px de largura?
   - Titulos quebram em 2 linhas ou ainda truncam?
3. Se algo quebrou, abrir F12, inspecionar o elemento, me passar a `class=` do elemento

**Proximo passo:**
- Aguardando validacao visual do user
- Se OK, popular Tier 1 via MCP: Acesso Web, Acesso App, Primeiro Atendimento (~3 chamadas MCP)
- Se algo nao funcionar, ajustar CSS com classes corretas

---

## 2026-04-23, Sessao 4, Refinamentos pos-import e voz Persua

**Contexto:** Master ZIP importado com sucesso. User validou estrutura visual. Consultei design-chief e brand-chief pra avaliacao final.

**Feedback dos chiefs:**
- Design Chief: aprovado pra soft launch. Top riscos: link callout nao clicavel, titulo da aba "Docmost" nao custom, placeholders no indice de busca, falta analytics
- Brand Chief: 85% poderia ser qualquer SaaS. Maior diferencial ausente = BRASILIDADE + CONVERSACIONAL. Intervencao de alto ROI: reescrever home

**Fixes aplicados nessa sessao:**
1. Dockerfile expandido com CSS custom reversivel (bloco `<style id="persua-custom">`):
   - Sidebar width ampliada pra 320px (nao trunca titulos longos)
   - Responsivo mobile (280px em <768px)
   - Link docmost.com residual escondido
2. Title da aba patched pra "Base de Conhecimento Persua"
3. Home reescrita com voz Persua brasileira:
   - Abertura humana ("Sua empresa merece atendimento que nao dorme")
   - Promessa concreta ("Em 10 minutos voce esta conectado")
   - Fechamento humano ("Persua e feita por gente que entende PME brasileira")
4. Acentuacao corrigida em todas descricoes das secoes do TREE (regra Persua)

**Decisoes:**
- User preferiu ampliar sidebar ao inves de encurtar titulos (respeita identidade das paginas)
- CSS custom mantido reversivel via `<style id="persua-custom">` no Dockerfile
- Voz Persua aplicada inicialmente so na home. Secoes mantem tom atual ate populacao

**Proximo passo:**
- User deleta raiz e reimporta master atualizado
- Se aprovado visual, comeca populacao do Tier 1 (Comece Aqui: Acesso Web, Acesso App, Primeiro atendimento)

---

## 2026-04-23, Sessao 3, Arvore completa e esqueleto master

**O que foi feito:**
- Descoberto que Docmost aceita estrutura hierarquica via ZIP (pasta com nome igual ao .md vira "filhos")
- Descoberto que Docmost aceita `docmost-metadata.json` no root do ZIP para mapear icones de pagina
- Descoberta a sintaxe de callouts: `:::info/success/warning/danger ... :::`
- Refinada Conexao WhatsApp Cloud API com callouts nativos, link da Meta e 16 imagens
- Consulta aos chiefs (design-chief + brand-chief) para escolher icones da sidebar
- Script idempotente `scripts/build_master_zip.py` que gera o ZIP master completo
- ZIP master entregue com 48 paginas (1 populada + 47 placeholders), 16 imagens, icones em todas

**Decisoes de arquitetura:**
- Cache de 3 camadas: `cache/flw-raw/` (bruto MCP, nunca editar), `drafts/` (processado), `import-packages/` (entregavel)
- User importa 1x o master. Depois populacao vem por copy-paste em paginas existentes (evita duplicacao)
- Cada tutorial populado gera um `.md` em drafts, user cola dentro da pagina existente no Docmost

**Proximo passo:**
- User importa master ZIP
- Confirmacao visual da arvore
- Popular Tier 1 (Comece Aqui: 3 paginas + indice) em batch via MCP

---

## 2026-04-23, Sessao 2, Ativacao do MCP e workflow definido

**O que foi feito:**
- Confirmado que Persua usa white-label Helena (mesma base que flw.chat)
- MCP `documentacao-ref` instalado e carregado (tools `getPage` e `searchDocumentation`)
- Criada estrutura de session management: CLAUDE.md, tasks.md, sessions.md, memory.md em `_tools/docmost/`
- Definido workflow: MCP fetch, adaptar pra Persua, salvar em drafts/, colar no Docmost

**Decisoes:**
- Nao distribuir estrutura identica aos concorrentes, adaptar tom e imagens pra Persua
- Screenshots/GIFs sempre com branding Persua, nunca reutilizar do flw

**Proximo passo:**
- Rodar tutorial piloto "Conexao WhatsApp Cloud API" via MCP
- Se ficar bom, executar em lote todos os Tier 1 e 2

---

## 2026-04-22, Sessao 1, Setup inicial

**O que foi feito:**
- Avaliadas plataformas: Mintlify, GitBook, HelpScout (caras), Starlight/Nextra/Docusaurus (code-first, descartado), Outline (bloqueio OAuth), Docmost (escolhido)
- Subido Docmost via Docker Compose em `_tools/docmost/`
- Patches aplicados no Dockerfile: fallbackLng pra pt-BR, remocao "Powered by Docmost", lang="pt-BR" no html, CSS injection pra esconder link residual
- Criado rascunho "Criar modelo de mensagem para campanha" em `drafts/`
- CEO recusou destravar features EE (legal/ethical)

**Gotchas aprendidos:**
- `sed` com `\`` backticks precisa escape correto no Dockerfile
- Empty `children:\`\`` deixa o elemento com padding visivel, precisou CSS injection
- Hash do bundle muda a cada versao do Docmost, usar glob `index-*.js`
- Janela anonima nao envia pt-BR Accept-Language corretamente

**Proximo passo:** (movido pra sessao 2) ativar MCP e comecar adaptacao de conteudo.

---
