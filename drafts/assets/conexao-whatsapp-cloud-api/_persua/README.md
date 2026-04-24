# _persua/ - Overlay de screenshots Persua

Pasta pra dropar suas capturas Persua que vao substituir as versoes flw
(cache raw do MCP) na hora de gerar o ZIP master.

## Como usar

1. Voce captura a tela equivalente na plataforma Persua
2. Salva aqui com o MESMO nome do arquivo flw:
   - `../print-01.png` (flw, cache MCP, nao mexer)
   - `_persua/print-01.png` (Persua, drop aqui)
3. Roda `python3 scripts/build_master_zip.py`
4. O script usa `_persua/print-01.png` no ZIP, ignora a flw

## Como o script decide

Pra cada `print-XX.png` na pasta pai (`../`):
- Se existe `_persua/print-XX.png` → usa a Persua
- Senao → usa a flw e lista como "pendente de captura" no relatorio final

## Por que essa pasta existe

- MCP re-pull sobrescreve cache/flw-raw/ e ../print-XX.png
- Mas NAO toca em `_persua/`, entao suas capturas sobrevivem
- Zero config: drop o arquivo com mesmo nome e funciona

## Dica pra ver o que ja foi trocado

```bash
ls _persua/*.png | wc -l     # quantas Persua voce ja capturou
ls ../print-*.png | wc -l    # total de imagens no tutorial
```

Ou roda o build script e olha a secao "Overlay _persua/" no relatorio.
