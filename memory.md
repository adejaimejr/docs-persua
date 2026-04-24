# Memory, Decisoes Duraveis e Gotchas

Coisas que DEVEM ser lembradas em qualquer sessao futura.

## Decisoes estrategicas

### Plataforma escolhida: Docmost community
- Motivo: open-source, editor WYSIWYG, self-host, custo zero de licenca
- Alternativas descartadas e por que: Mintlify/GitBook/HelpScout (caros), Starlight/Nextra (code-first demais), Outline (OAuth obrigatorio), Notion+Super.so (CEO preferiu open-source)
- **Nunca** voltar atras nessa decisao sem novo debate. Fallback documentado: GitBook free tier se Docmost quebrar catastroficamente.

### Features EE: nao destravar
- API Keys, SSO, Audit log, IA chat, verificacao de paginas: licenca comercial
- CEO pediu, foi declinado com base em license compliance
- Se precisar API no futuro: pagar Docmost Cloud (~US$ 5/user/mes) ou migrar pra BookStack/Outline

### Adaptacao de conteudo flw.chat, Persua
- Plataforma base (Helena) e a mesma, entao conteudo e tecnicamente equivalente
- **Obrigatorio** mudar:
  - Tom/linguagem (Persua tem identidade propria)
  - Imagens e GIFs (sempre com branding Persua)
  - Referencias a "FLW" ou nome do concorrente (nome da marca do competidor)
  - Links externos que apontam pro flw.chat
- **Permitido** reaproveitar:
  - Sequencia logica de passos (e o mesmo produto)
  - Termos tecnicos (Ajustes, Modelos, Campanhas, etc)
  - Pre-requisitos
- **Preservar** (NAO trocar):
  - "Hunion", aparece na tela real do OAuth Meta, e o nome da integracao oficial homologada da plataforma Helena com a Meta. Trocar causa divergencia entre o tutorial e o que o cliente ve na tela
- **Estrutura**:
  - Seguir sequencia de passos do original (pra encaixar com os prints ja capturados pelo cliente da plataforma Persua)
  - Limpar apenas numeracao (original tem gaps tipo Passo 3 pra Passo 6)
  - Limpar tom e adicionar blocos Persua (pre-requisitos, dicas, proximos passos)

## Gotchas tecnicos

### Dockerfile
- `sed` com backticks precisa do escape correto, nao usar aspas duplas que conflitam
- Hash do bundle muda por versao, usar `find ... -name "index-*.js"`
- `-exec ... \;` encadeado funciona, mas `&&` entre comandos precisa nova camada `RUN`

### Docmost UI
- Compartilhamento de pagina individual NAO mostra sidebar
- Para sidebar hierarquica: criar pagina-pai com subpaginas, compartilhar a pai com "Incluir subpaginas" ativo
- Nao tem abas top-level (tipo "Home/Guias" do GitBook), apenas paginas-raiz na sidebar

### Idioma
- fallbackLng hardcoded no bundle (patchado via Dockerfile)
- lang="en" no index.html hardcoded (patchado)
- Cada build novo do Docmost, o patch precisa rodar de novo (o Dockerfile cuida disso automaticamente)

### Share URLs
- Formato: `/share/:shareId/p/:pageSlug`
- includeChildren=true mostra subpaginas na sidebar do share publico

## Deploy em producao (Dokploy)

### Dominio e infra
- `docs.persua.com.br` - padrao help center (docs.stripe.com, docs.github.com)
- Dokploy self-hosted, Traefik ja incluso
- SSL via Let's Encrypt automatico (Traefik descobre por labels)

### Arquitetura do deploy
```
DNS docs.persua.com.br -> VPS Dokploy -> Traefik -> container docmost (porta 3000 interna)
                                                      |
                                                      +-- container db (postgres, rede interna)
                                                      +-- container redis (rede interna)
```

### Arquivos criticos
- `docker-compose.prod.yml` - sem ports expostos, env vars, labels Traefik, rede externa `dokploy-network`
- `.env.prod.example` - template de APP_URL, APP_SECRET, POSTGRES_PASSWORD (NAO commitar real)
- `deploy/README.md` - runbook 11 passos do zero ao share publico
- `Dockerfile` - reusado integral (patches de marca funcionam igual em prod)

### APP_URL e URLs de share
- `APP_URL=https://docs.persua.com.br` (env var, nao mais hardcoded)
- Docmost usa isso pra gerar links de share: `https://docs.persua.com.br/share/<shareId>/p/<slug>`
- Trocar `APP_URL` em deploy existente nao quebra URLs de share ja emitidas (sao relativos ao host)

