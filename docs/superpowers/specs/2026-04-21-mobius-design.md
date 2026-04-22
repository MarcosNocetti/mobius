# Mobius — Design Spec
**Data:** 2026-04-21  
**Status:** Aprovado

---

## Visão Geral

Mobius é um assistente de produtividade mobile com IA que permite ao usuário conversar com modelos de linguagem e executar ações reais — postar em redes sociais, criar eventos, enviar emails, automatizar o próprio celular — tudo a partir de um app Android/iOS.

O produto é diferenciado por ser **orientado a execução**: diferente de chats de IA que só geram texto, o Mobius age. O usuário diz o que quer, o agente planeja e executa.

**Público-alvo:** Híbrido — interface simples o suficiente para usuários leigos, com profundidade para power users que queiram customizar modelos, servidores e automações avançadas.

---

## Arquitetura

O sistema é dividido em dois repositórios independentes:

```
mobius/
├── mobius-server/   # Backend FastAPI
└── mobius-app/      # App Flutter
```

### Princípio fundamental
**O app é thin client.** Todo raciocínio de IA, orquestração e chamadas a APIs externas ficam no backend. O app renderiza, captura input do usuário e executa ações de acessibilidade no dispositivo. Nenhuma lógica pesada roda no celular.

### Diagrama

```
┌─────────────────────────────────────────────────────┐
│                   Flutter App                        │
│  Chat UI · Histórico · Config · Device Automation   │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS + WebSocket
┌──────────────────────▼──────────────────────────────┐
│              Mobius Backend (FastAPI)                 │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ AI Orchestr.│  │ Integrations │  │   Auth &   │  │
│  │ LiteLLM     │  │ Google·Notion│  │   Users    │  │
│  │ Claude·GPT  │  │ Instagram·X  │  │            │  │
│  └─────────────┘  └──────────────┘  └────────────┘  │
└──────────────────────────────────────────────────────┘
         Roda localmente (Docker) → deploy na nuvem
```

---

## Backend — mobius-server

### Stack
- **Framework:** FastAPI (Python)
- **Banco de dados:** PostgreSQL
- **Cache / filas:** Redis
- **Agente:** LangGraph
- **IA:** LiteLLM (abstração unificada de modelos)
- **Deploy:** Docker Compose (local no MVP, cloud-ready)

### Estrutura de diretórios

```
mobius-server/
├── app/
│   ├── api/          # Rotas REST + WebSocket
│   ├── agents/       # Orquestração LangGraph + definição de ferramentas
│   ├── integrations/ # Um módulo por serviço externo
│   ├── models/       # Schemas Pydantic + ORM (SQLAlchemy)
│   └── core/         # Config, auth, conexão DB
├── docker-compose.yml
└── .env
```

### Componentes

**Agent Engine (LangGraph)**  
Recebe a mensagem do usuário e executa um loop de raciocínio: analisa o pedido, seleciona ferramentas, executa em sequência e reporta progresso em tempo real via WebSocket. Usa function calling nativo do modelo — sem frameworks adicionais além do LangGraph.

**LiteLLM**  
Camada unificada que abstrai Claude, GPT-4o e Gemini. O usuário pode operar com o modelo gratuito padrão (Gemini 2.0 Flash) ou trazer sua própria API key para acessar modelos premium.

**Integration Services**  
Um módulo isolado por serviço externo. Cada módulo gerencia OAuth, refresh de tokens e as chamadas específicas da API. Tokens OAuth são armazenados no Redis com TTL.

**Auth**  
JWT para autenticação do app com o backend. No MVP (single-user, servidor local), o fluxo de registro é simplificado.

### Comunicação com o app
- **REST:** autenticação, configurações, listagem de histórico
- **WebSocket:** streaming de respostas da IA e progresso de execução de tarefas em tempo real

---

## Agent Engine — Ferramentas do MVP

Fluxo de execução:

```
Usuário: "Posta no Instagram uma foto do meu último projeto"
         ↓
    Agent Engine (LangGraph)
         ↓
    Plano: [get_last_project_info] → [generate_caption] → [post_instagram]
         ↓
    Executa ferramentas, emite progresso via WebSocket
         ↓
Usuário vê: "Buscando projeto... ✓  Gerando legenda... ✓  Postando... ✓"
```

| Categoria | Ferramentas |
|---|---|
| Redes sociais | `post_instagram`, `post_twitter`, `post_linkedin` |
| Produtividade | `create_calendar_event`, `send_gmail`, `create_notion_page` |
| Dispositivo | `open_app`, `take_screenshot`, `read_screen` |
| Utilitários | `web_search`, `summarize`, `generate_image_caption` |

