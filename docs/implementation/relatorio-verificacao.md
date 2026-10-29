# Relatório de implementação e verificação

## Resumo

O protótipo Tkinter de arquivo único foi organizado em cinco módulos de serviço: autenticação, tarefas/lembretes, chat/IA, sessões de foco e notificações. O ponto de entrada continua sendo `app.py`; a aplicação usa apenas a biblioteca padrão e SQLite. Foram acrescentados migrações de banco, autenticação scrypt para novos cadastros, recuperação de senha, rate limit de login, filtros e edição de tarefas, lembretes, integração configurável com IA/SMTP, timers de foco, painel, histórico e notificações.

Os requisitos oficiais em `docs/specs/requisitos/` não foram alterados. As regras web foram registradas como incompatíveis com a restrição desktop. O banco de dados local preexistente foi preservado; seu conteúdo não foi exibido nem usado pelos testes.

## Status por grupo funcional

| Requisito | Status | Evidência |
|---|---|---|
| FR1 — Contas (RF01–RF04, RF34–RF37, RF40–RF41) | PARCIAL | `estuda/authentication.py`; scrypt, login genérico, tentativas limitadas, expiração local de 8h, recuperação de token de uso único, exclusão em cascata e controles admin. Testes em `tests/test_services.py`. RF34 depende de SMTP configurado e de o app estar aberto ao clicar no link; hashes PBKDF2 antigos só migram após login válido. |
| FR2 — Tarefas (RF05–RF12, RF27–RF29, RF32, RF38–RF39, RF45–RF46) | PARCIAL | `estuda/tasks.py`; CRUD, filtros, validações, ownership, subtarefas, status, lembretes, notificações locais e até quatro tentativas de e-mail (inicial + três retries). Coberto por testes de regras. Lembretes só são processados enquanto o aplicativo está aberto e autenticado; SMTP é opcional e não foi testado contra um provedor real. |
| FR3 — Chat com IA (RF13–RF21, RF42) | PARCIAL | `estuda/ai_chat.py` e `estuda/integrations/ai.py`; histórico por conversa, contexto limitado aos 20 conteúdos mais recentes, remoção de identificadores comuns, estado Failed/reenvio, limite diário, propostas estruturadas aceitas/rejeitadas explicitamente. Testes usam IA simulada; não há `OPENAI_API_KEY` para validar uma chamada real. |
| FR4 — Sessões de foco (RF22–RF26, RF43) | APROVADO EM TESTES DE SERVIÇO | `estuda/focus_sessions.py`; exclusividade, timestamps, pausa/retomada, cálculo de tempo efetivo, término, conclusão e notificação. Testes automatizados exercitam os fluxos e métricas. |
| FR5 — Painel e métricas (RF30–RF31, RF33) | PARCIAL | Aba Visão geral e Histórico em `estuda/ui.py`; contagem de tarefas, métricas por período e histórico. Construção da GUI foi smoke-tested; não foi possível inspecionar visualmente a janela pelo controlador nem fazer interação autenticada manualmente. |
| FR6 — Notificações (RF44) | APROVADO EM TESTES DE SERVIÇO | `estuda/notifications.py` e aba Notificações; lista lidas/não lidas e marcação individual/em lote. Notificações de foco, subtarefas e lembretes são criadas pelos serviços correspondentes. |

## Status por grupo NFR

| Requisito | Status | Evidência |
|---|---|---|
| NFR7 — Confiabilidade (RNF112–RNF115) | PARCIAL | SQLite confirma transações antes do retorno; migração idempotente; erro de IA mantém tarefa persistida e não bloqueia os serviços locais. Testes em memória confirmam schema e isolamento, mas não foi feito um ensaio de encerramento abrupto da aplicação. |
| NFR8 — Usabilidade, acessibilidade e compatibilidade (RNF116–RNF120) | PARCIAL | GUI redimensionável, navegação padrão por teclado, textos/labels e dicas de uso. Smoke test confirmou a criação das abas e widgets. RNF119 cita larguras de viewport web e a janela desktop tem largura mínima de 760 px; RNF120 requer navegadores, incompatíveis com a decisão desktop. Fluxos não foram avaliados visualmente com usuário. |
| NFR9 — Desempenho/disponibilidade (RNF101–RNF103) | INCOMPATÍVEL COM DESKTOP | Exigem endpoints HTTP, SLA mensal e tempos de resposta backend; este produto é uma aplicação local sem backend/rotas. Não há evidência de carga/availability para esses NFRs. |
| NFR10 — Manutenção, testes, observabilidade, escala e integração (RNF121–RNF123, RNF125–RNF126) | PARCIAL | Cinco módulos de serviço, adaptadores dedicados de IA/SMTP, logging sem senhas/chaves e 13 testes automatizados. RNF125 exige 100 usuários simultâneos num servidor, incompatível com a arquitetura desktop local; nem todo critério tem teste dedicado. |
| NFR11 — Privacidade (RNF110–RNF111) | PARCIAL | Queries de serviços limitadas ao usuário; exclusão em cascata; aviso de dados locais; nome/e-mail removidos do contexto normal do chat. Conformidade legal completa/LGPD não foi certificada. O banco pessoal continua rastreado pelo Git porque `.git` recusou escrita no índice; não o inclua em commits. |
| NFR12 — Segurança (RNF104–RNF109, RNF124) | PARCIAL | Novas senhas usam scrypt; entrada validada; limite de tentativas e checagens de propriedade; IA por HTTPS e SMTP exige TLS; chaves apenas por variável de ambiente. O banco legado ainda contém hashes PBKDF2 até cada usuário autenticar, e uma aplicação desktop não consegue esconder a chave do processo local como faria um backend. |

## Arquivos principais

- `app.py`: inicializador desktop.
- `estuda/ui.py`: GUI Tkinter e fluxo entre abas.
- `estuda/database.py`: SQLite e migração do protótipo legado.
- `estuda/authentication.py`, `estuda/tasks.py`, `estuda/ai_chat.py`, `estuda/focus_sessions.py`, `estuda/notifications.py`: serviços dos cinco módulos.
- `estuda/integrations/ai.py`, `estuda/integrations/email.py`: integrações isoladas.
- `tests/test_services.py`: testes `unittest` independentes da base local.

## Execução e evidências

- Aplicação: `python app.py` no ambiente do projeto.
- Testes: `python -m unittest discover -s tests -v` — **13 aprovados, 0 reprovados**.
- Sintaxe: `python -m compileall -q app.py estuda tests` — concluído sem erros.
- Smoke test Tkinter: janela, sete abas para estudante e widgets Treeview/Text inicializados.
- IA real e SMTP real: não testados por falta de credenciais; instruções em `README-prototipo.md`.
- A GUI abriu no Windows e reportou o título `Estuda+ | Assistente de estudos`, mas o controlador de UI não listou a janela Python; os fluxos autenticados não tiveram inspeção visual.
- Requisito de segurança Git pendente: depois de encerrar o aplicativo, execute `git rm --cached assistente_estudos.db` no terminal do repositório. O comando remove apenas o rastreamento Git e preserva o banco local; depois confirme que o arquivo continua no disco e não aparece como incluído no commit.

## Estado final

**Parcialmente concluído.** A aplicação desktop e as regras locais estão implementadas e os testes de serviço passaram. Permanecem pendentes a configuração/validação de provedores reais de IA e e-mail, a remoção do banco pessoal do índice Git, a inspeção visual da janela autenticada e requisitos web/carga incompatíveis com desktop.
