# Relatório de implementação e verificação

## Resumo

O protótipo original de arquivo único foi organizado em cinco módulos de serviço: autenticação, tarefas/lembretes, chat/IA, sessões de foco e notificações. Em 02/11/2026, a interface Tkinter foi substituída por uma GUI desktop PySide6/Qt Widgets. O ponto de entrada continua sendo `app.py`; a aplicação usa SQLite. Foram acrescentados migrações de banco, autenticação scrypt para novos cadastros, recuperação de senha, rate limit de login, filtros e edição de tarefas, lembretes, integração configurável com IA/SMTP, timers de foco, painel, histórico e notificações.

Os requisitos oficiais em `docs/specs/requisitos/` não foram alterados. As regras web foram registradas como incompatíveis com a restrição desktop. O banco de dados local preexistente foi preservado; seu conteúdo não foi exibido nem usado pelos testes.

## Status por grupo funcional

| Requisito | Status | Evidência |
|---|---|---|
| FR1 — Contas (RF01–RF04, RF34–RF37, RF40–RF41) | PARCIAL | `estuda/authentication.py`; scrypt, login genérico, tentativas limitadas, expiração local de 8h, recuperação de token de uso único, exclusão em cascata e controles admin. Testes em `tests/test_services.py`. RF34 depende de SMTP configurado e de o app estar aberto ao clicar no link; hashes PBKDF2 antigos só migram após login válido. |
| FR2 — Tarefas (RF05–RF12, RF27–RF29, RF32, RF38–RF39, RF45–RF46) | PARCIAL | `estuda/tasks.py`; CRUD, filtros, validações, ownership, subtarefas, status, lembretes, notificações locais e até quatro tentativas de e-mail (inicial + três retries). Coberto por testes de regras. Lembretes só são processados enquanto o aplicativo está aberto e autenticado; SMTP é opcional e não foi testado contra um provedor real. |
| FR3 — Chat com IA (RF13–RF21, RF42) | PARCIAL | `estuda/ai_chat.py`, `estuda/integrations/ai.py` e `estuda/ui.py`; histórico por conversa, contexto limitado aos 20 conteúdos mais recentes, sanitização, estado Failed/reenvio com detalhes do provedor preservados, progresso na tela, prompts iniciais e propostas estruturadas. Suporte integrado a Gemini, OpenAI e Ollama local. Teste de interface com IA simulada confirmou exibição de resposta e preservação do texto se o serviço rejeitar a solicitação antes de registrá-la. Não foi feita chamada real à API. |
| FR4 — Sessões de foco (RF22–RF26, RF43) | APROVADO EM TESTES DE SERVIÇO | `estuda/focus_sessions.py`; exclusividade, timestamps, pausa/retomada, cálculo de tempo efetivo, término, conclusão e notificação. Testes automatizados exercitam os fluxos e métricas. |
| FR5 — Painel e métricas (RF30–RF31, RF33) | PARCIAL | Painel e Histórico em `estuda/ui.py`; contagem de tarefas, métricas por período e histórico. As páginas do Qt foram instanciadas e renderizadas para inspeção visual usando banco em memória; fluxos autenticados ainda precisam de validação manual completa. |
| FR6 — Notificações (RF44) | APROVADO EM TESTES DE SERVIÇO | `estuda/notifications.py` e aba Notificações; lista lidas/não lidas e marcação individual/em lote. Notificações de foco, subtarefas e lembretes são criadas pelos serviços correspondentes. |

## Status por grupo NFR

