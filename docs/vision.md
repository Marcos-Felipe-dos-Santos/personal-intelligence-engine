# PIE Vision

PIE is a local-first personal intelligence engine. Its long-term direction has two layers:

- **PIE Core**: the durable memory, validation, review, search, report, and audit layer.
- **Assistant Layer**: a future interaction layer that can use PIE Core as memory and as a tool, while keeping human approval at the center.

The immediate priority is to finish PIE Core v1 before building an assistant experience.

## PIE Core

PIE Core is responsible for evidence and traceability.

It should:

- capture raw entries
- preserve raw data before extraction
- validate structured data
- support human review
- support local search
- generate grounded reports
- keep audit logs
- expose safe commands and local APIs for future layers

Core should remain useful without any LLM, cloud service, voice interface, or external integration.

## Future Assistant Layer

The Assistant Layer is a future layer that may sit beside Core. It should not replace Core and should not become the source of truth.

It may eventually:

- interpret user intent
- query PIE Core
- summarize memories with citations
- propose actions
- call approved tools
- ask for confirmation before writes or external actions

The Assistant Layer should be allowed to feel like a personal helper, but it must remain grounded in source data and explicit user approval.

## Personal Assistant Inspiration

The project can use the idea of a highly capable personal assistant as a metaphor for direction: fast, contextual, helpful, and aware of the user's local memory.

That metaphor is not a product claim. PIE is not currently an assistant like that. It should also not clone a fictional character, voice, personality, or likeness. The final assistant name and identity should be chosen later, after the architecture and safety rules are clearer.

## Design Principles

- **Local-first**: default operation should work locally.
- **Privacy-first**: personal data should not leave the machine without explicit choice.
- **Source-grounded**: memory outputs should cite raw or structured entry IDs.
- **Auditability**: important transformations and actions should be inspectable.
- **Human approval**: writes, external actions, and sensitive operations should require confirmation.
- **Small steps**: build the memory core before building a broad assistant.

## Non-Goals For Now

- No Assistant Layer implementation in the current codebase.
- No voice cloning.
- No fictional character cloning.
- No autonomous external actions.
- No external write integrations without an approval layer.
- No RAG or embeddings until Core v1 basics are complete.
- No external workflow platform as the project nucleus.
