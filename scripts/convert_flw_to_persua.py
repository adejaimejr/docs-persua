#!/usr/bin/env python3
"""
Converte markdown bruto em `cache/flw-raw/<slug>.md` para drafts Persua em
`drafts/<slug>.md`, baixando imagens referenciadas para `drafts/assets/<slug>/`.

Transformacoes aplicadas:
1. `{% hint style="X" %}...{% endhint %}` -> `:::X\n...\n:::` (callouts nativos Docmost)
2. `{% content-ref url="..." %}[nome](...)` -> card H3 com nome titulado
3. `{% embed url="..." %}` -> removido (links de drive/youtube nao entram no draft)
4. Trocas de marca: "a plataforma" -> "a Persua"; "plataforma a plataforma" -> "Persua"
5. Preserva "Hunion" (homologacao oficial Meta-Helena, NAO trocar, regra Persua)
6. Preserva links externos da Meta (documentacao oficial)
7. Imagens: baixa via urllib pra drafts/assets/<slug>/print-NN.png e reescreve refs

Nao roda MCP. Le so arquivos locais do cache.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # _tools/docmost
CACHE = BASE / "cache" / "flw-raw"
DRAFTS = BASE / "drafts"
ASSETS = DRAFTS / "assets"

# Slug ja populado manualmente (nao sobrescrever)
PILOTO = {"conexao-whatsapp-cloud-api"}


def replace_brand(text: str) -> str:
    """Substituicoes de marca flw -> Persua, preservando Hunion e refs oficiais."""
    # Ordem importa: frases longas primeiro pra nao ficar "Persua a Persua"
    replacements = [
        (r"\*\*plataforma\*\* a \*\*plataforma\*\*", "**Persua**"),
        (r"\ba plataforma a plataforma\b", "a Persua"),
        (r"\bplataforma a plataforma\b", "Persua"),
        (r"\bna a plataforma\b", "na Persua"),
        (r"\bda a plataforma\b", "da Persua"),
        (r"\bpara a plataforma\b", "para a Persua"),
        (r"\bem a plataforma\b", "na Persua"),
        (r"\bcom a plataforma\b", "com a Persua"),
        (r"\bna plataforma\b", "na Persua"),
        (r"\bda plataforma\b", "da Persua"),
        (r"\bpela plataforma\b", "pela Persua"),
        (r"\bsua plataforma\b", "sua Persua"),
        (r"\bnossa plataforma\b", "a Persua"),
        (r"\bA plataforma\b", "A Persua"),
        (r"\*\*a plataforma\*\*", "**a Persua**"),
        (r"\*\*A plataforma\*\*", "**A Persua**"),
        (r"\*\*plataforma\*\*", "**Persua**"),
        (r"\*\*Plataforma\*\*", "**Persua**"),
    ]
    for pat, repl in replacements:
        text = re.sub(pat, repl, text)
    return text


def convert_hints(text: str) -> str:
    """Converte hints GitBook pra callouts Docmost `:::tipo`.

    Exemplos GitBook:
    {% hint style="success" %}
    Content
    {% endhint %}
    """
    pattern = re.compile(
        r"\{%\s*hint\s+style=\"(\w+)\"\s*%\}\s*(.+?)\s*\{%\s*endhint\s*%\}",
        re.DOTALL,
    )

    def repl(m: re.Match) -> str:
        style = m.group(1).lower()
        body = m.group(2).strip()
        # Normaliza style: GitBook usa 'success/info/warning/danger'
        if style not in {"success", "info", "warning", "danger"}:
            style = "info"
        return f":::{style}\n{body}\n:::"

    return pattern.sub(repl, text)


def strip_content_refs(text: str) -> str:
    """Remove blocos `{% content-ref url="..." %}[label](url){% endcontent-ref %}`.

    Esses blocos sao navegacao interna flw que nao traduz bem para Docmost.
    A navegacao do Docmost ja e feita pela sidebar gerada pelo ZIP.
    """
    pattern = re.compile(
        r"\{%\s*content-ref\s+url=\"[^\"]*\"\s*%\}\s*.*?\s*\{%\s*endcontent-ref\s*%\}",
        re.DOTALL,
    )
    return pattern.sub("", text)


def strip_embeds(text: str) -> str:
    """Remove `{% embed url="..." %}` (links de video de drive/youtube)."""
    pattern = re.compile(r"\{%\s*embed\s+url=\"[^\"]*\"\s*%\}", re.DOTALL)
    return pattern.sub("", text)


def extract_image_urls(text: str) -> list[str]:
    """Extrai URLs de imagens em sintaxe markdown E HTML.

    Captura:
    - `![alt](url)` onde url comeca com http. URLs podem ter `\\(` e `\\)`
      escapados (GitBook faz isso pra parens no filename).
    - `<img src="url" ...>` (HTML, vem dentro de `<figure>`)
    """
    urls = []
    seen = set()

    # Padrao markdown: ![alt](url)
    # URL aceita tudo que nao seja `)` nao escapado (usa `\\.` pra absorver escapes)
    md_pattern = re.compile(r"!\[[^\]]*\]\((https?://(?:\\.|[^()\\])+)\)")
    for match in md_pattern.finditer(text):
        raw_url = match.group(1)
        # Desescapa \( e \) pra URL real (vao ser re-encoded pelo urllib se precisar)
        url = raw_url.replace(r"\(", "(").replace(r"\)", ")")
        if url not in seen:
            urls.append(url)
            seen.add(url)

    # Padrao HTML: <img src="url" ...>
    html_pattern = re.compile(r'<img\s+[^>]*src="(https?://[^"]+)"', re.IGNORECASE)
    for match in html_pattern.finditer(text):
        url = match.group(1)
        if url not in seen:
            urls.append(url)
            seen.add(url)

    return urls


def download_image(url: str, dest: Path) -> bool:
    """Baixa imagem via urllib. Retorna True se OK.

    URLs do GitBook tem parens `(` `)` no path. HTTP requer eles como %28 %29.
    Reescreve o path preservando o query string.
    """
    parsed = urllib.parse.urlparse(url)
    # Re-encode path mantendo `/` e `%` ja existentes; converte `(` e `)` pra %28 %29
    safe_path = urllib.parse.quote(parsed.path, safe="/%")
    encoded_url = urllib.parse.urlunparse((
        parsed.scheme, parsed.netloc, safe_path, parsed.params, parsed.query, parsed.fragment
    ))
    try:
        req = urllib.request.Request(encoded_url, headers={"User-Agent": "persua-docmost/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.read())
        return True
    except Exception as e:
        print(f"  erro baixando {url[:80]}...: {e}")
        return False


def rewrite_image_refs(text: str, slug: str, url_map: dict[str, str]) -> str:
    """Reescreve URLs de imagem pra paths locais relativos.

    url_map e um dict {url_original: nome_do_arquivo_local}.
    Substitui tanto a URL "desescapada" quanto a "escapada com \\(  \\)".
    """
    for url, filename in url_map.items():
        local = f"assets/{slug}/{filename}"
        # Substitui URL tal como aparece no markdown original (com \( escapados)
        url_escaped = url.replace("(", r"\(").replace(")", r"\)")
        text = text.replace(url_escaped, local)
        # Substitui URL direta (sem escape) em HTML <img src="...">
        text = text.replace(url, local)

    # Converte `<figure><img src="assets/..." ...></figure>` em markdown puro
    def figure_to_md(m: re.Match) -> str:
        src = m.group(1)
        alt = m.group(2) or ""
        return f"![{alt}]({src})"

    figure_pattern = re.compile(
        r'<figure>\s*<img\s+src="([^"]+)"(?:\s+alt="([^"]*)")?[^>]*>(?:\s*<figcaption>[^<]*</figcaption>)?\s*</figure>',
        re.IGNORECASE | re.DOTALL,
    )
    text = figure_pattern.sub(figure_to_md, text)

    return text


def title_from_content(content: str, slug: str) -> str:
    """Extrai H1 do markdown (ou gera do slug)."""
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return slug.replace("-", " ").title()


def process_file(slug: str, cache_path: Path, skip_images: bool = False) -> dict:
    """Processa um arquivo do cache, gera draft + baixa imagens.

    Retorna stats: {slug, title, images_total, images_ok, images_failed}.
    """
    if slug in PILOTO:
        # Nao sobrescreve o piloto que foi populado manualmente
        print(f"  [skip] {slug}: piloto manual preservado")
        return {"slug": slug, "skipped": True}

    raw = cache_path.read_text(encoding="utf-8")

    # Transforma sintaxe GitBook -> Docmost
    text = raw
    text = convert_hints(text)
    text = strip_content_refs(text)
    text = strip_embeds(text)
    text = replace_brand(text)

    # Extrai imagens e baixa
    image_urls = extract_image_urls(text)
    url_map = {}
    images_ok = 0
    images_failed = 0

    if image_urls and not skip_images:
        slug_assets = ASSETS / slug
        for idx, url in enumerate(image_urls, start=1):
            # Descobre extensao pelo URL
            parsed = urllib.parse.urlparse(url)
            ext_match = re.search(r"\.(png|jpg|jpeg|gif|svg|webp)(?:\?|$)", parsed.path, re.IGNORECASE)
            ext = ext_match.group(1).lower() if ext_match else "png"
            filename = f"print-{idx:02d}.{ext}"
            dest = slug_assets / filename
            if dest.exists():
                # Ja baixada em execucao anterior
                url_map[url] = filename
                images_ok += 1
                continue
            ok = download_image(url, dest)
            if ok:
                url_map[url] = filename
                images_ok += 1
            else:
                images_failed += 1

    # Reescreve URLs de imagens no draft pra paths locais
    text = rewrite_image_refs(text, slug, url_map)

    # Limpa linhas vazias duplicadas resultantes das remocoes
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    # Salva em drafts/<slug>.md
    draft_path = DRAFTS / f"{slug}.md"
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(text, encoding="utf-8")

    title = title_from_content(text, slug)
    return {
        "slug": slug,
        "title": title,
        "images_total": len(image_urls),
        "images_ok": images_ok,
        "images_failed": images_failed,
    }


def main():
    skip_images = "--skip-images" in sys.argv
    only_slug = None
    for arg in sys.argv[1:]:
        if arg.startswith("--only="):
            only_slug = arg.split("=", 1)[1]

    if not CACHE.exists():
        print(f"Cache nao encontrado: {CACHE}")
        sys.exit(1)

    cache_files = sorted(CACHE.glob("*.md"))
    if only_slug:
        cache_files = [f for f in cache_files if f.stem == only_slug]

    print(f"Processando {len(cache_files)} arquivos do cache...")
    if skip_images:
        print("(imagens: SKIP)")

    stats = []
    for cf in cache_files:
        slug = cf.stem
        s = process_file(slug, cf, skip_images=skip_images)
        stats.append(s)
        if not s.get("skipped"):
            imgs = f"{s.get('images_ok', 0)}/{s.get('images_total', 0)} imgs"
            print(f"  [ok] {slug}: {s.get('title', '?')} ({imgs})")

    # Relatorio
    total = len([s for s in stats if not s.get("skipped")])
    total_imgs = sum(s.get("images_total", 0) for s in stats)
    total_ok = sum(s.get("images_ok", 0) for s in stats)
    total_fail = sum(s.get("images_failed", 0) for s in stats)

    print()
    print(f"Drafts gerados: {total}")
    print(f"Imagens: {total_ok}/{total_imgs} baixadas, {total_fail} falharam")


if __name__ == "__main__":
    main()
