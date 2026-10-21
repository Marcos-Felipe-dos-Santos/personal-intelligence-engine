# PIE — Personal Intelligence Engine

![CI](https://github.com/Marcos-Felipe-dos-Santos/personal-intelligence-engine/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Uma engine **local-first** para captura, estruturação e projeção de conhecimento pessoal.

O PIE captura entradas de texto desestruturadas, extrai dados estruturados, valida com Pydantic, persiste tudo em um banco SQLite local, e gera notas Markdown legíveis e relatórios.

## Status

O PIE Core é um software alpha experimental com fluxo local pela CLI para captura, revisão humana, busca, relatórios e recuperação. Está preparado para iniciar um piloto controlado com dados sintéticos; a camada de assistente ainda não está implementada.

A validação local em Windows com Python 3.13 passou com **405 testes**, Ruff, compilação e teste de instalação por wheel fora do repositório. O CI está configurado para Windows e Ubuntu com Python 3.10 a 3.13. A qualidade de um modelo Ollama real e o piloto de sete dias ainda precisam de validação. Comece pelo [checklist de teste controlado](docs/test_readiness.pt-BR.md).

## Privacidade Primeiro

O PIE pode armazenar dados pessoais sensíveis em bancos SQLite locais, notas Markdown, relatórios e audit logs. Não publique `pie.db`, `notes/`, `reports/`, `.env`, logs ou dados locais gerados no Git. Os exemplos do repositório são sintéticos.

## ✨ Funcionalidades

- 📝 **Captura** — Adicione entradas de texto via CLI
- 🔍 **Extração** — Classificação heurística por palavras-chave e adapter Ollama local opcional
- ✅ **Validação** — Schemas Pydantic com pontuação de confiança
- 💾 **Persistência** — SQLite como fonte de verdade única
- 📄 **Projeção** — Notas Markdown com frontmatter YAML
- 📊 **Relatórios** — Relatórios diários, semanais, por projeto, decisões e tarefas candidatas
- ✅ **Revisão humana** — Aprovação, rejeição e edição com histórico de alterações
- 🛠️ **Recuperação** — Retomada de capturas com falha e reconstrução de notas a partir do banco
- 🔒 **Auditoria** — Rastreabilidade completa via audit logs
- 🏠 **Local-first** — Sem nuvem obrigatória ou telemetria; Ollama remoto bloqueado por padrão
- 🔎 **Busca** — Busca textual local em todas as entradas

## 🚀 Início Rápido

### Instalação

Requer Python 3.10 ou superior. No Windows, a instalação inclui `tzdata` para os fusos horários IANA. Crie o ambiente virtual nesta máquina; ambientes virtuais copiados de outra instalação devem ser recriados.

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

### Definir a pasta dos dados

Antes de capturar entradas, defina uma raiz fixa. No PowerShell:

```powershell
$env:PIE_HOME = Join-Path $env:USERPROFILE '.pie'
pie doctor
```

No Linux/macOS:

```bash
export PIE_HOME="$HOME/.pie"
pie doctor
```

Sem `PIE_HOME`, os caminhos relativos usam a pasta atual e executar o PIE em outra pasta pode selecionar outro banco. Caminhos absolutos definidos em `PIE_DATABASE_PATH`, `PIE_NOTES_DIR`, `PIE_REPORTS_DIR`, `PIE_BACKUP_DIR` e `PIE_EXPORT_DIR` têm precedência sobre essa raiz. Confira os caminhos exibidos por `doctor`. Para o primeiro ensaio isolado, use os comandos do [checklist](docs/test_readiness.pt-BR.md).

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
   Confidence:    60%
   Validation:    needs_review
   Note:          notes/e5f6g7h8-....md
```

O `FakeExtractor` usa regras determinísticas; a confiança não representa probabilidade de acerto. Use `--project`, `--type` e `--tag` para informar campos explicitamente e revise entradas com `needs_review`.

#### Revisar e editar entradas

```bash
pie review list
pie review show <structured_entry_id>
pie review approve <structured_entry_id>
pie review reject <structured_entry_id>
pie review edit <structured_entry_id> --summary "Resumo corrigido" --project PIE
pie review history <structured_entry_id>
```

A revisão mantém o texto bruto original. Edições registram a versão anterior e a nova, e aprovação, rejeição e edição atualizam a nota Markdown. Para limpar o projeto, use `--project " "`, que também funciona em terminais que descartam argumentos vazios.

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

Gera um relatório Markdown da semana local que contém a data especificada (de segunda a domingo), agrupando as entradas por tipo e status de validação.

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

Gera um relatório Markdown com entradas associadas ao nome exato do projeto especificado.

Saída:
```
[OK] Project report generated!
   Report ID:    p7q8r9s0-...
   Project:      PIE
   Entries:      12
   File:         reports/project_PIE.md
```

Os relatórios são salvos em `reports/`, citam IDs de entradas estruturadas/brutas usadas como fonte e são ignorados pelo Git.

Também há relatórios focados:

```bash
pie report decisions --project PIE --since 2026-01-01
pie report tasks --project PIE
```

O relatório de tarefas reúne entradas `candidate_task` com validação `valid` ou `needs_review`. Ainda não há um ciclo de conclusão de tarefas.

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

Backups SQLite e exportações JSON são snapshots completos do banco e podem incluir entradas soft-deleted. A exportação Markdown é um resumo legível de entradas ativas e exclui entradas soft-deleted.

#### Excluir e restaurar entradas

```bash
pie entries delete <structured_entry_id>
pie entries restore <structured_entry_id>
pie entries purge --older-than 30
```

`delete` faz exclusão lógica reversível; `purge` remove definitivamente entradas excluídas há mais que o prazo informado e solicita confirmação. Backups, exportações e relatórios antigos podem conservar cópias do conteúdo.

#### Recuperar capturas e notas

```bash
pie entries failed
pie entries retry <raw_entry_id>
pie entries rebuild-note <structured_entry_id>
```

`failed` lista IDs de entradas brutas pendentes/com erro que ainda não têm estruturação, sem mostrar seu conteúdo. `retry` retoma a extração preservando o texto e o ID originais. `rebuild-note` reconstrói a nota a partir do SQLite sem executar a extração novamente.

Quando uma edição, revisão ou reprocessamento salva o banco mas falha ao escrever a nota, a CLI mostra um aviso e o comando de reconstrução. No lote, essa entrada conta como aplicada, com a nota pendente de recuperação.

As migrações SQL são transacionais, incluindo o registro da versão e a verificação de integridade referencial. `pie doctor` informa migrações pendentes sem aplicá-las; as operações normais aplicam migrações ao inicializar.

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
> Recomenda-se fortemente realizar um backup do banco de dados (ex: `pie backup create`) antes de executar o reprocessamento. O reprocessamento salva revisões no banco e regenera a nota Markdown de cada entrada reprocessada. A regeneração da nota ocorre após o commit no banco; se a escrita do arquivo falhar, a CLI informa que o banco foi atualizado, avisa que a nota está desatualizada e exibe o comando `pie entries rebuild-note <id>` para recuperá-la.
>
> O reprocessamento em lote usa transação por entrada, não all-or-nothing para o lote inteiro. Se uma entrada falhar antes do commit no banco, suas alterações sofrem rollback, enquanto entradas anteriores permanecem aplicadas. Falhas posteriores na escrita da nota são informadas separadamente e não desfazem os dados salvos. A saída do comando mostra total selecionado, total aplicado, total com falha, IDs aplicados, IDs com falha e erro resumido por ID com falha. `raw_entries.content` nunca é editado pelo reprocessamento.

### Extração local com LLM opcional

O PIE usa o `FakeExtractor` determinístico por padrão. Ele não exige Ollama, APIs de nuvem, nem qualquer serviço externo.

Para manter o comportamento padrão:

```bash
export PIE_EXTRACTOR_BACKEND=fake
```

O suporte experimental a Ollama está disponível como adapter local opcional:

```bash
export PIE_EXTRACTOR_BACKEND=ollama
export PIE_OLLAMA_BASE_URL=http://localhost:11434
export PIE_OLLAMA_MODEL='seu-modelo-instalado'
export PIE_LLM_TIMEOUT_SECONDS=30
export PIE_LLM_MAX_RETRIES=2
export PIE_LLM_RETRY_BACKOFF_SECONDS=1
```

No PowerShell, use `$env:PIE_EXTRACTOR_BACKEND = 'ollama'`, `$env:PIE_OLLAMA_MODEL = 'seu-modelo-instalado'` e a mesma sintaxe `$env:NOME = 'valor'` para as demais opções.

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
pie evaluate extraction --backend fake --min-score 0.8
```

`--min-score` retorna erro quando a média sintética fica abaixo do limite, preservando o relatório caso `--output` seja informado. Na avaliação atual, o `FakeExtractor` tem média aproximada de 52,26% e nenhum dos nove casos atinge o corte de 80%; portanto, o último comando deve falhar. A pontuação é lexical, inclui expectativas de confiança diferentes da calibração heurística e não mede precisão semântica.

Veja [docs/troubleshooting.md](docs/troubleshooting.md) para health check do Ollama, configuração de retry e mensagens de erro comuns.

### Executar Testes

```bash
python -m pytest -q
python -m ruff check .
python -m compileall -q personal_intelligence_engine
```

Os testes usam pastas temporárias e bloqueiam o carregamento de configuração local. Para validar também o pacote instalado:

```bash
python -m pip wheel . --no-deps --wheel-dir dist
python tests/smoke_installed_wheel.py dist/personal_intelligence_engine-0.1.0-py3-none-any.whl
```

Migrações, prompt e casos sintéticos de avaliação são incluídos no wheel. O smoke verifica captura, busca, relatório, backup, exportação e avaliação fora da pasta do código-fonte.

## 📁 Estrutura do Projeto

```
personal-intelligence-engine/
├── personal_intelligence_engine/
│   └── app/
│       ├── main.py           # Orquestrador da aplicação
│       ├── config.py         # Configuração
│       ├── cli/              # Comandos Click
│       ├── domain/           # Schemas Pydantic e enums
│       ├── services/         # Lógica de negócio
│       ├── repositories/     # Persistência SQLite
│       ├── adapters/         # Extratores e escrita Markdown
│       ├── migrations/       # Migrações SQL incluídas no pacote
│       ├── prompts/          # Prompt versionado do LLM
│       └── evaluation/       # Avaliação, relatórios e casos sintéticos
├── tests/                    # Testes unitários, integração e smoke do wheel
├── docs/                     # Arquitetura, privacidade e roteiros de teste
├── examples/                 # Exemplos sintéticos
└── pyproject.toml
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
- [Preparação para Teste Controlado](docs/test_readiness.pt-BR.md)
- [Guia de Uso de 7 Dias](docs/usage_playbook.md)
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
