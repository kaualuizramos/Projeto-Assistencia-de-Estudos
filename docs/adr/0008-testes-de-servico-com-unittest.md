# ADR 0008: Testes de serviço com unittest e banco isolado

- **Status:** Aceito
- **Data:** 2026-11-04
- **Referência:** Commit 17c182b; requisito RNF122

## Contexto

O projeto mantém testes automatizados para autenticação, tarefas, chat, sessões de foco, notificações, migrações e adaptadores. A suíte usa `unittest`, banco SQLite em memória e substitutos para serviços externos.

## Problema

Testes que dependem do banco pessoal do desenvolvedor, de uma chave de IA, de SMTP real ou da rede não seriam repetíveis nem seguros para executar durante o desenvolvimento escolar. Também é necessário verificar regras de negócio sem iniciar toda a interface desktop.

## Decisão

Usar `unittest` da biblioteca padrão para os testes automatizados de serviço. Criar bancos isolados em memória para cada caso e usar clientes simulados para IA e e-mail. Reservar testes manuais para a inicialização e a inspeção da interface, e não exigir chamadas reais aos provedores externos para validar as regras locais.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Testar usando `assistente_estudos.db` | Pode alterar dados pessoais e gerar resultados dependentes do estado da máquina. |
| Chamar Gemini, OpenAI, Ollama ou SMTP real em cada suíte | Exige serviços externos disponíveis, credenciais e cotas, tornando os testes lentos e não determinísticos. |
| Não manter testes automatizados | Deixa regras críticas e migrações vulneráveis a regressões não detectadas. |
| `unittest`, SQLite em memória e integrações simuladas | Adotada por não adicionar dependências e permitir testes locais repetíveis. |

## Consequências

**Positivas**
- Os testes não leem nem modificam o banco pessoal do projeto.
- Testes de serviço podem ser executados sem rede ou credenciais de IA/e-mail.
- Migrações e regras de autorização podem ser avaliadas em bancos temporários.

**Negativas e riscos aceitos**
- Clientes simulados não validam disponibilidade, preço, cota ou formato atual dos serviços externos.
- Testes de serviço não substituem testes manuais de todos os fluxos da interface.
- `unittest` fornece menos recursos auxiliares que frameworks de terceiros, embora seja suficiente para a escala atual.

**Mitigações já existentes**
- A suíte usa `Database(":memory:")` e clientes fakes para IA e SMTP.
- Adaptadores possuem testes de parsing, configuração e tratamento de falhas.
- A aplicação e as telas podem ser verificadas separadamente usando uma conta e banco de demonstração em memória.

## Quando reavaliar

Reavaliar se a suíte crescer a ponto de precisar de fixtures e parametrização mais avançadas, se forem introduzidos testes de interface automatizados ou se houver ambiente de integração contínua com credenciais de teste controladas.