### Redirect raiz -> share (padrao help center)
- Por default `docs.persua.com.br/` abre tela de login
- Pra funcionar como help center publico: redirect root -> URL do share da raiz
- Opcao A (recomendada): patch no Dockerfile com `sed` no index.html injetando `<script>location.replace("/share/<id>/p/base-de-conhecimento")</script>`
- Opcao B (mais limpa): Traefik middleware `redirectregex` no compose
- Requer deploy em 2 fases: primeiro sobe Docmost, cria share, anota shareId, adiciona patch com o ID real, redeploy

### Gotchas criticos do deploy
1. **APP_SECRET novo** em prod (openssl rand -hex 32), senao invalida sessoes
2. **Rede `dokploy-network`** precisa estar como `external: true` no compose
3. **`build: .`** no compose, senao Dokploy tenta so pull da imagem base (sem patches)
4. **POSTGRES_PASSWORD** so funciona se TANTO a db QUANTO o DATABASE_URL referenciam a mesma env var
5. **FILE_IMPORT_SIZE_LIMIT** default 200MB - OK pro ZIP de 60MB
6. **Migrations** rodam no first boot, esperar ~60s
7. **Share publico** precisa ativar "Link publico" + "Incluir subpaginas"

---

## Conversao flw.chat -> Persua drafts (scripts/convert_flw_to_persua.py)

### Transformacoes sintaticas
- `{% hint style="success/info/warning/danger" %}...{% endhint %}` -> `:::tipo\n...\n:::` (callout nativo Docmost)
- `{% content-ref url="..." %}[label](url){% endcontent-ref %}` -> removido (navegacao interna flw que nao traduz)
- `{% embed url="..." %}` -> removido (videos drive/youtube)
- `<figure><img src="..." ...></figure>` -> `![alt](path-local)` (markdown puro)

### Trocas de marca
- "a plataforma" -> "a Persua", "na plataforma" -> "na Persua", etc
- "**plataforma**" -> "**Persua**"
- **Preservar** "Hunion" (nome da integracao oficial Helena-Meta, NAO trocar — aparece na tela real do OAuth)
- Preservar links docs.whatsapp.com e developers.facebook.com (referencias oficiais)

### Gotcha critico: URLs GitBook com parens escapados
- URLs no markdown flw aparecem como `![](https://...%20\(1\)%20\(1\)%20\(1\).png?alt=media)`
- O `\(` e `\)` sao escapes markdown de parens literais no filename
- Regex simples nao captura: precisa aceitar `\(` e `\)` como parte do URL
- Antes de baixar: re-encode `(` -> `%28`, `)` -> `%29` via `urllib.parse.quote(path, safe="/%")` (senao HTTP 400)
- Apos baixar: usa `text.replace(url_original_escapado, path_local)` pra reescrever

### Script de conversao: comando util
```bash
# Processa tudo (cache -> drafts + imagens)
python3 scripts/convert_flw_to_persua.py

# Testa um slug especifico
python3 scripts/convert_flw_to_persua.py --only=acessando-pela-web

# Skip download de imagens (so processa texto)
python3 scripts/convert_flw_to_persua.py --skip-images
```

### Piloto preservado
- `conexao-whatsapp-cloud-api.md` NAO e sobrescrito pelo convert_flw_to_persua.py
- Tem `PILOTO = {"conexao-whatsapp-cloud-api"}` como guard
- Piloto usa marcadores `[PRINT XX → arraste: ...]` (sintaxe drag-drop antiga)
- `build_master_zip.py` tem `convert_drag_drop_to_markdown_images()` pra converter no build

---

## Overlay _persua/ (de-para de imagens)

### Conceito
Cada pasta `drafts/assets/<slug>/` pode ter um subfolder `_persua/` com
screenshots Persua que substituem as flw no ZIP final.

### Estrutura
```
drafts/assets/<slug>/
├── print-01.png          <- flw cache (MCP)
├── print-02.png          <- flw cache
├── _persua/
│   ├── README.md         <- doc da convencao (auto-gerado)
│   ├── print-01.png      <- Persua (user drop)
│   └── print-02.png      <- Persua (user drop)
```

### Regra de build
Pra cada `<slug>/print-XX.png`:
- Se existe `_persua/print-XX.png` → usa a Persua no ZIP
- Senao → usa a flw e lista como "pendente de captura" no relatorio

