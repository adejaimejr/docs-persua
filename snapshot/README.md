# Snapshot de URLs (URL stability)

Pasta destinada a preservar continuidade de URLs entre reimports do Docmost.

## Arquivos

- **`urls-baseline.json`** (versionado), estado canonico dos URLs. Cada deep-link
  ja distribuido pra cliente (`/share/<key>/p/<slug>-<id>`) so continua vivo se
  os campos `pages.slug_id` e `shares.key` no banco continuarem batendo com
  esse baseline.
- **`state-current.json`** (gitignored), dump do estado pos-reimport. Gerado
  por `scripts/dump-state.sql` rodado no Postgres prod.
- **`restore.sql`** (gitignored), UPDATEs gerados por
  `scripts/build-restore-sql.py` que reescrevem o estado atual pra bater com
  o baseline.

## Quando atualizar `urls-baseline.json`

So quando a **estrutura** muda (paginas novas, renomeadas, hierarquia
alterada). A regra geral:
- `slug_id` e `key` aleatorios -> baseline preserva
- Titulos + hierarquia -> baseline reflete

Se voce mudar um titulo, precisa regerar o baseline (senao a heuristica de
match por path falha pra essa pagina).

Pra regerar, ver `tasks.md` secao "Pre-requisito" do fluxo de update.
