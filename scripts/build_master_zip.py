#!/usr/bin/env python3
"""
Gera o ZIP master da Base de Conhecimento Persua para import no Docmost.

Estrutura:
- Base de Conhecimento.md (raiz)
- Base de Conhecimento/<Secao>.md (paginas pai de cada tier)
- Base de Conhecimento/<Secao>/<Sub>.md (sub paginas, profundidade 2)
- Base de Conhecimento/<Secao>/<Sub>/<SubSub>.md (sub-sub, profundidade 3)
- docmost-metadata.json (mapeia icones + ordem)
- assets/<slug>/ (imagens dos tutoriais, com overlay _persua/)

Fluxo de conteudo:
1. Cada (secao, pagina) tem um slug explicito em SLUG_MAP
2. Se `drafts/<slug>.md` existe, usa como conteudo
3. Senao, gera placeholder "Pagina em desenvolvimento"
4. Para pagina pai com subs, gera cards H3 das subpaginas

Overlay _persua/:
- Para cada `<slug>/print-NN.{png,jpg,jpeg,gif}`, checa `<slug>/_persua/print-NN.<ext>`
- Se existe, usa a Persua no ZIP (mesma path final, so muda a origem)
- Relatorio final mostra % Persua vs flw pendentes
"""

from __future__ import annotations

import os
import json
import re
import shutil
import zipfile
import urllib.parse
from pathlib import Path
from typing import Optional

IMG_EXTS = ("*.png", "*.jpg", "*.jpeg", "*.gif")

BASE = Path(__file__).resolve().parent.parent  # _tools/docmost
STAGING = Path("/tmp/docmost-master")
OUT_ZIP = BASE / "import-packages" / "base-de-conhecimento-master.zip"
ROOT = "Base de Conhecimento"
DRAFTS = BASE / "drafts"
ASSETS_SRC = BASE / "drafts" / "assets"


# =============================================================================
# SLUG_MAP: titulo Persua -> slug do draft/cache
# =============================================================================
# Mapeia o titulo exibido (em PT-BR com acento) pro slug do arquivo em
# `drafts/<slug>.md`. Slugs vem do cache/flw-raw/ (ultima parte do URL flw).
#
# Titulos que aparecem em DOIS lugares (ex: "Grupos do WhatsApp" em Atendimento
# E em Apps) usam chave com prefixo de secao pra desambiguar.

