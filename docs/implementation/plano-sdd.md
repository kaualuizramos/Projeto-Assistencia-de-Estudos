# Plano SDD e matriz de verificação — Estuda+

## Interpretação do escopo

As especificações oficiais em `docs/specs/requisitos/` são a fonte de verdade e permanecem inalteradas. O produto é uma aplicação desktop local em Python. Em 02/11/2026, a solicitação do usuário substituiu a GUI Tkinter por PySide6/Qt Widgets; não é uma aplicação web. Portanto, “FR 1–6” no pedido é tratado como os seis grupos funcionais RF dos documentos 01–06; os IDs oficiais individuais continuam sendo RF01–RF46. “NFR 7–12” corresponde aos documentos 07–12 e aos IDs RNF101–RNF126.

Os RF que mencionam páginas, endpoints ou navegador são atendidos por telas e operações de serviço da aplicação desktop. RNF121 é adaptado para cinco módulos desktop com serviço e repositório próprios, sem rotas HTTP. RNF101–RNF103, RNF120 e RNF125 exigem endpoints web, navegador ou concorrência de servidor e não são propriedades verificáveis de um aplicativo desktop de usuário único; serão explicitamente reportados como incompatíveis com a plataforma definida, sem alterar os requisitos originais.

Integrações de IA e e-mail permanecem fora do processo visual e são isoladas em adaptadores. As credenciais são lidas do ambiente. A falta de credenciais deve produzir indisponibilidade clara e preservar as demais funções, nunca respostas de IA inventadas.

## Estado inicial investigado

- Um único arquivo `app.py`, GUI Tkinter, persistência SQLite e respostas de chat por palavras-chave.
- Não havia suíte de testes nem arquivo de dependências; o ambiente `.venv` tem Python 3.14 e Tkinter.
- O código inicial usa PBKDF2, não o algoritmo exigido RNF104; não tinha expiração de sessão, autorização/isolamento de login completo, limite de tentativas, edição/filtros de tarefas, IA externa, foco, painel, lembretes ou notificações completas.
- `assistente_estudos.db` é rastreado pelo Git e contém dados. O conteúdo pessoal não foi exibido. A regra `.gitignore` foi acrescentada, mas a pasta `.git` permanece sem escrita mesmo após pedido de permissão; o arquivo local continua rastreado e requer `git rm --cached assistente_estudos.db` manualmente. Hashes PBKDF2 existentes serão migrados para scrypt depois de login bem-sucedido.
- Nenhum arquivo de testes, configuração de CI, `tasks.md` ou especificação adicional SDD foi encontrado.

## Plano

1. Criar uma camada SQLite versionada e serviços para autenticação, tarefas/lembretes, chat/IA, sessões de foco e notificações.
2. Manter `app.py` como ponto de entrada e fornecer GUI desktop PySide6 integrada com dashboard, filtros e histórico.
3. Implementar adaptadores configuráveis de IA e SMTP, sem credenciais no código; manter o app útil quando os serviços externos não estiverem configurados.
4. Adicionar testes `unittest` para regras críticas e migração em banco temporário, sem usar os dados locais.
5. Atualizar o guia de execução e esta matriz com evidências dos testes e limitações da plataforma.

## Matriz de rastreabilidade

| Grupo / IDs oficiais | Componente esperado | Verificação planejada |
|---|---|---|
| RF01–RF04, RF34–RF37, RF40–RF41 | `authentication` | cadastro/login/erro genérico, inatividade, rate limit, recuperação, exclusão, ownership e controles administrativos |
| RF05–RF12, RF27–RF29, RF32, RF38–RF39, RF45–RF46 | `tasks` | CRUD, validação, subtarefas, conclusão, filtros, lembretes, notificações e falha/retry de e-mail |
| RF13–RF21, RF42 | `ai_chat` + adaptador de IA | contexto limitado, anonimização, persistência, falha/reenvio, resposta estruturada e aceitação explícita |
| RF22–RF26, RF43 | `focus_sessions` | iniciar/pausar/retomar/terminar, exclusividade, duração e notificação de conclusão |
| RF30–RF31, RF33 | `dashboard` + `focus_sessions` | métricas por período e históricos |
| RF44 | `notifications` | listar não lidas e marcar como lidas |
| RNF112–RNF115 | SQLite e isolamento do AI | persistência antes de sucesso, reinício e independência de falha de IA |
| RNF116–RNF119 | GUI desktop | fluxo descobrível, teclado, rótulos e redimensionamento; medidas web serão tratadas como adaptação |
| RNF120 | Plataforma | incompatível: versões de navegadores não se aplicam à GUI desktop |
| RNF101–RNF103, RNF125 | Plataforma/backend | incompatíveis: endpoints HTTP e carga de 100 usuários simultâneos não existem na aplicação desktop local |
| RNF104–RNF109, RNF124 | autenticação, persistência, integrações | scrypt, input validation, rate limiting, autorização por usuário, TLS externo e segredo fora do cliente versionado |
| RNF110–RNF111 | dados e telas de conta | minimização, aviso local, não exposição entre contas e exclusão solicitada |
| RNF121–RNF123, RNF126 | módulos, testes, logging e adaptadores | inspeção estrutural, `unittest`, logs sem segredos, adaptadores substituíveis |

## Evidências finais

- `python -m compileall -q app.py estuda tests`: concluído sem erros.
- `python -m unittest discover -s tests -v`: 13 testes aprovados.
- Migração de esquema legado e inicialização repetida exercitadas com banco em memória, sem usar os dados locais.
- GUI criada em Tkinter e inspecionada por smoke test local: janela existe, abas principais e widgets de tarefas/chat inicializados. A janela do processo iniciado não foi exposta pelo inventário do controlador visual; portanto não houve verificação visual manual dos fluxos autenticados.
- Integrações reais de IA/e-mail não foram chamadas: não há credenciais configuradas. Os adaptadores são exercitados por doubles de teste; a configuração externa permanece necessária para uso real.
- RNF101–RNF103, RNF120 e RNF125 não são aplicáveis à plataforma desktop exigida e continuam incompatíveis sem uma versão backend/web.
- `docs/implementation/relatorio-verificacao.md` registra o status por grupo funcional e de NFR.

## Atualização de interface — 02/11/2026

- A GUI ativa foi migrada de Tkinter para PySide6/Qt Widgets a pedido do usuário. `app.py` continua sendo o ponto de entrada, e os serviços SQLite/regras de negócio foram preservados.
- `requirements.txt` declara `PySide6-Essentials>=6.10.1,<7`; essa distribuição cobre Qt Widgets sem instalar os módulos adicionais não usados pelo app.
- `app.py` e `estuda/ui.py` passaram por `py_compile`; a suíte de serviços foi executada novamente: 13 testes aprovados.
- PySide6 Essentials 6.12 foi instalado no `.venv` local usando wheels oficiais verificadas. `app.py` inicializou sem erro e as telas de login, painel, tarefas, foco, chat, notificações, histórico e conta foram renderizadas para inspeção com banco SQLite em memória. A inspeção visual apontou e corrigiu o contraste do painel de login. Os 13 testes de serviços passaram após a migração. Ainda não foi realizado um ensaio manual completo dos fluxos autenticados; IA/SMTP reais também não foram testados sem credenciais.
- Na melhoria da experiência do chat: indicador de provedor/chave sem expor segredo; botões de início rápido; indicador de envio e resposta; cartões de propostas e tentativas com falha recolhidos quando vazios; texto restaurado se a solicitação for rejeitada antes de ser persistida; erros específicos do provedor preservados ao reenviar. Smoke test Qt com banco em memória e IA simulada passou.
