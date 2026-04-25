# Tasks, Tutoriais Docmost Persua

## Producao em docs.persua.com.br (LIVE)

- **URL publica:** https://docs.persua.com.br (redirect automatico pra share root)
- **Share atual:** `gbgk3jiefs` -> base-de-conhecimento-7fjGrtZ7DD (atualizado 2026-04-24)
- **Repo:** github.com/adejaimejr/docs-persua
- **Volume:** `docs-persua-data`
- **Postgres:** `postgres_postgres` (db dedicado `docmost`)
- **Redis:** `redis_redis` (DB 4 reservado)
- **Constraint:** node.hostname=manager1

### Fluxo de update em producao (Caminho 2 escolhido)

1. Edita drafts + captura telas em `_persua/` localmente
2. `python3 scripts/build_master_zip.py`
3. `git add . && git commit -m "..." && git push`
4. No Docmost UI: delete raiz "Base de Conhecimento" + esvazia lixeira
5. Settings > Import > upload do ZIP atualizado
6. Recompartilha publicamente, copia URL gerada
7. `./scripts/update-share-id.sh <URL_DO_NOVO_SHARE>`
8. `git add Dockerfile && git commit && git push` (Dokploy autodeploy)

## Em progresso / aguardando usuario
- **Capturar telas Persua** em batch e dropar nos respectivos `drafts/assets/<slug>/_persua/`
  - 101 tutoriais com drafts prontos, 556 imagens (incluindo jpg/jpeg/gif) no total
  - 45 imagens Persua ja capturadas em 14 slugs = 8% do total (baseline 2026-04-24)
  - 4 slugs 100% Persua: acessando-pela-web, abrir-dados-do-contato, adicionar-etapa, assumir-atendimento
  - Pra cada batch capturado, rodar `python3 scripts/build_master_zip.py` regenera o ZIP automaticamente

## Proximo passo
- **Continuar capturas Persua** focando em completar os 10 slugs parciais:
  - alterar-perfil-do-whatsapp (1/5), api-nao-oficial (1/12), api-oficial (2/9)
  - apps-ativar-app-de-pagamento (3/6), apps-cancelar-estornar-pagamento (5/7)
  - apps-consultar-pagamento (5/6), apps-integrar-com-banco-asaas (2/5)
  - arquivar-campanha (5/7), ativar-e-desativar-funcionalidade (3/9)
  - conexao-whatsapp-cloud-api (9/16)
- Depois de cada batch, repetir o fluxo de update em producao (build, push, reimport, update-share-id)

## Estatisticas atuais

