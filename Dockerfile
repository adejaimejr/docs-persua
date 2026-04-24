FROM docmost/docmost:latest

# ----------------------------------------------------------------------------
# Patches obrigatorios (nao remover sem avaliar)
# ----------------------------------------------------------------------------
#  - fallbackLng: forca traducao PT-BR como padrao no i18next
#  - Powered by Docmost: remove string de branding (AGPL permite modificar UI)
#  - lang="pt-BR": ajusta atributo HTML root pra acessibilidade e SEO
RUN find /app/apps/client/dist/assets -name "index-*.js" -type f \
    -exec sed -i 's/fallbackLng:`en-US`/fallbackLng:`pt-BR`/g' {} \; \
    -exec sed -i 's/`Powered by Docmost`/``/g' {} \; \
    -exec sed -i 's/rowHeight:30/rowHeight:48/g' {} \; \
 && sed -i 's|<html lang="en">|<html lang="pt-BR">|' /app/apps/client/dist/index.html

# ----------------------------------------------------------------------------
# Title custom da aba do browser
# ----------------------------------------------------------------------------
RUN sed -i 's|<title>Docmost</title>|<title>Base de Conhecimento Persua</title>|' /app/apps/client/dist/index.html

# ----------------------------------------------------------------------------
# Brand assets Persua (logo no header + favicon + CSS custom)
# ----------------------------------------------------------------------------
COPY brand/persua-logo.png /app/apps/client/dist/persua-logo.png
COPY brand/persua-logo-dark.png /app/apps/client/dist/persua-logo-dark.png
COPY brand/persua-icon.png /app/apps/client/dist/persua-icon.png
COPY brand/persua-custom.css /app/apps/client/dist/persua-custom.css

# Substitui favicon padrao pela icone Persua
RUN sed -i 's|href="/icons/favicon-32x32.png"|href="/persua-icon.png"|g' /app/apps/client/dist/index.html \
 && sed -i 's|href="/icons/favicon-16x16.png"|href="/persua-icon.png"|g' /app/apps/client/dist/index.html

# Injeta o CSS custom como <link> no <head>. Fica facil editar o arquivo
# brand/persua-custom.css sem escape de aspas/quebras de linha no Dockerfile.
# Para reverter: remover esta linha e rebuild.
RUN sed -i 's|</head>|<link rel="stylesheet" href="/persua-custom.css?v=8" /></head>|' /app/apps/client/dist/index.html

# ----------------------------------------------------------------------------
# Redirect raiz / -> share publico da Base de Conhecimento
# ----------------------------------------------------------------------------
# docs.persua.com.br/ -> docs.persua.com.br/share/<id>/p/base-de-conhecimento-<sufixo>
# Sem isso, a raiz cai na tela de login do Docmost. Como queremos help center
# publico, redirecionamos antes de carregar o bundle React.
#
# IMPORTANTE: o SHARE_ID muda toda vez que a raiz e deletada e reimportada
# via Settings > Import. Pra manter o redirect funcionando, voce tem 2 opcoes:
#   1. Editar paginas via UI direto (mantem shareId, simples)
#   2. Deletar/reimportar e atualizar o SHARE_ID + sufixo aqui no Dockerfile
RUN sed -i 's|</head>|<script>if(location.pathname==="/"\&\&!location.search)location.replace("/share/o8yw2uvuas/p/base-de-conhecimento-zKTcPfquod");</script></head>|' /app/apps/client/dist/index.html
