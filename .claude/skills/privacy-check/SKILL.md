---
name: privacy-check
description: Verifica se o codigo respeita a tese local-first/privacy-first do PIE. Use ao mexer em adapters, exports, logs ou config.
context: fork
agent: senior-reviewer
argument-hint: [arquivo-ou-modulo]
---

Faca uma auditoria de privacidade com foco em: $ARGUMENTS

Verifique no codigo (NAO nos dados reais) os seguintes vetores de vazamento:

1. LLM remoto: o adapter Ollama (local_llm_extractor.py) envia conteudo para
   endpoint externo? _validate_base_url bloqueia hosts nao-locais?
   Conteudo pessoal vai cru no prompt?

2. Logs: ha logger.info/debug imprimindo conteudo de raw_entries ou dados
   pessoais? Logs deveriam mostrar IDs e metadados, nunca o conteudo.

3. Exports/backups: export_json e export_markdown excluem soft-deleted?
   backups antigos podem reter dados apagados?

4. Delete real: soft delete e purge removem o .md correspondente de notes/
   do disco, ou o plaintext fica la apos o usuario "apagar"?

5. Mensagens de erro: exceptions vazam conteudo de entradas em tracebacks?

NAO leia notes/, reports/, backups/, exports/ nem pie.db — analise so o codigo.
NAO altere arquivos.

Saida:
- Vetores verificados (com status: ok / risco / nao aplicavel)
- Vazamentos confirmados no codigo (com arquivo:linha)
- Correcao recomendada para cada risco
- Veredito: respeita a tese local-first? SIM / COM RESSALVAS / NAO