### Cache flw-raw (markdown bruto do MCP)
- 101 paginas baixadas (100% do sitemap mapeado)
- Estrutura: /guide/atalhos/faq/* (22), /guide/documentacao/atendimento/* (21),
  /guide/documentacao/apps/* (34), /guide/documentacao/ajustes/* (13),
  /guide/documentacao/relatorios/* (3), /guide/faq/* (6), pagina raiz piloto (1)

### Drafts Persua (adaptados)
- 101 drafts gerados automaticamente via `scripts/convert_flw_to_persua.py`
- Transformacoes: hints -> callouts Docmost, marca flw -> Persua, `<figure>` -> markdown
- 237/240 imagens baixadas do CDN GitBook (98.75%), 3 falharam com 404

### ZIP master
- 156 paginas .md (11 secoes + subpaginas aninhadas ate nivel 3)
- 556 imagens (png + jpg/jpeg/gif suportados desde 2026-04-24)
- Tamanho: 76 MB
- 120 paginas populadas com draft, 0 placeholders
- Cobertura overlay Persua: 45/556 imagens (8%)

## Backlog priorizado

### Prioridade ALTA, Tier 1 onboarding (8 paginas)
- [~] Conexao WhatsApp Cloud API (9/16 Persua, parcial)
- [x] Acessando a Plataforma pela Web (1/1 Persua)
- [ ] Acessando a Plataforma pelo App Movel
- [x] Abrir Dados do Contato (3/3 Persua)
- [ ] Iniciar atendimento
- [x] Assumir atendimento (1/1 Persua, gif animado)
- [ ] Transferir atendimento
- [ ] Concluir e classificar atendimento

### Prioridade MEDIA, Conexao + Portfolio + Perfil (14 paginas)
- [ ] Conexao via QR Code (Coexistencia)
- [ ] Portabilidade de numero
- [ ] Remover conexao QR Code
- [ ] Remover numero do portfolio
- [ ] Desativar contas de anuncio
- [ ] Criar portfolio empresarial
- [ ] Verificar portfolio empresarial
- [ ] Informacoes do portfolio
- [ ] Incluir administradores
- [ ] Alterar logomarca do portfolio
- [ ] Desativar autenticacao em 2 fatores
- [ ] Alterar nome de exibicao (Display Name)
- [~] Alterar perfil do WhatsApp (1/5 Persua, parcial)
- [ ] Configurar pagamento (Meta) + Consultar extrato

### Prioridade MEDIA, Atendimento avancado + Apps (60+ paginas)
- [ ] Ferramentas de Interacao (8 subs)
- [ ] Integracao com CRM (1 sub)
- [ ] Grupos do WhatsApp Atendimento (3 subs)
- [ ] Campanhas (6 subs)
- [ ] Chatbot (4 subs, inclui pergunta dinamica)
- [ ] Sequencias (8 subs)
- [ ] Pagamentos App (4 subs)
- [ ] IA Agentes Inteligentes (6 subs)
- [ ] Mensagens Agendadas (3 subs)
- [ ] Chat Interno (2 subs)
- [ ] Grupos/Tempo/Distribuicao/Transcricao (varios)

### Prioridade BAIXA, Relatorios + Ajustes + FAQ (26 paginas)
- [ ] Relatorios (3 paginas)
- [ ] Ajustes Conta (2 subs)
- [ ] Ajustes Equipes (3 subs)
- [ ] Ajustes Integracoes (3 subs)
- [ ] Ajustes Modelo de Mensagens (4 subs)
- [ ] Ajustes Usuarios (3 subs)
- [ ] FAQ (10 paginas)

## Melhorias de UX/Design pendentes (feedback chiefs)
- [ ] Link clicavel no callout "Comece Aqui" da home (editar manualmente apos import)
- [ ] Analytics instrumentado (Plausible ou Umami via CSS/script injection no Dockerfile)
- [ ] Placeholders fora do indice de busca (estudar API de search do Docmost)
- [ ] Cores da marca Persua aplicadas via CSS custom (se usuario aprovar paleta)
- [ ] 3 imagens com 404 na fonte flw: precisam ser capturadas na Persua direto

## Concluido
- [x] Setup Docmost Docker local com patches PT-BR (2026-04-22)
- [x] Remocao do "Powered by Docmost" via patch (2026-04-22)
- [x] Rascunho piloto: Criar modelo de mensagem para campanha (2026-04-22)
- [x] MCP `documentacao-ref` instalado e carregado (2026-04-23)
- [x] Rascunho piloto completo: Conexao WhatsApp Cloud API com 16 imagens, callouts nativos, link Meta docs (2026-04-23)
- [x] Consulta aos chiefs (design-chief + brand-chief) pra definir icones da sidebar (2026-04-23)
- [x] Esqueleto master ZIP com 48 paginas + estrutura hierarquica + metadata de icones (2026-04-23)
- [x] Script `scripts/build_master_zip.py` idempotente (2026-04-23)
- [x] Cache do conteudo bruto do MCP em `cache/flw-raw/` (2026-04-23)
- [x] Fix emoji duplicado na sidebar (2026-04-23)
- [x] Fix drag-drop markers virando markdown images no import ZIP (2026-04-23)
- [x] Ordenacao forcada via position no metadata JSON (2026-04-23)
- [x] Revisao final dos chiefs (design + brand) pos-import (2026-04-23)
- [x] CSS custom reversivel: sidebar larga + text-wrap + esconde link docmost (2026-04-23)
- [x] Title custom da aba "Base de Conhecimento Persua" (2026-04-23)
- [x] Home reescrita com voz Persua brasileira e conversacional (2026-04-23)
- [x] Logo Persua no header + favicon (2026-04-23)
- [x] Fix scroll do logo (position:fixed) (2026-04-23)
- [x] Dark logo + fix menu sidebar (classes CSS modules + rowHeight patch) (2026-04-23)
- [x] Reducao tipografia (body 15px, h1 28px, page-title 32px) + callout size fix (2026-04-23)
- [x] Sistema overlay _persua/ para de-para de imagens (scripts/build_master_zip.py) (2026-04-23)
- [x] Discovery completo do sitemap flw.chat (~90 URLs) (2026-04-24)
- [x] Download massivo: 100 paginas baixadas via MCP em 2 agents paralelos (2026-04-24)
- [x] Script convert_flw_to_persua.py criado: hints->callouts, marca, imagens, figures (2026-04-24)
- [x] Conversao completa: 101 drafts gerados + 237/240 imagens baixadas (2026-04-24)
- [x] TREE expandido: 48 -> 138 paginas, SLUG_MAP com 100+ entradas (2026-04-24)
- [x] ZIP master v2: 138 paginas .md + 245 imagens, 33MB (2026-04-24)
- [x] Batch capturas Persua: 13 slugs novos + 36 imagens em _persua/ (2026-04-24)
- [x] Suporte jpg/jpeg/gif no overlay _persua/ no build_master_zip.py (2026-04-24)
- [x] Deploy do batch: ZIP reimportado, share atualizado pra gbgk3jiefs (2026-04-24)

## Fora de escopo (nao fazer)
- Destravar features da EE (API, SSO, Audit, IA): licenca comercial
- Migrar para GitBook ou Mintlify: decisao ja tomada
- Copiar screenshots flw.chat diretamente pra producao: usar so como placeholder, substituir por Persua antes de publicar
