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
- [Modelo de Dados](docs/data_model.md)
- [Privacidade](docs/privacy.md)
- [Roadmap](docs/roadmap.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Checklist de Publicação Git](docs/git_publication_checklist.md)

## 🌍 English

English documentation available in [README.md](README.md).

## Licença

Este projeto está licenciado sob a licença MIT. Veja [LICENSE](LICENSE).
