# ADR 0004: Persistência local com SQLite e migrações versionadas

- **Status:** Aceito
- **Data:** 2026-11-04
- **Referência:** Commits 17c182b, 27a4e8a e 477cbb6

## Contexto

O Estuda+ é um aplicativo desktop individual. Ele precisa preservar contas, tarefas, conversas, notificações e sessões entre execuções. A aplicação utiliza SQLite em um arquivo local, com criação e migração de esquema controladas pelo módulo `estuda/database.py`.

## Problema

O protótipo precisa de persistência confiável sem exigir que o estudante instale ou administre um servidor de banco de dados. O esquema também evolui conforme novas funcionalidades são implementadas, e o banco local contém dados pessoais que não devem ser enviado ao repositório.

## Decisão

Usar SQLite local como armazenamento da aplicação. Aplicar migrações incrementais com `PRAGMA user_version`, habilitar chaves estrangeiras e transações por conexão, e manter o arquivo de banco fora do controle de versão.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Arquivos JSON ou CSV | Não oferecem as mesmas garantias transacionais e relações necessárias para usuários, tarefas, conversas e subtarefas. |
| Banco de dados servidor | Exigiria implantação, rede e administração que não fazem parte do escopo desktop local. |
| SQLite local | Adotado por ser embutido, persistente e suficiente para o uso de um aplicativo local. |

## Consequências

**Positivas**
- O aplicativo funciona sem conexão a um servidor de banco de dados.
- Transações, chaves estrangeiras e migrações ficam disponíveis sem uma dependência adicional.
- Cada instalação mantém seus dados na máquina local.

**Negativas e riscos aceitos**
- O banco não sincroniza dados entre computadores nem fornece acesso multiusuário remoto.
- Falha ou perda do arquivo local pode causar perda dos dados sem cópia de segurança.
- Alterações de esquema precisam manter compatibilidade com bancos criados por versões anteriores.

**Mitigações já existentes**
- A criação de conexões usa transações, chave estrangeira e espera por bloqueios temporários.
- O esquema registra sua versão e aplica migrações incrementais.
- `assistente_estudos.db` é ignorado pelo Git e foi removido do rastreamento para não versionar dados pessoais.

## Quando reavaliar

Reavaliar se houver necessidade de sincronização entre dispositivos, colaboração simultânea entre usuários em computadores diferentes, cópias de segurança automáticas ou volume de dados que não seja adequado a um arquivo local.
