# Estuda+ — aplicativo desktop de assistência de estudos

Aplicação desktop local para Windows/PC, desenvolvida em Python com **PySide6 (Qt Widgets)** e SQLite. O banco preserva tarefas, subtarefas, conversas, notificações e sessões entre execuções. A interface é nativa para desktop e não é uma aplicação web.

## Executar

1. Abra a pasta do repositório no PyCharm e selecione o ambiente `.venv` já criado.
2. No terminal do projeto, instale a dependência gráfica com `python -m pip install -r requirements.txt`.
3. Execute `app.py` ou, no terminal do projeto, `python app.py`.
4. Crie sua conta na tela inicial. A senha deve ter ao menos 8 caracteres.

Os testes podem ser executados com `python -m unittest discover -s tests -v`.

## Funcionalidades

- Cadastro, login, limite de tentativas, encerramento após 8 horas sem atividade, recuperação de senha por e-mail e exclusão de conta confirmada.
- Tarefas com validação de título, descrição, data e prioridade; edição, exclusão, filtros e classificação de atrasadas.
- Subtarefas; a conclusão da tarefa é bloqueada enquanto existirem etapas pendentes.
- Lembretes locais e notificação dentro do aplicativo; envio opcional por e-mail e tentativas automáticas em caso de falha.
- Chat por provedor de IA configurado, com histórico, contexto recente, falha/reenvio e propostas de subtarefas que precisam ser aceitas pelo estudante.
- Sessões de foco com temporizador, pausa, retomada, término, histórico e notificação de conclusão.
- Painel com métricas de tarefas e foco, notificações lidas/não lidas e histórico pessoal.
- Configuração administrativa de habilitação e limite diário do assistente.

## Integrações externas

O restante do aplicativo continua funcionando sem as integrações. Sem credenciais, o chat informa que a IA está indisponível e mantém a mensagem com estado de falha. Para habilitar a IA, configure as variáveis no ambiente antes de iniciar o aplicativo. Não coloque chaves em arquivos Python, no banco de dados ou em commits.

### Gemini (Google AI Studio)

- Defina `ESTUDA_AI_PROVIDER=gemini`.
- Defina `GEMINI_API_KEY` com a chave criada no Google AI Studio.
- Opcionalmente, defina `ESTUDA_AI_MODEL` (padrão: `gemini-3.8-flash`).

### OpenAI (Responses API)

- Defina `ESTUDA_AI_PROVIDER=openai` e `OPENAI_API_KEY` para selecionar OpenAI explicitamente. Sem provedor definido, o app usa Gemini; quando `GEMINI_API_KEY` existir, ela prevalece sobre uma seleção OpenAI antiga sem chave OpenAI.
- Defina `OPENAI_API_KEY` com sua chave da plataforma OpenAI.
- Opcionalmente, defina `ESTUDA_AI_MODEL` (padrão: `gpt-4o-mini`).

No PyCharm, abra **Run > Edit Configurations...**, selecione a configuração de `app.py` e adicione as variáveis em **Environment variables**. Exemplo Gemini: `ESTUDA_AI_PROVIDER=gemini;GEMINI_API_KEY=sua-chave`. Salve e reinicie o aplicativo. Cada provedor requer sua própria chave e limites/cobrança são definidos pelo fornecedor.

Para e-mail, defina as variáveis de ambiente `ESTUDA_SMTP_HOST`, `ESTUDA_SMTP_PORT` (padrão 587), `ESTUDA_SMTP_USER`, `ESTUDA_SMTP_PASSWORD`, `ESTUDA_SMTP_FROM` e, quando o provedor exigir TLS implícito, `ESTUDA_SMTP_SSL=true`. O aplicativo exige STARTTLS ou TLS implícito para a conexão SMTP.

O chat envia somente os últimos 20 conteúdos de mensagem necessários à conversa; remove o nome e o e-mail cadastrados, endereços de e-mail detectáveis e credenciais escritas em formatos comuns. As requisições são feitas por HTTPS e não solicitam armazenamento da resposta pelo provedor. Evite inserir dados pessoais desnecessários no chat.

Para conceder o perfil administrador antes de criar a conta, defina `ESTUDA_ADMIN_EMAIL` com o e-mail que será usado no cadastro. A primeira conta com esse e-mail recebe os controles de habilitar/desabilitar o assistente e definir o limite diário. Não deixe essa variável configurada num computador compartilhado.

O link de recuperação de senha é entregue por SMTP e aciona o diálogo de senha do aplicativo em execução neste computador; mantenha o Estuda+ aberto ao clicar no link. Lembretes só enviam e-mail quando essa opção for marcada, desativada por padrão.

## Dados locais e migração

O banco `assistente_estudos.db` fica na pasta do projeto e é preservado por migrações versionadas. O banco preexistente do protótipo permanece no computador. Os hashes antigos PBKDF2 são atualizados para scrypt quando a conta correspondente entra com sucesso; novos cadastros usam scrypt desde a criação. A regra para ignorar o banco está no `.gitignore`, mas o arquivo já era rastreado pelo Git; para parar de rastreá-lo sem apagar a cópia local, execute `git rm --cached assistente_estudos.db` uma vez. Não inclua o banco modificado num commit: ele contém dados locais.

O arquivo `estuda.log` registra eventos e erros sem senhas, tokens de sessão, chaves de API ou conteúdo de conversas. Não compartilhe esses arquivos. O banco contém dados pessoais e ainda está rastreado no Git até executar o comando de remoção indicado acima.