| Requisito | Status | Evidência |
|---|---|---|
| NFR7 — Confiabilidade (RNF112–RNF115) | PARCIAL | SQLite confirma transações antes do retorno; migração idempotente; erro de IA mantém tarefa persistida e não bloqueia os serviços locais. Testes em memória confirmam schema e isolamento, mas não foi feito um ensaio de encerramento abrupto da aplicação. |
| NFR8 — Usabilidade, acessibilidade e compatibilidade (RNF116–RNF120) | PARCIAL | GUI desktop Qt redimensionável, navegação lateral, textos/labels e controles nativos. Telas foram renderizadas e inspecionadas visualmente; RNF119 cita larguras de viewport web e RNF120 requer navegadores, incompatíveis com a plataforma desktop. |
| NFR9 — Desempenho/disponibilidade (RNF101–RNF103) | INCOMPATÍVEL COM DESKTOP | Exigem endpoints HTTP, SLA mensal e tempos de resposta backend; este produto é uma aplicação local sem backend/rotas. Não há evidência de carga/availability para esses NFRs. |
| NFR10 — Manutenção, testes, observabilidade, escala e integração (RNF121–RNF123, RNF125–RNF126) | PARCIAL | Cinco módulos de serviço, adaptadores dedicados de IA/SMTP, logging sem senhas/chaves e 16 testes automatizados. RNF125 exige 100 usuários simultâneos num servidor, incompatível com a arquitetura desktop local; nem todo critério tem teste dedicado. |
| NFR11 — Privacidade (RNF110–RNF111) | PARCIAL | Queries de serviços limitadas ao usuário; exclusão em cascata; aviso de dados locais; nome/e-mail removidos do contexto normal do chat. Conformidade legal completa/LGPD não foi certificada. O banco pessoal continua rastreado pelo Git porque `.git` recusou escrita no índice; não o inclua em commits. |
| NFR12 — Segurança (RNF104–RNF109, RNF124) | PARCIAL | Novas senhas usam scrypt; entrada validada; limite de tentativas e checagens de propriedade; IA por HTTPS e SMTP exige TLS; chaves apenas por variável de ambiente. O banco legado ainda contém hashes PBKDF2 até cada usuário autenticar, e uma aplicação desktop não consegue esconder a chave do processo local como faria um backend. |

## Arquivos principais

- `app.py`: inicializador desktop.
- `estuda/ui.py`: GUI PySide6/Qt Widgets e navegação por páginas.
- `requirements.txt`: dependência PySide6-Essentials usada pela GUI Qt.
- `estuda/database.py`: SQLite e migração do protótipo legado.
- `estuda/authentication.py`, `estuda/tasks.py`, `estuda/ai_chat.py`, `estuda/focus_sessions.py`, `estuda/notifications.py`: serviços dos cinco módulos.
- `estuda/integrations/ai.py`, `estuda/integrations/email.py`: integrações isoladas (Gemini, OpenAI e Ollama; SMTP).
- `tests/test_services.py`: testes `unittest` independentes da base local.
- Smoke test de UI Qt com banco em memória e IA simulada: mensagem/resposta exibidas no histórico e texto restaurado no campo quando a IA estava desativada antes do registro.

## Execução e evidências

- Aplicação: `python app.py` no ambiente do projeto.
- Testes: `python -m unittest discover -s tests -v` — **16 aprovados, 0 reprovados**.
- Sintaxe: `python -m compileall -q app.py estuda tests` — concluído sem erros.
- Verificação anterior da GUI Tkinter: janela e páginas inicializadas antes da migração.
- GUI Qt: `py_compile` passou; PySide6 Essentials foi instalado no ambiente local a partir de wheels oficiais verificadas. As telas de login e das sete áreas do estudante foram renderizadas usando SQLite em memória e inspecionadas visualmente.
- IA real e SMTP real: não testados por falta de credenciais; instruções em `README-prototipo.md`.
- A aplicação abriu e as telas foram renderizadas; não foi feito um ensaio manual completo clicando e percorrendo todos os fluxos autenticados.
- Requisito de segurança Git pendente: depois de encerrar o aplicativo, execute `git rm --cached assistente_estudos.db` no terminal do repositório. O comando remove apenas o rastreamento Git e preserva o banco local; depois confirme que o arquivo continua no disco e não aparece como incluído no commit.

## Estado final

**Parcialmente concluído.** A aplicação desktop e as regras locais estão implementadas e os 16 testes de serviço passaram. A interface PySide6 foi aberta, renderizada e inspecionada visualmente; ainda falta um ensaio manual completo dos fluxos autenticados. Permanecem também a validação real de IA/e-mail, a remoção do banco pessoal do índice Git e requisitos web/carga incompatíveis com desktop.