### Modelos suportados no MVP

| Modelo | Acesso |
|---|---|
| Gemini 2.0 Flash | Gratuito, padrão |
| Claude Sonnet | API key própria |
| GPT-4o | API key própria |
| Gemini Pro | API key própria |

---

## App Flutter — mobius-app

### Stack
- **Framework:** Flutter (Dart)
- **Plataformas MVP:** Android (iOS na fase 2)
- **Comunicação:** HTTP + WebSocket via `dart:io` / `web_socket_channel`

### Estrutura de diretórios

```
mobius-app/
├── lib/
│   ├── screens/
│   │   ├── chat/          # Tela principal de conversa
│   │   ├── automations/   # Rotinas salvas e agendamento
│   │   ├── integrations/  # Gerenciar OAuth de serviços
│   │   └── settings/      # Servidor, modelo de IA, API keys
│   ├── services/
│   │   ├── backend_client.dart   # HTTP + WebSocket
│   │   ├── device_agent.dart     # Automação via Accessibility Services
│   │   └── notification.dart     # Feedback de tarefas em background
│   └── widgets/
```

### Telas do MVP

**Chat** — Tela principal. Streaming de respostas da IA, bolhas de mensagem, indicador de "IA pensando", cards de resultado inline (ex: "Postagem publicada ✓"). Histórico persistido no backend.

**Automações** — Lista de rotinas salvas. O usuário cria um fluxo via chat e salva para execução agendada (ex: "Todo dia às 9h postar resumo no LinkedIn").

**Integrações** — Conectar e desconectar serviços externos. Status de conexão visível (ativo / expirado / erro).

**Configurações** — URL do servidor Mobius, escolha de modelo de IA, campo para API keys próprias.

### Device Automation (Android)
Usa Android Accessibility Services para abrir apps, clicar em elementos, preencher campos e ler conteúdo da tela. O app solicita permissão de acessibilidade na primeira execução.

**iOS:** Limitado a Shortcuts API e ações in-app. Implementação completa na fase 2.

---

## Integrações do MVP

| Serviço | Ações |
|---|---|
| Instagram | Publicar foto/vídeo/story |
| Twitter/X | Postar tweet, responder |
| LinkedIn | Publicar post |
| Google Calendar | Criar/listar eventos |
| Gmail | Enviar email, ler inbox resumida |
| Notion | Criar página, adicionar a banco de dados |

Todas as integrações usam OAuth 2.0. O backend gerencia o fluxo completo; o app só exibe o status de conexão.

---

## Deploy

### MVP (local)
```bash
# No servidor local (ex: Raspberry Pi / PC em casa)
cd mobius-server
docker-compose up

# No .env do app
MOBIUS_SERVER_URL=http://192.168.x.x:8000
```

### Cloud (fase de lançamento)
O mesmo `docker-compose.yml` é compatível com Railway, Fly.io ou qualquer VPS. Única mudança: variáveis de ambiente e domínio HTTPS.

---

## Escopo do MVP

### Dentro
- Chat em tempo real com streaming
- Modelos: Gemini Flash (grátis) + Claude / GPT-4o (API key)
- Post em Instagram, Twitter/X, LinkedIn
- Google Calendar, Gmail, Notion
- Device automation no Android
- Rotinas agendadas
- App configurável para apontar para servidor local

### Fora (fase 2+)
- iOS device automation
- Criar sites / landing pages
- Automação de likes/comentários em massa
- Marketplace de automações
- Multi-usuário / times
- Publicação em lojas (App Store / Play Store)

---

## Fases de Desenvolvimento

**Fase 1 — MVP**
1. Backend: estrutura base, auth, WebSocket, Agent Engine com Gemini Flash
2. App: Chat com streaming, tela de configurações/servidor
3. Integração: Google Calendar + Gmail
4. Integração: Twitter/X
5. Integração: Instagram + LinkedIn + Notion
6. Device automation Android
7. Rotinas agendadas

**Fase 2**
- iOS automation
- Publicação nas lojas
- Multi-usuário
- Deploy cloud

---

## Decisões de Design

| Decisão | Escolha | Motivo |
|---|---|---|
| Mobile stack | Flutter | Performance, único código Android+iOS, bom suporte a Accessibility Services |
| Backend | FastAPI | Equipe conhece Python, async nativo, ótimo pra WebSocket |
| IA | LiteLLM | Abstrai múltiplos provedores sem lock-in |
| Agente | LangGraph | Orquestração multi-step sem overhead excessivo |
| Deploy MVP | Docker local | Cloud-ready desde o início, sem custo de infra no MVP |