### Por que funciona
- MCP re-pull sobrescreve `drafts/assets/<slug>/print-XX.png` mas NAO toca `_persua/`
- Markdown nao muda: `![](assets/<slug>/print-XX.png)` sempre resolve pro arquivo certo
- Zero config: drop o arquivo com mesmo nome em `_persua/` e funciona

### Reportagem
Ao rodar `build_master_zip.py`, output inclui secao "Overlay _persua/":
- Total Persua vs total flw pendentes
- Por tutorial: status OK (todas Persua) ou pendente
- Lista dos primeiros 10 pendentes

### Nao usar pra
- Imagens que mudam de NOME (overlay assume mesmo filename)
- Adicionar imagens novas que nao existem na flw (script so copia `*.png` direto do slug_dir, nao descobre novos em `_persua/`)

---

## Workflow de imagens

### Baixar prints da doc de referencia
- MCP `documentacao-ref` retorna markdown com URLs publicas de imagens no CDN `3968359699-files.gitbook.io`
- Baixar com curl pra `drafts/assets/<slug-da-pagina>/print-XX.png`
- Numeracao bate com o PRINT marker do .md (print-01.png = PRINT 01)
- Algumas URLs podem dar 502 transiente, fazer retry
- URLs com parens precisam URL-encode: `(` = `%28`, `)` = `%29`

### Marcar status de cada print
- Na pasta assets/ criar README.md com tabela "arquivo / usa como / acao"
- Classificar: "Pode usar" (tela generica Meta), "Recapturar na Persua" (tem branding flw visivel)
- Prints faltantes no original: marcar como `[PRINT XX → CAPTURAR NA PERSUA: descricao]`

## Gotchas do ZIP import

### Emoji duplicado na sidebar
- Se o H1 do .md tem emoji E o metadata.json tem icon, o sidebar mostra **emoji duplicado**
- **Solucao**: deixar emoji APENAS no metadata.json, H1 sem emoji
- Aplicado em `build_master_zip.py` (funcoes `placeholder_content`, `section_parent_content`, `root_content`)

### Drag-drop markers vs markdown images
- Drafts em `drafts/` usam marcadores texto `[PRINT XX → arraste: path]` (pra drag-drop no editor)
- ZIP import precisa de markdown image syntax `![](path)` (pra virar attachment automatico)
- **Solucao**: script `build_master_zip.py` tem funcao `convert_drag_drop_to_markdown_images` que transforma automaticamente ao montar o ZIP
- Marcadores "CAPTURAR NA PERSUA" viram callouts `:::info` com aviso de captura pendente

### Reimportar no Docmost
- Import SEMPRE cria paginas novas, nunca atualiza existentes
- Pra reimportar: deletar a raiz inteira (cascade apaga tudo) E importar de novo
- Pra preservar edicoes manuais: nao reimportar, copiar conteudo do draft e colar em pagina existente

### Ordenacao de paginas no sidebar
- `docmost-metadata.json` suporta `position` (alem de `icon`)
- Formato: `{"encoded-path.md": {"icon": "👋", "position": "a"}}`
- Position e string lexicografica (a, b, c, ...). Sem position, ordena alfabetico
- Importante forcar ordem, senao "Comece Aqui" vai pra meio da lista alfabetica

### Links internos entre paginas
- Docmost usa slugs gerados dinamicamente no import
- Nao da pra fazer link direto entre paginas no markdown do ZIP (slug so existe apos import)
- Solucao: cards com H3 sem link, user clica pela sidebar
- Se quiser linkar: editar manualmente apos import com slug real

## Workflow ZIP import (preferido)

**Docmost community aceita import de ZIP** via Settings > Import > Markdown. Isso automatiza upload de imagens.

### Estrutura esperada do ZIP
```
<page-slug>.zip/
├── <page-slug>.md              (usa ![alt](assets/.../print-XX.png))
└── assets/
    └── <page-slug>/
        └── print-XX.png
```

### Como o Docmost resolve paths
- Codigo fonte: `import.utils.js` funcao `resolveRelativeAttachmentPath`
- Tenta: path relativo ao root do ZIP, ou relativo ao diretorio do .md
- Se encontrar, cria attachment e atualiza link

### Gerar ZIP
- Criar estrutura em `/tmp/docmost-import/`
- `cd /tmp/docmost-import && zip -r <destino>/<slug>.zip <slug>.md assets/`
- Salvar em `_tools/docmost/import-packages/<slug>.zip`

### Marcadores no .md do ZIP
- Para prints baixados: `![alt](assets/<slug>/print-XX.png)` (sintaxe markdown)
- Para prints faltantes (user captura): blockquote `> 📸 Capturar: descricao (PRINT XX)`

