# ADR 0006: Credenciais fora do banco e minimização do contexto de IA

- **Status:** Aceito
- **Data:** 2026-11-04
- **Referência:** Commits 17c182b, 3148bc4; requisitos RNF110, RNF123 e RNF124

## Contexto

Os provedores Gemini e OpenAI usam chaves externas; Ollama pode executar localmente. O chat precisa enviar contexto para responder, enquanto as especificações exigem cuidado com credenciais, registros e dados pessoais.

## Problema

Credenciais salvas no código ou banco podem ser versionadas junto ao projeto. Enviar toda a conversa ou identificadores do usuário para um provedor remoto também expõe dados além do necessário para responder à solicitação atual.

## Decisão

Ler credenciais e seleção de provedor do ambiente, sem persistir chaves no código ou no banco. Antes de enviar contexto ao provedor, limitar o conteúdo às 20 mensagens mais recentes e remover o nome e e-mail cadastrados, outros e-mails detectáveis e credenciais identificadas por padrões comuns. A configuração de Ollama permite manter as chamadas no computador local.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Incluir a chave no código-fonte | Facilita vazamento em commits e cópias do projeto. |
| Salvar a chave no banco SQLite | Mistura credenciais externas com os dados do aplicativo e mantém o segredo em disco sem um cofre dedicado. |
| Ler credenciais do ambiente e reduzir o contexto enviado | Adotada por evitar persistência no projeto e limitar dados enviados ao provedor. |
| Sempre enviar o histórico completo | Aumenta a exposição de dados e o tamanho da requisição sem ser necessário para o contexto recente especificado. |

## Consequências

**Positivas**
- Chaves não são gravadas nas tabelas da aplicação.
- O contexto remoto é limitado e passa por sanitização antes do envio.
- O usuário pode escolher Ollama para processar o chat localmente.

**Negativas e riscos aceitos**
- Variáveis de ambiente precisam ser configuradas no processo que inicia o aplicativo.
- A sanitização por padrões não garante a remoção de toda informação pessoal que o usuário possa escrever.
- Em um aplicativo desktop, a chave continua acessível ao usuário e a processos com permissões sobre o mesmo ambiente; variável de ambiente não é um cofre de segredos.
- Quando Gemini ou OpenAI são selecionados, o texto sanitizado ainda é enviado ao serviço externo por HTTPS e fica sujeito às políticas desse provedor.

**Mitigações já existentes**
- A documentação orienta configurar as chaves fora do código e não as incluir em commits.
- Os logs registram tipo de erro e identificadores internos, sem gravar o conteúdo da conversa ou a chave.
- A seleção de Ollama permite operação sem chave externa, e as demais funcionalidades permanecem disponíveis quando a IA não está acessível.

## Quando reavaliar

Reavaliar se o aplicativo for distribuído a usuários sem controle do ambiente onde executa, se precisar de um cofre de credenciais do sistema operacional, se for adotado um backend central ou se a política de privacidade dos provedores mudar.
