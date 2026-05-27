# PIE — Personal Intelligence Engine

![CI](https://github.com/Marcos-Felipe-dos-Santos/personal-intelligence-engine/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Uma engine **local-first** para captura, estruturação e projeção de conhecimento pessoal.

O PIE captura entradas de texto desestruturadas, extrai dados estruturados, valida com Pydantic, persiste tudo em um banco SQLite local, e gera notas Markdown legíveis e relatórios.

## Status

O PIE é um software alpha experimental. Nesta fase, ele é voltado para desenvolvimento local e exemplos sintéticos, não para uso como produto de privacidade finalizado.

## Privacidade Primeiro

O PIE pode armazenar dados pessoais sensíveis em bancos SQLite locais, notas Markdown, relatórios e audit logs. Não publique `pie.db`, `notes/`, `reports/`, `.env`, logs ou dados locais gerados no Git. Os exemplos do repositório são sintéticos.

## ✨ Funcionalidades

- 📝 **Captura** — Adicione entradas de texto via CLI
- 🔍 **Extração** — Classificação automática por palavras-chave (arquitetura pronta para LLM)
- ✅ **Validação** — Schemas Pydantic com pontuação de confiança
- 💾 **Persistência** — SQLite como fonte de verdade única
- 📄 **Projeção** — Notas Markdown com frontmatter YAML
- 📊 **Relatórios** — Relatórios diários com resumo de entradas
- 🔒 **Auditoria** — Rastreabilidade completa via audit logs
- 🏠 **Local-first** — Sem nuvem, sem APIs externas, sem telemetria
- 🔎 **Busca** — Busca textual local em todas as entradas

## 🚀 Início Rápido

### Instalação

```bash
# Clone o repositório
git clone https://github.com/Marcos-Felipe-dos-Santos/personal-intelligence-engine.git
cd personal-intelligence-engine

# Crie o ambiente virtual
python -m venv .venv

# Ative (Windows)
.venv\Scripts\activate

# Ative (Linux/macOS)
source .venv/bin/activate

# Instale em modo desenvolvimento
pip install -e ".[dev]"
```

### Uso

#### Adicionar uma entrada

```bash
pie add "Eu decidi usar SQLite para o projeto"
```

Saída:
```
✅ Entry created successfully!
   Entry ID:      a1b2c3d4-...
   Structured ID: e5f6g7h8-...
   Type:          decision
   Confidence:    85%
   Validation:    valid
   Note:          notes/e5f6g7h8-....md
```

#### Gerar relatório diário

```bash
pie report daily --date 2026-05-09
```

`--date` é interpretado como um dia local de calendário. Os timestamps continuam armazenados em UTC, e o timezone local padrão é `America/Sao_Paulo`. Configure `PIE_LOCAL_TIMEZONE` com outro timezone IANA se necessário.

Saída:
```
📊 Daily report generated!
   Report ID:    i9j0k1l2-...
   Date:         2026-05-09
   Entries:      3
   File:         reports/daily_2026-05-09.md
```

#### Gerar relatório semanal

```bash
pie report weekly --date 2026-05-26
```

Gera um relatório Markdown da semana que contém a data especificada (de segunda a domingo), agrupando as entradas por tipo e status de validação.

Saída:
```
[OK] Weekly report generated!
   Report ID:    w3x4y5z6-...
   Start Date:   2026-05-25
   End Date:     2026-05-31
   Entries:      8
   File:         reports/weekly_2026-05-25_to_2026-05-31.md
```

#### Gerar relatório de projeto

```bash
pie report project --project PIE
```

Gera um relatório Markdown com todas as entradas associadas ao projeto especificado.

Saída:
```
[OK] Project report generated!
   Report ID:    p7q8r9s0-...
   Project:      PIE
   Entries:      12
   File:         reports/project_PIE.md
```

#### Listar entradas

```bash
pie entries list
pie entries list --type decision
pie entries list --project PIE --limit 10
pie entries list --status needs_review
```

#### Ver detalhes de uma entrada

```bash
pie entries show <structured_entry_id>
```

#### Buscar entradas

```bash
pie search "SQLite"
pie search "SQLite" --type decision
pie search "pipeline" --project PIE
pie search "review" --status needs_review
```

A busca procura texto no conteúdo bruto, resumo, projeto e JSON estruturado (incluindo tags). Os resultados mostram um snippet curto e a origem do match.

#### Backup e Exportação

```bash
# Criar backup do banco de dados local
pie backup create

# Exportar tabelas em formato JSON
pie export json

# Exportar resumo de entradas estruturadas agrupadas por tipo em Markdown
pie export markdown
```

Os backups são salvos em `backups/` e as exportações em `exports/` (ambos diretórios são ignorados pelo Git). Esses diretórios são configuráveis via `PIE_BACKUP_DIR` e `PIE_EXPORT_DIR`.

#### Reprocessando Entradas Armazenadas

```bash
# Visualizar alterações para uma entrada específica (dry-run)
pie entries reprocess <structured_entry_id> --dry-run

# Reprocessar uma entrada específica e aplicar alterações
pie entries reprocess <structured_entry_id>

# Visualizar alterações para entradas com status needs_review (dry-run)
pie entries reprocess --status needs_review --dry-run --limit 5

# Reprocessar entradas com status needs_review e aplicar alterações
pie entries reprocess --status needs_review
```

> [!IMPORTANT]
> Recomenda-se fortemente realizar um backup do banco de dados (ex: `pie backup create`) antes de executar o reprocessamento. O reprocessamento salva revisões no banco, mas não atualiza automaticamente arquivos de notas Markdown em `notes/`.
>
> O reprocessamento em lote usa transação por entrada, não all-or-nothing para o lote inteiro. Se uma entrada falhar, ela sofre rollback completo, enquanto entradas anteriores processadas com sucesso permanecem aplicadas. A saída do comando mostra total selecionado, total aplicado, total com falha, IDs aplicados, IDs com falha e erro resumido por ID com falha. `raw_entries.content` nunca é editado pelo reprocessamento.

### Extração local com LLM opcional

O PIE usa o `FakeExtractor` determinístico por padrão. Ele não exige Ollama, APIs de nuvem, nem qualquer serviço externo.

Para manter o comportamento padrão:

```bash
PIE_EXTRACTOR_BACKEND=fake
```

O suporte experimental a Ollama está disponível como adapter local opcional:

```bash
PIE_EXTRACTOR_BACKEND=ollama
PIE_OLLAMA_BASE_URL=http://localhost:11434
PIE_OLLAMA_MODEL=<seu-modelo-local>
PIE_LLM_TIMEOUT_SECONDS=30
PIE_LLM_MAX_RETRIES=2
PIE_LLM_RETRY_BACKOFF_SECONDS=1
```

Depois execute:

```bash
pie add "Eu decidi testar a extração local com Ollama"
```

Se o Ollama não estiver rodando ou o modelo não estiver configurado, o PIE mostra um erro claro e não faz fallback silencioso para o `FakeExtractor`.

Verifique o extractor configurado sem criar entrada:

```bash
pie doctor
```

Execute a avaliação sintética de qualidade da extração sem criar entradas no banco:

```bash
pie evaluate extraction --backend fake
pie evaluate extraction --backend fake --output reports/evaluation/fake.md
```

Veja [docs/troubleshooting.md](docs/troubleshooting.md) para health check do Ollama, configuração de retry e mensagens de erro comuns.

### Executar Testes

```bash
python -m pytest -q
```

## 📁 Estrutura do Projeto

```
personal_intelligence_engine/
├── app/
│   ├── main.py              # Orquestrador da aplicação
│   ├── config.py             # Gerenciamento de configuração
│   ├── domain/
│   │   ├── schemas.py        # Modelos Pydantic
│   │   └── types.py          # Enums e constantes
│   ├── services/             # Camada de lógica de negócio
│   ├── adapters/             # Implementações intercambiáveis
│   │   ├── fake_extractor.py # Extrator determinístico
│   │   └── markdown_writer.py
│   ├── repositories/         # Camada de acesso a dados
│   │   └── database.py       # Gerenciamento SQLite
│   └── cli/
│       └── commands.py       # Comandos CLI com Click
├── migrations/
│   └── 001_initial_schema.sql
├── tests/
├── docs/
│   ├── architecture.md
│   ├── privacy.md
│   ├── data_model.md
│   └── roadmap.md
└── examples/
```

## 🔑 Decisões Arquiteturais

| Decisão | Justificativa |
|---------|---------------|
| SQLite | Simples, portátil, sem servidor |
| Pydantic | Validação forte com mensagens claras |
| Click | Framework CLI limpo com boa UX |
| FakeExtractor | Testes determinísticos sem dependência de LLM |
| Markdown como projeção | Saída legível, não é fonte de verdade |
| UUID strings | Identificadores portáteis e resistentes a colisão |
| Audit log | Rastreabilidade total para debug e confiança |

## 🔒 Privacidade

Os dados de runtime ficam na sua máquina por desenho, mas arquivos locais ficam em texto claro se o sistema operacional não os proteger. Leia [docs/privacy.md](docs/privacy.md) antes de usar dados pessoais reais.

## 📋 Roadmap

Veja [docs/roadmap.md](docs/roadmap.md) para o plano completo de desenvolvimento.

## 📖 Documentação

- [Arquitetura](docs/architecture.md)
- [Estado Atual](docs/current_state.md)
- [Visão](docs/vision.md)
- [Arquitetura da Assistant Layer](docs/assistant_architecture.md)
- [Modelo de Dados](docs/data_model.md)
- [Gap Analysis do Core v1](docs/core_v1_gap_analysis.md)
- [Privacidade](docs/privacy.md)
- [Roadmap](docs/roadmap.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Checklist de Publicação Git](docs/git_publication_checklist.md)

## 🌍 English

English documentation available in [README.md](README.md).

## Licença

Este projeto está licenciado sob a licença MIT. Veja [LICENSE](LICENSE).