SLUG_MAP = {
    # Comece Aqui
    "Acessando a Plataforma pela Web": "acessando-pela-web",
    "Acessando a Plataforma pelo App Móvel": "acessando-pelo-app",
    "Abrir Dados do Contato": "abrir-dados-do-contato",

    # Conexão WhatsApp
    "Conexão WhatsApp Cloud API": "conexao-whatsapp-cloud-api",
    "Conexão via QR Code (Coexistência)": "conexao-via-qr-code",
    "Portabilidade de número": "portabilidade-de-numero",
    "Remover conexão QR Code": "remover-conexao-qr-code",
    "Remover número do portfólio": "remover-numero-do-portfolio",
    "Desativar contas de anúncio": "desativar-contas-de-anuncio",

    # Portfólio Empresarial
    "Criar portfólio empresarial": "criar-portfolio-empresarial",
    "Verificar portfólio empresarial": "verificar-portfolio-empresarial",
    "Informações do portfólio": "informacoes-do-portfolio",
    "Incluir administradores": "incluir-administradores",
    "Alterar logomarca do portfólio": "alterar-logomarca-do-portfolio",
    "Desativar autenticação em 2 fatores": "desativar-autenticacao-em-dois-fatores",

    # Perfil WhatsApp Business
    "Alterar nome de exibição": "alterar-display-name",
    "Alterar perfil do WhatsApp": "alterar-perfil-do-whatsapp",

    # Pagamentos (Meta)
    "Configurar pagamento (Meta)": "configurar-pagamento",
    "Consultar extrato de pagamento": "consultar-extrato-de-pagamento",

    # Atendimento > Comece Aqui
    "Central de Atendimento, Acessando pela Web": "acessando-pela-web",
    "Central de Atendimento, Acessando pelo App Móvel": "acessando-pelo-app",
    "Central de Atendimento, Abrir Dados do Contato": "abrir-dados-do-contato",

    # Atendimento > Operações
    "Iniciar atendimento": "iniciar-atendimento",
    "Assumir atendimento": "assumir-atendimento",
    "Transferir atendimento": "transferir-atendimento",
    "Reiniciar atendimento": "reiniciar-atendimento",
    "Concluir e classificar atendimento": "concluir-atendimento",
    "Alterar padrão de arquivamento": "alterar-padrao-de-arquivamento-12h-imediato",

    # Atendimento > Ferramentas
    "Enviar imagem": "enviar-imagem",
    "Enviar vídeo": "enviar-video",
    "Enviar áudio": "enviar-audio",
    "Gravar áudio": "gravar-audio",
    "Enviar documento": "enviar-documento",
    "Enviar modelo de mensagem": "enviar-modelo-de-mensagem",
    "Enviar mensagem rápida": "enviar-mensagem-rapida",
    "Agendar mensagem pelo atendimento": "agendamentos-pelo-atendimento",

    # Atendimento > Integração CRM
    "Inserir card em painel": "inserir-card-em-painel-1",

    # Atendimento > Grupos
    "Grupos API Oficial": "api-oficial",
    "Grupos API Não Oficial": "api-nao-oficial",
    "Gerenciar grupos (Arquivar, Bloquear, Sair, Excluir)": "gerenciar-grupos-arquivar-bloquear-sair-excluir",

    # Apps > Campanhas
    "Criar nova campanha": "criar-nova-campanha",
    "Criar modelo de mensagem para campanha": "criar-modelo-de-mensagem-para-campanha",
    "Consultar campanha": "consultar-campanha",
    "Exportar campanha": "exportar-campanha",
    "Arquivar campanha": "arquivar-campanha",
    "Riscos e custos da campanha": "riscos-e-custos-da-campanha",

    # Apps > Chatbot
    "Tipos de chatbot": "tipos-de-chatbot",
    "Criando um chatbot": "criando-um-chatbot",
    "Bloco Enviar Mensagem (chatbot)": "chatbot-enviar-mensagem",
    "Pergunta dinâmica (chatbot)": "chatbot-pergunta-dinamica",

    # Apps > Sequências
    "Criar sequência": "criar-sequencia",
    "Objetivo da sequência": "objetivo-da-sequencia",
    "Adicionar etapa": "adicionar-etapa",
    "Incluir contato na sequência": "incluir-contato-na-sequencia",
    "Visualizar contatos da sequência": "visualizar-contatos",
    "Finalizar sequência": "finalizar-sequencia",
    "Reiniciar sequência": "reiniciar-sequencia",
    "Desabilitar ou excluir sequência": "desabilitar-excluir-sequencia",

    # Apps > Pagamentos (módulo)
    "Ativar app de Pagamento": "apps-ativar-app-de-pagamento",
    "Integrar com banco Asaas": "apps-integrar-com-banco-asaas",
    "Consultar pagamento": "apps-consultar-pagamento",
    "Cancelar ou estornar pagamento": "apps-cancelar-estornar-pagamento",

    # Apps > IA, Agentes Inteligentes
    "Novo agente": "novo-agente",
    "Aba de configurações (Agentes IA)": "aba-configuracoes",
    "Habilidades do agente": "habilidades",
    "Simular tempo de digitação": "simular-tempo-de-digitacao",
    "Indicador de digitando": "indicador-de-digitando",
    "Versões dos agentes": "versoes-dos-agentes",

    # Apps > Mensagens Agendadas
    "Modelo para mensagens agendadas": "modelo-para-mensagens-agendadas",
    "Como gerenciar os agendamentos": "como-gerenciar-os-agendamentos",
    "Agendamentos pelo CRM": "agendamentos-pelo-crm",

    # Apps > Chat Interno
    "Ativar e desativar funcionalidade (Chat Interno)": "ativar-e-desativar-funcionalidade",
    "Tipos de conversa (Usuário, Equipe, Todos)": "tipos-de-conversa-usuario-x-equipe-x-todos",

    # Apps > Grupos do WhatsApp (módulo)
    "Habilitar app de Grupos": "habilitar-o-app",

    # Apps > Tempo de Segurança
    "Corrigir sincronização do Tempo de Segurança": "como-corrigir-problemas-com-a-sincronizacao-do-tempo-de-seguranca",

    # Apps > Distribuição
    "Configuração da Distribuição de Atendimentos": "distribuicao-de-atendimentos-leaf",

    # Apps > Transcrição IA
    "Degustação de Transcrição de Áudio": "degustacao-de-transcricao-de-audio",

    # Relatórios
    "Como exportar relatório": "como-exportar-relatorio-na-plataforma",
    "Como concluir atendimentos em massa": "como-concluir-atendimentos-em-massa",
    "Consumo de infraestrutura": "consumo-de-infraestrutura",

    # Ajustes > Conta
    "Remover canal de atendimento": "remover-canal-de-atendimento",
    "Horário de atendimento": "horario-de-atendimento",

    # Ajustes > Equipes
    "Cadastrar equipe": "cadastrar-equipe",
    "Distribuição e transbordo de atendimento": "distribuicao-e-transbordo-de-atendimento",
    "Tipo de associação Usuário x Supervisor": "tipo-de-associacao-usuario-x-supervisor",

    # Ajustes > Integrações
    "Botão do WhatsApp e Tag de rastreamento": "botao-do-whatsapp-e-tag-de-rastreamento",
    "Renovar token do Instagram e Messenger": "renovar-token-do-instagram-e-messenger",
    "Transcrição de áudio (integração)": "transcricao-de-audio",

    # Ajustes > Modelos de Mensagens
    "Cadastrar modelos de mensagem": "cadastrar-modelos-de-mensagem",
    "Como criar modelo de mensagem": "como-criar-modelo-de-mensagem",
    "Editar modelos de mensagem": "editar-modelos-de-mensagem",
    "Marketing x Utilidade (modelos)": "mensagens-de-marketing-x-mensagens-de-utilidade",

    # Ajustes > Usuários
    "Tipos de perfis de usuários": "tipos-de-perfis-de-usuarios",
    "Cadastrar usuários": "cadastrar-usuarios",
    "Editar foto do usuário": "editar-foto-do-usuario",

    # CRM > Contato
    "Cadastrar contato": "crm-cadastrar-contato",
    "Inserir etiqueta em contato": "crm-inserir-etiqueta",
    "Importar contatos em lote": "crm-importacao-de-contatos",
    "Exportar base de contatos": "crm-exportar-base-de-contatos",

    # CRM > Carteiras
    "Tipos de carteiras": "crm-tipos-de-carteiras",
    "Criar uma nova carteira": "crm-criar-carteira",
    "Incluir contato na carteira": "crm-incluir-contato-carteira",
    "Alterar ou excluir uma carteira": "crm-alterar-excluir-carteira",

    # CRM > Painéis (Vendas)
    "Criar e configurar um Painel de Vendas": "crm-criar-painel-vendas",
    "Duplicação de Painel de Vendas": "crm-duplicacao-painel",
    "Marcar card como Ganho": "crm-marcar-como-ganho",
    "Marcar card como Perda": "crm-marcar-como-perda",
    "Filtros por Situação no CRM": "crm-filtros-por-situacao",
    "Exclusão segura de etapas do painel": "crm-exclusao-de-etapas",

    # Relatórios (complemento)
    "Como exportar mensagens": "como-exportar-mensagens-na-plataforma",

    # FAQ
    "Número Privado (LID) e Unificação de Contatos": "faq-numero-privado-lid",
    "Status de Integridade do Canal": "faq-status-integridade-canal",
    "Rate Limit da API Não Oficial": "faq-rate-limit-api-nao-oficial",
    "Mensagem Aguardando": "faq-mensagens-waiting",
    "Códigos de Erros da Meta": "codigos-de-erros-da-meta",
    "Solicitar revisão de banimento": "solicitar-revisao-de-banimento",
    "Mensagens do Instagram não chegam": "mensagens-do-instagram-nao-chegam",
    "Acessar página de suporte": "acessar-pagina-de-suporte",
    "Por que a Meta rejeita modelos de Marketing?": "faq-meta-rejeita-modelos-marketing",
    "Por que a Meta rejeita modelos de Utilidade?": "faq-meta-rejeita-modelos-utilidade",
}


