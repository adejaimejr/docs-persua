#!/usr/bin/env python3
"""
Gera SQL de restore de URLs apos delete+reimport no Docmost.

Compara o BASELINE (estado canonico, versionado em snapshot/urls-baseline.json)
com o estado ATUAL pos-reimport (gerado por dump-state.sql) e produz UPDATEs
que reescrevem:
  - pages.slug_id (sufixo de cada deep-link /p/<title>-<slug_id>)
  - shares.key (id que vai em /share/<key>/)

Match e feito por `path` hierarquico (Base de Conhecimento / Secao / Pagina),
que e estavel entre reimports desde que titulos + estrutura nao mudem.

Uso:
  # 1. Apos reimport+recompartilhamento, rodar dump-state.sql em prod e
  #    salvar a saida em snapshot/state-current.json
  # 2. Gerar o SQL de restore:
  python3 scripts/build-restore-sql.py \\
      --baseline snapshot/urls-baseline.json \\
      --current snapshot/state-current.json \\
      --output snapshot/restore.sql
  # 3. Rodar snapshot/restore.sql no Postgres prod (terminal Dokploy)

Saida: arquivo SQL com BEGIN/COMMIT, comentarios e summary de mudancas.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_state(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8").strip()
    # Aceita tanto JSON puro quanto saida do psql -t -A (1 linha JSON)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERRO: {path} nao parece JSON valido: {e}", file=sys.stderr)
        sys.exit(1)


def index_pages(state: dict) -> dict[str, dict]:
    """Indexa por path -> page record."""
    return {p["path"]: p for p in state.get("pages", [])}


def index_shares(state: dict) -> dict[str, dict]:
    """Indexa por page_path -> share record."""
    return {s["page_path"]: s for s in state.get("shares", [])}


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera SQL de restore de URLs")
    parser.add_argument("--baseline", required=True, type=Path, help="JSON canonico (snapshot/urls-baseline.json)")
    parser.add_argument("--current", required=True, type=Path, help="JSON pos-reimport (gerado por dump-state.sql)")
    parser.add_argument("--output", required=True, type=Path, help="Arquivo SQL de saida")
    args = parser.parse_args()

    baseline = load_state(args.baseline)
    current = load_state(args.current)

    base_pages = index_pages(baseline)
    curr_pages = index_pages(current)
    base_shares = index_shares(baseline)
    curr_shares = index_shares(current)

    sql_lines: list[str] = []
    sql_lines.append("-- =================================================================")
    sql_lines.append("-- restore.sql, gerado por scripts/build-restore-sql.py")
    sql_lines.append("-- =================================================================")
    sql_lines.append(f"-- Baseline: {args.baseline}")
    sql_lines.append(f"-- Current:  {args.current}")
    sql_lines.append(f"-- Baseline pages: {len(base_pages)} | Current pages: {len(curr_pages)}")
    sql_lines.append(f"-- Baseline shares: {len(base_shares)} | Current shares: {len(curr_shares)}")
    sql_lines.append("--")
    sql_lines.append("-- Rodar em transacao unica. Se algo der erro, ROLLBACK preserva o estado.")
    sql_lines.append("-- =================================================================")
    sql_lines.append("")
    sql_lines.append("BEGIN;")
    sql_lines.append("")

    # ---- Pages ----
    matched = 0
    skipped_unchanged = 0
    missing = []
    new = []

    sql_lines.append("-- ---- pages.slug_id ----")
    for path, base in sorted(base_pages.items()):
        curr = curr_pages.get(path)
        if not curr:
            missing.append(path)
            continue
        if curr["slug_id"] == base["slug_id"]:
            skipped_unchanged += 1
            continue
        sql_lines.append(
            f"UPDATE pages SET slug_id = '{base['slug_id']}', updated_at = now() "
            f"WHERE id = '{curr['id']}'; "
            f"-- {path}"
        )
        matched += 1

    for path in curr_pages:
        if path not in base_pages:
            new.append(path)

    if missing:
        sql_lines.append("")
        sql_lines.append("-- AVISO: paginas no baseline mas ausentes no current (renomeadas ou apagadas):")
        for p in missing:
            sql_lines.append(f"--   - {p}")

    if new:
        sql_lines.append("")
        sql_lines.append("-- INFO: paginas novas no current (sem baseline, slug_id atual sera mantido):")
        for p in new:
            sql_lines.append(f"--   + {p}")

    # ---- Shares ----
    sql_lines.append("")
    sql_lines.append("-- ---- shares.key ----")
    share_matched = 0
    share_missing = []
    share_new = []

    for path, base in sorted(base_shares.items()):
        curr = curr_shares.get(path)
        if not curr:
            share_missing.append(path)
            continue
        if curr["key"] == base["key"]:
            continue
        # Precisa do page id atual pra fazer o UPDATE
        curr_page = curr_pages.get(path)
        if not curr_page:
            sql_lines.append(f"-- WARN: share aponta pra path '{path}' mas pagina nao existe no current. SKIP.")
            continue
        sql_lines.append(
            f"UPDATE shares SET key = '{base['key']}', updated_at = now() "
            f"WHERE page_id = '{curr_page['id']}' AND deleted_at IS NULL; "
            f"-- {path}"
        )
        share_matched += 1

    for path in curr_shares:
        if path not in base_shares:
            share_new.append(path)

    if share_missing:
        sql_lines.append("")
        sql_lines.append("-- AVISO: shares no baseline ausentes no current. Recrie via UI antes do restore:")
        for p in share_missing:
            sql_lines.append(f"--   - {p}  (key esperada: {base_shares[p]['key']})")

    if share_new:
        sql_lines.append("")
        sql_lines.append("-- INFO: shares novos no current sem equivalente no baseline (key sera mantida):")
        for p in share_new:
            sql_lines.append(f"--   + {p}")

    sql_lines.append("")
    sql_lines.append("COMMIT;")
    sql_lines.append("")
    sql_lines.append("-- =================================================================")
    sql_lines.append("-- Resumo")
    sql_lines.append(f"--   pages atualizadas:  {matched}")
    sql_lines.append(f"--   pages ja iguais:    {skipped_unchanged}")
    sql_lines.append(f"--   pages ausentes:     {len(missing)}")
    sql_lines.append(f"--   pages novas:        {len(new)}")
    sql_lines.append(f"--   shares atualizados: {share_matched}")
    sql_lines.append(f"--   shares ausentes:    {len(share_missing)}")
    sql_lines.append(f"--   shares novos:       {len(share_new)}")
    sql_lines.append("-- =================================================================")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(sql_lines), encoding="utf-8")

    print(f"SQL escrito em {args.output}")
    print(f"  pages atualizadas:  {matched}")
    print(f"  pages ja iguais:    {skipped_unchanged}")
    print(f"  pages ausentes:     {len(missing)}")
    print(f"  pages novas:        {len(new)}")
    print(f"  shares atualizados: {share_matched}")
    print(f"  shares ausentes:    {len(share_missing)} (recriar via UI antes de rodar o SQL)")
    print(f"  shares novos:       {len(share_new)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
