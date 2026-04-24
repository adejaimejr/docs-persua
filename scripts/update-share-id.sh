#!/usr/bin/env bash
# ============================================================================
# update-share-id.sh
# ============================================================================
# Atualiza o SHARE_ID no Dockerfile depois de reimportar a Base de Conhecimento.
#
# Toda vez que voce deleta a raiz "Base de Conhecimento" e reimporta o ZIP
# master, o Docmost gera um novo shareId quando voce recompartilha. O redirect
# raiz `docs.persua.com.br/` -> share precisa apontar pra esse novo ID.
#
# Em vez de editar o Dockerfile na mao, roda esse script com o novo URL
# completo do share publico que o Docmost te dá.
#
# Uso:
#   ./scripts/update-share-id.sh <URL_COMPLETA_DO_SHARE>
#
# Exemplo:
#   ./scripts/update-share-id.sh https://docs.persua.com.br/share/o8yw2uvuas/p/base-de-conhecimento-zKTcPfquod
#
# Depois:
#   git add Dockerfile
#   git commit -m "update: novo shareId apos reimport"
#   git push
#
# Dokploy faz autodeploy. Em ~1-2 min, docs.persua.com.br/ redireciona pro
# novo share.
# ============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Uso: $0 <URL_COMPLETA_DO_SHARE>"
  echo ""
  echo "Exemplo:"
  echo "  $0 https://docs.persua.com.br/share/o8yw2uvuas/p/base-de-conhecimento-zKTcPfquod"
  exit 1
fi

URL="$1"

# Extrai shareId e slug suffix
if [[ ! "$URL" =~ /share/([a-zA-Z0-9]+)/p/base-de-conhecimento-([A-Za-z0-9]+) ]]; then
  echo "Erro: URL invalida. Esperado formato:"
  echo "  https://docs.persua.com.br/share/<SHARE_ID>/p/base-de-conhecimento-<SUFIXO>"
  exit 1
fi

SHARE_ID="${BASH_REMATCH[1]}"
SLUG_SUFFIX="${BASH_REMATCH[2]}"

DOCKERFILE="$(dirname "$0")/../Dockerfile"

if [ ! -f "$DOCKERFILE" ]; then
  echo "Erro: Dockerfile nao encontrado em $DOCKERFILE"
  exit 1
fi

echo "Atualizando Dockerfile..."
echo "  Novo SHARE_ID:    $SHARE_ID"
echo "  Novo SLUG_SUFFIX: $SLUG_SUFFIX"
echo ""

# Cross-platform sed (BSD/macOS vs GNU/Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' -E "s|location\.replace\(\"/share/[a-zA-Z0-9]+/p/base-de-conhecimento-[A-Za-z0-9]+\"\)|location.replace(\"/share/${SHARE_ID}/p/base-de-conhecimento-${SLUG_SUFFIX}\")|" "$DOCKERFILE"
else
  sed -i -E "s|location\.replace\(\"/share/[a-zA-Z0-9]+/p/base-de-conhecimento-[A-Za-z0-9]+\"\)|location.replace(\"/share/${SHARE_ID}/p/base-de-conhecimento-${SLUG_SUFFIX}\")|" "$DOCKERFILE"
fi

echo "Linha atualizada no Dockerfile:"
grep -E "location.replace" "$DOCKERFILE" | sed 's/^/  /'
echo ""

echo "Proximos passos pra publicar o novo redirect:"
echo "  git add Dockerfile"
echo "  git commit -m 'update: novo shareId apos reimport'"
echo "  git push"
echo ""
echo "Dokploy faz autodeploy. Em ~1-2 min, https://docs.persua.com.br/ apontara pro novo share."