def resolve_draft(title: str) -> Path | None:
    """Resolve um titulo de pagina pro Path do draft correspondente.

    Retorna Path se existe o draft, None se nao tiver mapping ou draft.
    """
    slug = SLUG_MAP.get(title)
    if not slug:
        return None
    draft = DRAFTS / f"{slug}.md"
    return draft if draft.exists() else None


# =============================================================================
# TREE: estrutura hierarquica de toda a Base de Conhecimento
# =============================================================================
# Formato:
# - pagina folha: ("icone", "titulo", "descricao")
# - pagina com subs: ("icone", "titulo", "descricao", [subs])
# - subpagina: segue o mesmo formato recursivamente

TREE = {
    "icon": "📚",
    "title": "Base de Conhecimento",
    "description": (
        "Bem-vindo à Base de Conhecimento da Persua. "
        "Aqui você encontra todos os guias para usar nossa plataforma de CRM conversacional: "
        "conexão com WhatsApp, atendimento, campanhas, IA e muito mais."
    ),
    "sections": [
        {
            "icon": "👋",
            "title": "Comece Aqui",
            "description": (
                "Primeiros passos essenciais para usar a Persua com segurança e autonomia. "
                "Acesso à plataforma, dados do contato e fundamentos do atendimento."
            ),
            "pages": [
                ("💻", "Acessando a Plataforma pela Web",
                 "Como fazer login na Persua pelo navegador com segurança e código de validação."),
                ("📱", "Acessando a Plataforma pelo App Móvel",
                 "Como fazer login no aplicativo móvel da Persua com código de validação."),
                ("📇", "Abrir Dados do Contato",
                 "Como consultar e editar as informações do contato durante o atendimento."),
            ],
        },
        {
            "icon": "🔗",
            "title": "Conexão WhatsApp",
            "description": (
                "Tudo sobre como conectar seu número de WhatsApp à Persua. "
                "Escolha entre Cloud API oficial ou QR Code, faça portabilidade de número "
                "ou gerencie conexões existentes."
            ),
            "pages": [
                ("🔌", "Conexão WhatsApp Cloud API",
                 "Método oficial da Meta para vincular seu WhatsApp Business à Persua."),
                ("📷", "Conexão via QR Code (Coexistência)",
                 "Método alternativo de conexão via escaneamento, com uso simultâneo no app."),
                ("🔄", "Portabilidade de número",
                 "Migre seu número da API Oficial de outro provedor sem perder histórico."),
                ("🗑️", "Remover conexão QR Code",
                 "Como desvincular uma conexão QR Code quando precisar trocar de método."),
                ("❌", "Remover número do portfólio",
                 "Como desconectar e remover números que não usa mais."),
                ("🚫", "Desativar contas de anúncio",
                 "Como desativar contas de anúncio antes de remover o portfólio empresarial."),
            ],
        },
        {
            "icon": "🗂️",
            "title": "Portfólio Empresarial",
            "description": (
                "Configure e gerencie seu Portfólio Empresarial no Meta Business Manager. "
                "Criação, verificação, administradores e configurações de segurança."
            ),
            "pages": [
                ("🆕", "Criar portfólio empresarial",
                 "Como criar um novo Portfólio Empresarial no Meta Business Manager."),
                ("✅", "Verificar portfólio empresarial",
                 "Processo de verificação oficial do portfólio junto à Meta."),
                ("ℹ️", "Informações do portfólio",
                 "Dados básicos e identificação do seu portfólio empresarial na Meta."),
                ("👥", "Incluir administradores",
                 "Como adicionar outros administradores ao seu portfólio empresarial."),
                ("🖼️", "Alterar logomarca do portfólio",
                 "Como alterar a logomarca que representa sua empresa no portfólio."),
                ("🔓", "Desativar autenticação em 2 fatores",
                 "Como desativar a autenticação em dois fatores quando necessário."),
            ],
        },
        {
            "icon": "🪪",
            "title": "Perfil do WhatsApp Business",
            "description": (
                "Personalize o perfil do seu WhatsApp Business, "
                "incluindo nome de exibição, descrição, endereço e demais informações que seus clientes veem."
            ),
            "pages": [
                ("✏️", "Alterar nome de exibição",
                 "Como alterar o Display Name que seus clientes veem no WhatsApp."),
                ("📝", "Alterar perfil do WhatsApp",
                 "Como atualizar nome, descrição, endereço, site e demais dados do perfil."),
            ],
        },
        {
            "icon": "💳",
            "title": "Pagamentos",
            "description": (
                "Cadastre e gerencie a forma de pagamento exigida pela Meta "
                "para operar a API Oficial do WhatsApp Business. Inclui consulta de extrato."
            ),
            "pages": [
                ("💰", "Configurar pagamento (Meta)",
                 "Como cadastrar forma de pagamento no Meta Business Manager."),
                ("📑", "Consultar extrato de pagamento",
                 "Como acompanhar os custos das conversas realizadas via API oficial."),
            ],
        },
        {
            "icon": "💬",
            "title": "Atendimento",
            "description": (
                "O coração da Persua. Aprenda a operar a central de atendimento, "
                "transferir conversas, usar ferramentas de interação e integrar com o CRM."
            ),
            "pages": [
                ("🎧", "Central de Atendimento",
                 "Visão geral da central onde você recebe e gerencia atendimentos.",
                 [
                     ("💻", "Central de Atendimento, Acessando pela Web",
                      "Login e navegação pela interface web da central."),
                     ("📱", "Central de Atendimento, Acessando pelo App Móvel",
                      "Login e navegação pelo aplicativo móvel."),
                     ("📇", "Central de Atendimento, Abrir Dados do Contato",
                      "Como consultar e editar dados do contato durante o atendimento."),
                 ]),
                ("🛠️", "Operações no Atendimento",
                 "Transferir, assumir, concluir e outras operações durante o atendimento.",
                 [
                     ("▶️", "Iniciar atendimento",
                      "Como iniciar um novo atendimento ativo ou receptivo."),
                     ("✋", "Assumir atendimento",
                      "Como assumir um atendimento da aba Novos."),
                     ("🔀", "Transferir atendimento",
                      "Como transferir atendimentos entre equipes ou atendentes."),
                     ("🔁", "Reiniciar atendimento",
                      "Como retomar um atendimento após a janela de 24h da Meta."),
                     ("🏁", "Concluir e classificar atendimento",
                      "Como finalizar e classificar atendimentos para relatórios."),
                     ("🕐", "Alterar padrão de arquivamento",
                      "Escolha entre arquivar em 12h ou imediatamente após concluir."),
                 ]),
                ("📎", "Ferramentas de Interação",
                 "Recursos adicionais como mídias, modelos, respostas rápidas e agendamentos.",
                 [
                     ("🖼️", "Enviar imagem",
                      "Formatos, limites e como enviar imagens em cada canal."),
                     ("🎥", "Enviar vídeo",
                      "Formatos, limites e como enviar vídeos em cada canal."),
                     ("🎵", "Enviar áudio",
                      "Formatos, limites e como enviar áudios em cada canal."),
                     ("🎤", "Gravar áudio",
                      "Como gravar áudio direto pela plataforma."),
                     ("📄", "Enviar documento",
                      "Formatos, limites e como enviar PDFs e outros documentos."),
                     ("📋", "Enviar modelo de mensagem",
                      "Como enviar templates aprovados pela Meta."),
                     ("⚡", "Enviar mensagem rápida",
                      "Como usar mensagens pré-cadastradas para agilizar respostas."),
                     ("⏰", "Agendar mensagem pelo atendimento",
                      "Como programar o envio de mensagens a partir do atendimento."),
                 ]),
                ("🔗", "Integração com o CRM",
                 "Como os atendimentos se conectam com contatos e negociações no CRM.",
                 [
                     ("📌", "Inserir card em painel",
                      "Como criar cards nos painéis do CRM direto pelo atendimento."),
                 ]),
                ("👥", "Grupos do WhatsApp",
                 "Como criar e gerenciar grupos do WhatsApp via Persua.",
                 [
                     ("🏢", "Grupos API Oficial",
                      "Regras e limites para grupos em canais da API Oficial."),
                     ("📱", "Grupos API Não Oficial",
                      "Regras e limites para grupos em canais da API Não Oficial."),
                     ("🗃️", "Gerenciar grupos (Arquivar, Bloquear, Sair, Excluir)",
                      "Ações de controle: arquivar, bloquear, sair ou excluir grupos."),
                 ]),
            ],
        },
        {
            "icon": "👥",
            "title": "CRM",
            "description": (
                "Organize seus contatos, crie funis de venda e acompanhe o relacionamento "
                "com seus clientes do primeiro contato ao pós-venda."
            ),
            "pages": [
                ("📇", "Contato",
                 "Cadastre, importe e organize seus contatos no CRM da Persua.",
                 [
                     ("➕", "Cadastrar contato",
                      "Como cadastrar um novo contato manualmente."),
                     ("🏷️", "Inserir etiqueta em contato",
                      "Como organizar contatos com etiquetas personalizadas."),
                     ("📥", "Importar contatos em lote",
                      "Como importar contatos via Excel, CSV ou vCard."),
                     ("📤", "Exportar base de contatos",
                      "Como exportar sua base de contatos da plataforma."),
                 ]),
                ("💼", "Carteiras",
                 "Distribua contatos estrategicamente entre atendentes e equipes.",
                 [
                     ("🗂️", "Tipos de carteiras",
                      "Carteira Única vs Múltipla, quando usar cada uma."),
                     ("🆕", "Criar uma nova carteira",
                      "Como criar e configurar uma carteira de contatos."),
                     ("👤", "Incluir contato na carteira",
                      "Como adicionar contatos em uma carteira existente."),
                     ("✏️", "Alterar ou excluir uma carteira",
                      "Como editar ou remover carteiras quando necessário."),
                 ]),
                ("📊", "Painéis de Vendas",
                 "Kanban para gerenciar seu funil comercial com cards e etapas.",
                 [
                     ("🆕", "Criar e configurar um Painel de Vendas",
                      "Como criar seu primeiro funil de vendas com etapas personalizadas."),
                     ("📋", "Duplicação de Painel de Vendas",
                      "Como duplicar a estrutura de um painel para criar outros funis."),
                     ("🏆", "Marcar card como Ganho",
                      "Como registrar uma venda concluída com sucesso."),
                     ("❌", "Marcar card como Perda",
                      "Como registrar uma negociação perdida com motivo."),
                     ("🔍", "Filtros por Situação no CRM",
                      "Como filtrar cards por Em andamento, Ganho ou Perda."),
                     ("🗑️", "Exclusão segura de etapas do painel",
                      "Como excluir etapas do funil sem perder cards."),
                 ]),
            ],
        },
        {
            "icon": "🧩",
            "title": "Apps",
            "description": (
                "Módulos complementares da Persua: campanhas, chatbot, sequências, "
                "pagamentos, IA, mensagens agendadas e mais."
            ),
            "pages": [
                ("📣", "Campanhas",
                 "Envios em massa para suas listas de contatos.",
                 [
                     ("🎯", "Criar nova campanha",
                      "Como criar e disparar uma nova campanha."),
                     ("✉️", "Criar modelo de mensagem para campanha",
                      "Como criar modelos de mensagem do tipo campanha."),
                     ("📊", "Consultar campanha",
                      "Como consultar resultados e status das campanhas enviadas."),
                     ("📤", "Exportar campanha",
                      "Como exportar dados da campanha em formato planilha."),
                     ("📥", "Arquivar campanha",
                      "Como arquivar campanhas que não são mais necessárias."),
                     ("⚠️", "Riscos e custos da campanha",
                      "Entenda os riscos e custos antes de disparar uma campanha."),
                 ]),
                ("🤖", "Chatbot",
                 "Automação de respostas e fluxos conversacionais.",
                 [
                     ("🗂️", "Tipos de chatbot",
                      "Conheça os tipos disponíveis e suas aplicações."),
                     ("🛠️", "Criando um chatbot",
                      "Passo a passo para criar seu primeiro chatbot."),
                     ("💬", "Bloco Enviar Mensagem (chatbot)",
                      "Como usar o bloco de envio de mensagem no fluxo."),
                     ("❓", "Pergunta dinâmica (chatbot)",
                      "Como configurar perguntas que buscam opções via API externa."),
                 ]),
                ("🔄", "Sequências",
                 "Automações em sequência para follow up e reengajamento.",
                 [
                     ("🆕", "Criar sequência",
                      "Como criar uma nova sequência de mensagens."),
                     ("🎯", "Objetivo da sequência",
                      "Como definir o objetivo de uma sequência."),
                     ("➕", "Adicionar etapa",
                      "Como adicionar novas etapas em uma sequência."),
                     ("👤", "Incluir contato na sequência",
                      "Como adicionar contatos em uma sequência existente."),
                     ("👁️", "Visualizar contatos da sequência",
                      "Como consultar os contatos que estão em uma sequência."),
                     ("🏁", "Finalizar sequência",
                      "Como finalizar uma sequência manualmente."),
                     ("🔁", "Reiniciar sequência",
                      "Como reiniciar uma sequência para um contato."),
                     ("🚫", "Desabilitar ou excluir sequência",
                      "Como desabilitar temporariamente ou excluir uma sequência."),
                 ]),
                ("💰", "Pagamentos (App)",
                 "Cobrança direta pela plataforma via Asaas.",
                 [
                     ("⚡", "Ativar app de Pagamento",
                      "Como ativar o módulo de pagamentos na Persua."),
                     ("🏦", "Integrar com banco Asaas",
                      "Como conectar sua conta Asaas à Persua."),
                     ("🔍", "Consultar pagamento",
                      "Como consultar o status de pagamentos gerados."),
                     ("↩️", "Cancelar ou estornar pagamento",
                      "Como cancelar ou estornar pagamentos."),
                 ]),
                ("🧠", "IA, Agentes Inteligentes",
                 "Agentes de IA que conversam com seus clientes de forma inteligente.",
                 [
                     ("🆕", "Novo agente",
                      "Como criar seu primeiro agente de IA."),
                     ("⚙️", "Aba de configurações (Agentes IA)",
                      "Como configurar comportamento, regras e restrições do agente."),
                     ("🎓", "Habilidades do agente",
                      "Como adicionar habilidades ao agente (coletar dados, transferir, etc)."),
                     ("⌨️", "Simular tempo de digitação",
                      "Como humanizar o agente com tempo de digitação realista."),
                     ("💭", "Indicador de digitando",
                      "Como ativar o indicador de digitando durante a resposta."),
                     ("📌", "Versões dos agentes",
                      "Como gerenciar versões e testar mudanças antes de publicar."),
                 ]),
                ("⏰", "Mensagens Agendadas",
                 "Agende envios de mensagens para horários específicos.",
                 [
                     ("📋", "Modelo para mensagens agendadas",
                      "Como criar modelos específicos para mensagens agendadas."),
                     ("🗓️", "Como gerenciar os agendamentos",
                      "Como criar, editar e cancelar agendamentos."),
                     ("🔗", "Agendamentos pelo CRM",
                      "Como agendar mensagens a partir dos painéis do CRM."),
                 ]),
                ("💭", "Chat Interno",
                 "Comunicação interna da equipe dentro da plataforma.",
                 [
                     ("🔛", "Ativar e desativar funcionalidade (Chat Interno)",
                      "Como ativar o Chat Interno para sua equipe."),
                     ("👥", "Tipos de conversa (Usuário, Equipe, Todos)",
                      "Diferenças entre os tipos de conversa no Chat Interno."),
                 ]),
                ("👥", "Grupos do WhatsApp (App)",
                 "Ativação e gestão de grupos via Persua.",
                 [
                     ("⚡", "Habilitar app de Grupos",
                      "Como habilitar o módulo de Grupos do WhatsApp."),
                 ]),
                ("⏱️", "Tempo de Segurança",
                 "Janela de segurança antes do envio de mensagens.",
                 [
                     ("🔧", "Corrigir sincronização do Tempo de Segurança",
                      "Como resolver problemas de sincronização do Tempo de Segurança."),
                 ]),
                ("📡", "Distribuição de Atendimentos",
                 "Rodízio automático de conversas entre atendentes.",
                 [
                     ("⚙️", "Configuração da Distribuição de Atendimentos",
                      "Como configurar o rodízio e o transbordo."),
                 ]),
                ("🎙️", "Transcrição de Áudio com IA",
                 "Converte áudios recebidos em texto automaticamente.",
                 [
                     ("🎁", "Degustação de Transcrição de Áudio",
                      "Detalhes sobre o período de teste gratuito da transcrição."),
                 ]),
            ],
        },
        {
            "icon": "📊",
            "title": "Relatórios",
            "description": (
                "Acompanhe o desempenho do atendimento, "
                "produtividade da equipe e métricas de conversão."
            ),
            "pages": [
                ("📤", "Como exportar relatório",
                 "Como gerar arquivos XLS com dados de atendimento para análise."),
                ("💬", "Como exportar mensagens",
                 "Como exportar o histórico completo das conversas realizadas."),
                ("✅", "Como concluir atendimentos em massa",
                 "Como finalizar múltiplos atendimentos de uma só vez."),
                ("🖥️", "Consumo de infraestrutura",
                 "Como consultar o consumo de recursos da sua conta."),
            ],
        },
        {
            "icon": "⚙️",
            "title": "Ajustes",
            "description": (
                "Configurações gerais da plataforma: conta, equipes, integrações, "
                "modelos de mensagens e usuários."
            ),
            "pages": [
                ("🔧", "Conta",
                 "Configurações cadastrais, canais de atendimento e horário.",
                 [
                     ("❌", "Remover canal de atendimento",
                      "Como desconectar canais que não usa mais."),
                     ("🕐", "Horário de atendimento",
                      "Como configurar horários de funcionamento e resposta automática."),
                 ]),
                ("👥", "Equipes",
                 "Organização de equipes e regras de distribuição.",
                 [
                     ("🆕", "Cadastrar equipe",
                      "Como criar uma equipe e associar usuários."),
                     ("📡", "Distribuição e transbordo de atendimento",
                      "Como configurar rodízio automático entre membros da equipe."),
                     ("👨‍💼", "Tipo de associação Usuário x Supervisor",
                      "Diferenças entre associar como Usuário ou Supervisor."),
                 ]),
                ("🔌", "Integrações",
                 "Integre a Persua com ferramentas externas.",
                 [
                     ("🔗", "Botão do WhatsApp e Tag de rastreamento",
                      "Como instalar botão flutuante e tag de rastreamento no seu site."),
                     ("🔄", "Renovar token do Instagram e Messenger",
                      "Como renovar tokens quando a conexão expira."),
                     ("🎙️", "Transcrição de áudio (integração)",
                      "Configurações de transcrição de áudio no nível de integração."),
                 ]),
                ("📨", "Modelo de Mensagens",
                 "Templates aprovados pela Meta para iniciar conversas.",
                 [
                     ("🆕", "Cadastrar modelos de mensagem",
                      "Como cadastrar novos templates para aprovação da Meta."),
                     ("📝", "Como criar modelo de mensagem",
                      "Guia passo a passo de criação de modelos."),
                     ("✏️", "Editar modelos de mensagem",
                      "Como editar modelos sem precisar de nova aprovação."),
                     ("📊", "Marketing x Utilidade (modelos)",
                      "Quando usar cada categoria e como a Meta cobra cada uma."),
                 ]),
                ("👤", "Usuários",
                 "Gestão de usuários e níveis de acesso.",
                 [
                     ("📋", "Tipos de perfis de usuários",
                      "Administrador, Atendente e Atendente Restrito."),
                     ("➕", "Cadastrar usuários",
                      "Como cadastrar novos usuários na plataforma."),
                     ("🖼️", "Editar foto do usuário",
                      "Como alterar sua foto de perfil."),
                 ]),
            ],
        },
        {
            "icon": "❓",
            "title": "FAQ",
            "description": (
                "Respostas para as dúvidas mais comuns: erros frequentes, "
                "limitações técnicas, status de canais e muito mais."
            ),
            "pages": [
                ("🔒", "Número Privado (LID) e Unificação de Contatos",
                 "O que é o LID e como unificar contatos duplicados."),
                ("🟢", "Status de Integridade do Canal",
                 "Como interpretar o status de integridade do seu número."),
                ("⚡", "Rate Limit da API Não Oficial",
                 "Limites de velocidade de envio em conexões não oficiais."),
                ("⏳", "Mensagem Aguardando",
                 "O que significa mensagem aguardando e como resolver."),
                ("❌", "Códigos de Erros da Meta",
                 "Principais códigos de erro retornados pela Meta e como resolver."),
                ("🚫", "Solicitar revisão de banimento",
                 "Como solicitar revisão quando seu canal é bloqueado."),
                ("📸", "Mensagens do Instagram não chegam",
                 "O que fazer quando mensagens do Instagram não aparecem."),
                ("🆘", "Acessar página de suporte",
                 "Como acessar a página de suporte oficial."),
                ("📢", "Por que a Meta rejeita modelos de Marketing?",
                 "Principais causas de rejeição de modelos Marketing e como evitar."),
                ("📋", "Por que a Meta rejeita modelos de Utilidade?",
                 "Principais causas de rejeição de modelos Utilidade e como evitar."),
            ],
        },
    ],
}