### Fluxo de edicao do cliente (com ZIP)
1. No Docmost: Settings > Import > seleciona o ZIP
2. Pagina criada automaticamente com imagens no lugar
3. User edita inline pra substituir placeholders flw por Persua
4. Capturar os PRINT faltantes (sinalizados com 📸 Capturar) e colar no lugar

### Fluxo drag-drop (fallback)
1. Usar o .md em `drafts/` que tem marcadores `[PRINT XX → arraste: path]`
2. Abrir pasta assets no Finder (`open <path>`)
3. Pra cada marcador: arrastar arquivo pro editor

## Sintaxe de callouts no Docmost

Docmost tem 4 tipos de callout nativos: **info** (azul), **success** (verde), **warning** (amarelo), **danger** (vermelho).

### Sintaxe markdown

```
:::success
**Titulo**

conteudo markdown, listas, bold, tudo funciona
:::
```

Fonte: `/app/packages/editor-ext/dist/lib/markdown/utils/callout.marked.js`

### Convencao da Persua

- `:::success` para Pre-requisitos, confirmacao, finalizacao
- `:::warning` para Atencao, limitacoes, cuidados
- `:::info` para Proximos passos, contexto adicional, links uteis
- `:::danger` para Erros criticos, nao recuperaveis

Nao usar `>` blockquote com emoji para simular callout. Usar a sintaxe `:::` sempre.

## Referencias externas

### Links da documentacao Meta (preservar)
- Manter link oficial da Meta no final de tutoriais tecnicos (ex: Embedded Signup, Business Suite)
- Formato: "Para referencia tecnica completa, consulte a [documentacao oficial da Meta](URL)"
- NAO adaptar ou esconder, e informacao complementar legitima

## Customizacoes visuais Persua (CSS + assets)

### Logo e favicon (Dockerfile + CSS externo)
- Brand assets em `_tools/docmost/brand/`:
  - `persua-logo.png` (14KB, do `Logo_fundo_transparente.png`) para o header LIGHT
  - `persua-logo-dark.png` (23KB, do `Logo_fundo_transparente_escuro.png`) para o header DARK
  - `persua-icon.png` (16KB, do `icone_persua.png`) para o favicon
  - `persua-custom.css` (arquivo CSS editavel, sem escape no Dockerfile)
- SVG nao usado (Logo.svg 140KB + escuro 332KB, pesados demais pra header)
- Dockerfile usa `COPY` pra colocar assets em `/app/apps/client/dist/`
- index.html patched via `sed` pra:
  - Favicon: substituir paths dos `<link rel="icon">`
  - CSS: injetar `<link rel="stylesheet" href="/persua-custom.css?v=N" />`
- **Nao usar SVG original** (Logo.svg = 140KB, pesado demais pra header)
- Se precisar versao dark, tem `Logo_com_fundo_escuro.svg` em persua/_assets/brand/

### Gotcha critico: classes do Docmost NAO sao TreeNode/treeNode
- CSS selectors errados: `[class*="TreeNode"]`, `[class*="treeNode"]`, `[class*="page-tree"]`
- Classes reais do Docmost (scoped CSS modules, prefixo `_` minusculo + hash):
  - `_row_tofwf_69` = wrapper da linha no react-arborist
  - `_node_tofwf_14` = link flex interno (icone + texto)
  - `_treeNode_1500s_10` = container externo
- Seletor correto: `[class*="_row_tofwf"]`, `[class*="_node_tofwf"]`, `[class*="_treeNode_"]`
- Descobrir novas classes: `docker exec persua-docmost sh -c 'cat /app/apps/client/dist/assets/index-*.css' | tr '}' '\n' | grep -iE 'treenode|_row|_node' | head`

### Gotcha critico: react-arborist tem rowHeight fixo no JS bundle
- Docmost configura react-arborist com `rowHeight:30` (fixo em px)
- CSS `min-height` sozinho NAO RESOLVE: react-arborist renderiza rows com inline style `height: 30px` E posiciona cada row absolutamente em `top: index * rowHeight`
- Aumentar CSS so causa overflow vertical da row (mesma sobreposicao)
- **Solucao**: patch sed no bundle JS: `sed -i 's/rowHeight:30/rowHeight:48/g'`
- 48px cabe 2 linhas de texto com line-height 1.25 confortavel
- Aplicado no Dockerfile no mesmo RUN dos patches obrigatorios (fallbackLng, Powered by)

