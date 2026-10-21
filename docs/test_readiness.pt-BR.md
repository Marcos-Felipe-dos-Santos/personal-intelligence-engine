# Preparação para teste controlado do PIE Core

O escopo liberado é o fluxo local pela CLI: captura, revisão, busca, relatórios,
backup/exportação e recuperação. O extrator padrão é heurístico e exige revisão
humana. A camada de assistente e a qualidade de um modelo Ollama real ainda
precisam de validação própria.

## Verificação técnica

Na raiz do projeto, no PowerShell:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m compileall -q personal_intelligence_engine
.venv\Scripts\python.exe -m pip wheel . --no-deps --wheel-dir dist
.venv\Scripts\python.exe tests/smoke_installed_wheel.py dist/personal_intelligence_engine-0.1.0-py3-none-any.whl
```

Os testes bloqueiam o carregamento de configuração local e executam os fluxos
em diretórios temporários. O smoke instala o wheel em uma pasta temporária e
confere migrações, prompt, comandos, relatórios, backup, exportação e avaliação
fora do repositório. O CI executa essas verificações no Windows e Ubuntu com
Python 3.10 a 3.13.

## Base separada para o piloto

Abra um terminal novo na raiz do projeto. Os comandos abaixo criam uma base
temporária e selecionam o extrator determinístico. Todos os caminhos são
definidos explicitamente para evitar configurações herdadas.

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:PIE_HOME = Join-Path ([System.IO.Path]::GetTempPath()) ('pie-piloto-' + [guid]::NewGuid())
$env:PIE_DATABASE_PATH = Join-Path $env:PIE_HOME 'pie.db'
$env:PIE_NOTES_DIR = Join-Path $env:PIE_HOME 'notes'
$env:PIE_REPORTS_DIR = Join-Path $env:PIE_HOME 'reports'
$env:PIE_BACKUP_DIR = Join-Path $env:PIE_HOME 'backups'
$env:PIE_EXPORT_DIR = Join-Path $env:PIE_HOME 'exports'
$env:PIE_EXTRACTOR_BACKEND = 'fake'
$env:PIE_LOCAL_TIMEZONE = 'America/Sao_Paulo'
.venv\Scripts\pie.exe doctor
.venv\Scripts\pie.exe add 'Decidi validar o PIE com dados sinteticos' --project PILOTO --type decision
.venv\Scripts\pie.exe entries list
.venv\Scripts\pie.exe review list
.venv\Scripts\pie.exe search 'validar'
.venv\Scripts\pie.exe report project --project PILOTO
.venv\Scripts\pie.exe backup create
```

Use os IDs exibidos para testar aprovação, rejeição, edição e exclusão/restauração
em entradas sintéticas diferentes. Confirme que a nota acompanha o status do banco.
`pie review edit <id> --project ""` limpa o projeto pela API Click; se o terminal
não preservar argumentos vazios, passe `--project " "`.

## Recuperação de falhas

- `pie entries failed` lista os IDs de entradas brutas pendentes/com erro que
  ainda não têm estruturação. A listagem não mostra o conteúdo.
- `pie entries retry <raw_entry_id>` retoma a extração usando o texto e o ID
  originais. O extrator precisa estar disponível; entradas já processadas ou
  excluídas são recusadas.
- `pie entries rebuild-note <structured_entry_id>` reconstrói uma nota a partir
  do banco sem executar novamente a extração.
- Edição, aprovação, rejeição e reprocessamento informam quando o banco foi salvo
  e a escrita da nota falhou. No lote, essa entrada conta como aplicada, com uma
  nota pendente de reconstrução. Corrija o acesso ao disco e execute o comando
  de reconstrução exibido.
- Migrações novas são transacionais: falha de SQL, verificação ou integridade
  desfaz a migração e seu registro. `doctor` informa migrações pendentes sem
  aplicá-las. As operações normais continuam aplicando migrações na inicialização.
- Para ensaiar restauração, copie um backup para uma base separada e aponte os
  caminhos para essa cópia. O teste automatizado reabre a cópia, verifica a
  integridade, o texto bruto, as revisões e a reconstrução da nota.

## Critérios de aprovação

1. Testes, lint e smoke do wheel passam no ambiente em uso.
2. Captura, revisão, busca e relatórios mantêm os IDs e o texto bruto corretos.
3. Falha de extração pode ser retomada sem duplicar a entrada bruta.
4. Falha de nota é visível; reconstruí-la recupera a projeção sem alterar a memória.
5. Uma cópia do backup recupera entradas, revisões e notas.
6. O piloto de sete dias registra erros, correções manuais e utilidade dos relatórios.

A avaliação sintética atual do `FakeExtractor` tem média aproximada de 52,26%,
com zero dos nove casos acima do corte de 80%. A pontuação é lexical, inclui
expectativas de confiança diferentes da calibração heurística e não mede
precisão semântica. Os critérios não foram relaxados para produzir aprovação.
Há proteção contra regressão da média atual e um limite opcional explícito:

```powershell
.venv\Scripts\pie.exe evaluate extraction --backend fake --min-score 0.8
```

Esse comando deve falhar com o extrator atual; preserva o relatório caso `--output`
seja informado. Use os resultados para decidir melhorias do extrator ou avaliar
um modelo local antes de confiar na classificação automática.

Após o ensaio sintético, siga o [roteiro de sete dias](usage_playbook.md).