# =============================================================================
# Funcoes de geracao de conteudo
# =============================================================================

def sanitize_filename(name: str) -> str:
    """Remove caracteres problematicos para filesystem/zip."""
    return name.replace("/", "-").replace(":", "")


def placeholder_content(icon: str, title: str, description: str) -> str:
    """Pagina ainda nao populada (nao tem draft)."""
    return f"""# {title}

{description}

---

:::info
**Pagina em desenvolvimento**

Esta pagina esta sendo preparada. Conteudo completo, passo a passo e imagens serao publicados em breve.
:::
"""


def section_parent_content(icon: str, title: str, description: str, pages: list) -> str:
    """Pagina pai de uma secao, com cards das sub-paginas."""
    cards = []
    for page in pages:
        p_icon = page[0]
        p_title = page[1]
        p_desc = page[2]
        cards.append(f"### {p_icon} {p_title}\n\n{p_desc}\n")
    cards_text = "\n".join(cards) if cards else "_Paginas desta secao serao adicionadas em breve._"

    return f"""# {title}

{description}

---

## Guias desta secao

{cards_text}
"""


def root_content(tree: dict) -> str:
    """Pagina raiz da Base de Conhecimento."""
    highlight_titles = ["Comece Aqui", "Conexão WhatsApp", "Atendimento", "Apps", "CRM", "FAQ"]
    highlight = [s for s in tree["sections"] if s["title"] in highlight_titles]
    others = [s for s in tree["sections"] if s["title"] not in highlight_titles]

    hl_cards = []
    for s in highlight:
        hl_cards.append(f"### {s['icon']} {s['title']}\n\n{s['description']}\n")
    hl_text = "\n".join(hl_cards)

    ot_cards = []
    for s in others:
        ot_cards.append(f"- {s['icon']} **{s['title']}**, {s['description']}")
    ot_text = "\n".join(ot_cards)

    return f"""# {tree['title']}

Sua empresa merece atendimento que não dorme. Aqui você aprende a fazer a Persua trabalhar por você 24 horas por dia, de configurar seu primeiro WhatsApp até rodar campanha com Inteligência Artificial.

Cada guia é um passo a passo real, com prints da plataforma, prontos para você seguir junto.

:::info
**É a sua primeira vez por aqui?** Abre a seção 👋 **Comece Aqui** no menu à esquerda. Em 10 minutos você está conectado e atendendo seu primeiro cliente.
:::

---

## Para ir direto ao ponto

{hl_text}

---

## Outros temas que você vai precisar

{ot_text}

---

Ficou com dúvida em algum tutorial? Fala com a gente pelo WhatsApp de suporte. A Persua é feita por gente que entende PME brasileira, e a gente responde rápido.
"""


