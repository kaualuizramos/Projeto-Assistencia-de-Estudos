# Estuda+ — protótipo de apresentação

Aplicação desktop simples em Python para demonstrar cadastro/login, organização de tarefas de estudo e uma conversa demonstrativa com um assistente.

## Como executar

1. Abra a pasta do projeto no PyCharm.
2. Abra `app.py` e execute o arquivo com Python 3.10 ou superior.
3. Na primeira execução, o programa cria `assistente_estudos.db` na pasta do projeto.
4. Crie uma conta na aba **Criar conta** e entre.

O protótipo usa apenas bibliotecas incluídas no Python (Tkinter e SQLite). No Windows, o instalador oficial do Python inclui Tkinter.

## O que dá para demonstrar

- Criar conta com nome, e-mail único e senha de pelo menos 8 caracteres.
- Entrar e sair da conta; senhas ficam armazenadas como hash com salt.
- Criar, listar, concluir/reabrir e excluir tarefas, com descrição, prazo e prioridade.
- Criar e concluir subtarefas. Uma tarefa com subtarefas pendentes não pode ser concluída.
- Conversar com respostas locais de demonstração. O histórico fica salvo por conta.

## Limites desta versão

O chat **não chama um modelo de IA**: respostas são simuladas por regras simples para a apresentação funcionar sem chave de API ou internet. Recuperação de senha por e-mail, lembretes, notificações, limite diário de mensagens, sessões com expiração por inatividade e painel administrativo ficam para versões futuras.

Os requisitos originais continuam nos arquivos em `docs/specs/requisitos/`; o protótipo implementa somente um recorte deles.