### Logo dark mode
- Docmost aplica `[data-mantine-color-scheme="dark"]` no `<html>` quando usuario clica no toggle
- Arquivo dark: copiado de `persua/_assets/brand/Logo_fundo_transparente_escuro.png` (23KB)
- CSS: `[data-mantine-color-scheme="dark"] .mantine-AppShell-header::before { background-image: url("/persua-logo-dark.png") !important; }`
- Tambem coberto `[data-mantine-color-scheme="auto"]` com `@media (prefers-color-scheme: dark)` pra fallback

### Gotcha critico: logo no header precisa position:FIXED (nao absolute, nao block)
- `.mantine-AppShell-header` (class Mantine `m_3b16f56b`) e **apenas wrapper de altura fixa**, NAO e flex container
- Docmost coloca um `<div>` flex DENTRO do header, nao e o header que e flex
- Tentativas anteriores e por que falharam:
  1. `::before` com `display:block`: vira bloco ACIMA do filho flex, empurra conteudo pra baixo, **quebra layout** (logo aparece em linha propria acima do top bar)
  2. `::before` com `position:absolute` + `position:relative !important` no header: sobrescreve o `position:fixed` default do Mantine, **header para de grudar no topo** e scrolla com conteudo. Logo fica descolado do header na hora do scroll
  3. `padding-left:120px` no primeiro filho do header: empurra o flex interno pra direita, mas como flex tem width:100%, **os icones do canto direito vazam pra fora do viewport**
- **Solucao que funciona**: `position:fixed` DIRETO no `::before` + `margin-left:110px` so no `:first-child` do header
  - Logo fica pinado no viewport, independente do scroll/layout do header
  - `margin-left` so no primeiro filho reserva espaco visual pro logo, sem vazar
  - `z-index:500` garante que o logo sobrepoe qualquer coisa
- Aplicado em `brand/persua-custom.css` secao 4

### CSS para sidebar da share page
- A share page publica NAO usa apenas `.mantine-AppShell-navbar`
- Precisa seletores multiplos: `aside.mantine-AppShell-aside`, `aside[class*="sidebar"]`, `nav[class*="sidebar"]`
- Text-wrap via `white-space:normal + word-break:break-word` funciona mesmo sem saber a class exata
- Aplicado em elementos que contem texto da navegacao: `[class*="TreeNode"]`, `[class*="treeNode"]`, `[class*="page-tree"]`

### Title e brand no HTML
- `<title>` patched pra "Base de Conhecimento Persua"
- `<html lang="pt-BR">`
- Favicon Persua substituindo o Docmost default

### Logo dark/light switcher
- Docmost aplica `[data-mantine-color-scheme="dark"]` no `<html>` quando user troca pra dark
- CSS troca `background-image` do logo via `[data-mantine-color-scheme="dark"] body::before`
- Fallback via `@media (prefers-color-scheme: dark)` pra modo "auto"

### Spacing do sidebar (tree de paginas)
- Problema: com sidebar de 320px + titulos longos quebrando em 2 linhas, segunda linha encostava no icone do item seguinte
- Causa: `line-height:1.35` arruma a linha interna mas nao cria respiro entre items
- Fix (Design Chief): `min-height:32px + padding-block:5px + margin-block:1px + align-items:flex-start` nos items da tree (TreeNode, page-tree > div|a|button)
- `align-self:flex-start` nos filhos pra alinhar icone no TOPO com primeira linha do texto (nao centralizado com texto de 2 linhas)

### Consulta aos chiefs (decisao durable)
- Design Chief: spacing atual segue padrao Notion/Linear/Mintlify (32px min-height, 4-6px padding-block)
- Brand Chief: emojis como icones OK pra Persua (conversacional, brasileiro, PME friendly). SVG custom seria corporate demais. Hierarquia atual representa bem a marca.

### Reversibilidade
- Todo CSS custom esta em bloco `<style id="persua-custom">` no index.html
- Pra reverter: remover o `RUN sed` que injeta o style, rebuild
- Os patches obrigatorios (PT-BR, sem Powered by, title) ficam em bloco separado e permanecem

## Regras de conteudo (Persua)
- Acentuacao obrigatoria em texto visivel
- Linguagem de beneficio, sem jargao tecnico excessivo
- NUNCA usar em dash (—), trocar por virgula ou ponto
- Antes de finalizar tutorial: passar pelo `/humanizer`
- Pre-requisitos sempre em blockquote com icone
- Passos numerados com H2 headers
- Placeholders de imagem: `[PRINT: descricao]` ou `[GIF: descricao]`