def convert_drag_drop_to_markdown_images(content: str) -> str:
    """Converte marcadores drag-drop em markdown image syntax.

    Mantido por compatibilidade com o piloto conexao-whatsapp-cloud-api que
    usa os marcadores `[PRINT XX → arraste: path]`. Novos drafts gerados via
    convert_flw_to_persua.py ja vem com markdown image direto.
    """
    pattern_arraste = re.compile(r"\[PRINT\s+\d+\s*→\s*arraste:\s*([^\]]+?)\s*\]")
    content = pattern_arraste.sub(r"![](\1)", content)

    pattern_capturar = re.compile(r"\[PRINT\s+\d+\s*→\s*CAPTURAR NA PERSUA:\s*([^\]]+?)\s*\]")
    content = pattern_capturar.sub(
        r":::info\n📸 **Capturar na Persua:** \1\n:::",
        content,
    )

    return content


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# =============================================================================
# Build principal
# =============================================================================

def build():
    # Limpa staging
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    metadata_pages = {}
    populated_count = 0
    placeholder_count = 0

    def pos_key(idx: int) -> str:
        """Gera chave de position lexicografica: a, b, c, ... aa, ab..."""
        return chr(ord("a") + idx) if idx < 26 else "a" + chr(ord("a") + idx - 26)

    def enc_path(rel: str) -> str:
        return "/".join(urllib.parse.quote(s) for s in rel.split("/"))

    def content_for_page(icon: str, title: str, desc: str, has_subs: bool, subs: list | None = None) -> str:
        """Decide conteudo:
        1. Se existe draft -> usa draft
        2. Senao se tem subs -> gera section_parent
        3. Senao -> placeholder
        """
        nonlocal populated_count, placeholder_count
        draft = resolve_draft(title)
        if draft:
            raw = draft.read_text(encoding="utf-8")
            populated_count += 1
            return convert_drag_drop_to_markdown_images(raw)
        if has_subs and subs:
            return section_parent_content(icon, title, desc, subs)
        placeholder_count += 1
        return placeholder_content(icon, title, desc)

    # Raiz
    root_dir = STAGING / ROOT
    root_file = STAGING / f"{ROOT}.md"
    write_file(root_file, root_content(TREE))
    metadata_pages[urllib.parse.quote(f"{ROOT}.md")] = {"icon": TREE["icon"]}

    for sec_idx, section in enumerate(TREE["sections"]):
        sec_title = section["title"]
        sec_icon = section["icon"]
        sec_file = root_dir / f"{sec_title}.md"
        write_file(sec_file, section_parent_content(sec_icon, sec_title, section["description"], section["pages"]))
        rel = f"{ROOT}/{sec_title}.md"
        metadata_pages[enc_path(rel)] = {
            "icon": sec_icon,
            "position": pos_key(sec_idx),
        }

        if not section["pages"]:
            continue

        sec_dir = root_dir / sec_title
        for p_idx, page in enumerate(section["pages"]):
            p_icon = page[0]
            p_title = page[1]
            p_desc = page[2]
            has_subs = len(page) >= 4 and page[3]
            subs = page[3] if has_subs else None

            content = content_for_page(p_icon, p_title, p_desc, has_subs, subs)

            p_file = sec_dir / f"{p_title}.md"
            write_file(p_file, content)
            rel = f"{ROOT}/{sec_title}/{p_title}.md"
            metadata_pages[enc_path(rel)] = {
                "icon": p_icon,
                "position": pos_key(p_idx),
            }

            if has_subs:
                sub_dir = sec_dir / p_title
                for s_idx, sub in enumerate(subs):
                    s_icon = sub[0]
                    s_title = sub[1]
                    s_desc = sub[2]
                    sub_content = content_for_page(s_icon, s_title, s_desc, False, None)
                    s_file = sub_dir / f"{s_title}.md"
                    write_file(s_file, sub_content)
                    rel = f"{ROOT}/{sec_title}/{p_title}/{s_title}.md"
                    metadata_pages[enc_path(rel)] = {
                        "icon": s_icon,
                        "position": pos_key(s_idx),
                    }

    # Metadata JSON
    metadata = {
        "source": "docmost",
        "pages": metadata_pages,
    }
    (STAGING / "docmost-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Copia assets com overlay _persua/
    persua_used = []
    flw_pending = []
    per_tutorial = {}

    if ASSETS_SRC.exists():
        for slug_dir in sorted(ASSETS_SRC.iterdir()):
            if not slug_dir.is_dir():
                continue

            slug = slug_dir.name
            per_tutorial.setdefault(slug, {"persua": 0, "flw": 0})
            persua_overlay = slug_dir / "_persua"

            flw_imgs = []
            for pattern in IMG_EXTS:
                flw_imgs.extend(slug_dir.glob(pattern))

            for flw_img in sorted(flw_imgs):
                fname = flw_img.name
                persua_img = persua_overlay / fname
                dest = STAGING / "assets" / slug / fname
                dest.parent.mkdir(parents=True, exist_ok=True)

                if persua_img.exists():
                    shutil.copy2(persua_img, dest)
                    persua_used.append(f"{slug}/{fname}")
                    per_tutorial[slug]["persua"] += 1
                else:
                    shutil.copy2(flw_img, dest)
                    flw_pending.append(f"{slug}/{fname}")
                    per_tutorial[slug]["flw"] += 1

    # Zipa
    OUT_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(STAGING):
            for f in files:
                abs_path = Path(root) / f
                rel = abs_path.relative_to(STAGING)
                zf.write(abs_path, rel)

    # Relatorio
    total_md = sum(1 for p in STAGING.rglob("*.md"))
    total_imgs = sum(1 for p in STAGING.rglob("*") if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"))
    total_icons = len(metadata_pages)
    zip_size_kb = OUT_ZIP.stat().st_size // 1024

    print(f"ZIP gerado: {OUT_ZIP}")
    print(f"Tamanho: {zip_size_kb} KB")
    print(f"Paginas (.md): {total_md}")
    print(f"Imagens: {total_imgs}")
    print(f"Icones mapeados em metadata: {total_icons}")
    print(f"Paginas populadas (draft): {populated_count}")
    print(f"Paginas placeholder: {placeholder_count}")

    # Relatorio overlay _persua/
    total_assets = len(persua_used) + len(flw_pending)
    if total_assets:
        pct = (len(persua_used) * 100) // total_assets if total_assets else 0
        print()
        print(f"Overlay _persua/: {len(persua_used)} Persua / {len(flw_pending)} flw pendentes ({pct}% Persua)")
        tutorials_with_persua = {s: st for s, st in per_tutorial.items() if st["persua"] > 0}
        if tutorials_with_persua:
            print("Tutoriais com Persua ativo:")
            for slug, stats in tutorials_with_persua.items():
                total_slug = stats["persua"] + stats["flw"]
                status = "OK" if stats["flw"] == 0 else "pendente"
                print(f"  - {slug}: {stats['persua']}/{total_slug} Persua [{status}]")


if __name__ == "__main__":
    build()
