-- ============================================================================
-- dump-state.sql, exporta estado dos URLs do Docmost
-- ============================================================================
-- Roda no Postgres do docs.persua.com.br pra extrair em JSON:
--   - Hierarquia de paginas com slug_id (sufixo do URL /p/<title>-<slug_id>)
--   - Shares ativos com key (parte /share/<key>/) ligados a cada pagina
--
-- Quando rodar:
--   1. ANTES do primeiro reimport (gera baseline canonico, versionado em snapshot/)
--   2. APOS cada reimport (gera estado atual, usado pra montar UPDATEs de restore)
--
-- Como rodar no Dokploy:
--   docker exec -i $(docker ps -q -f name=postgres_postgres) \
--     psql -U docmost -d docmost -t -A -f - < dump-state.sql > state.json
--
-- Ou cole o conteudo direto no terminal psql do Dokploy e copie a saida.
-- ============================================================================

WITH RECURSIVE page_paths AS (
  SELECT
    id,
    title,
    slug_id,
    parent_page_id,
    position,
    title AS path,
    1 AS depth
  FROM pages
  WHERE parent_page_id IS NULL AND deleted_at IS NULL

  UNION ALL

  SELECT
    p.id,
    p.title,
    p.slug_id,
    p.parent_page_id,
    p.position,
    pp.path || ' / ' || p.title AS path,
    pp.depth + 1
  FROM pages p
  INNER JOIN page_paths pp ON p.parent_page_id = pp.id
  WHERE p.deleted_at IS NULL
)
SELECT json_build_object(
  'generated_at', now(),
  'page_count', (SELECT count(*) FROM page_paths),
  'pages', (
    SELECT json_agg(json_build_object(
      'id', id,
      'path', path,
      'slug_id', slug_id,
      'title', title,
      'depth', depth,
      'position', position
    ) ORDER BY path)
    FROM page_paths
  ),
  'shares', (
    SELECT COALESCE(json_agg(json_build_object(
      'key', s.key,
      'page_path', pp.path,
      'include_sub_pages', s.include_sub_pages,
      'search_indexing', s.search_indexing
    )), '[]'::json)
    FROM shares s
    INNER JOIN page_paths pp ON s.page_id = pp.id
    WHERE s.deleted_at IS NULL
  )
) AS state;
