# ADR 0005: Contrato comum para provedores de IA

- **Status:** Aceito
- **Data:** 2026-11-04
- **Referência:** Commits 3148bc4, e25e474 e ADR 0001

## Contexto

O chat pode usar Gemini, OpenAI ou Ollama. A escolha é feita por configuração de ambiente e os clientes de cada provedor ficam em `estuda/integrations/ai.py`. O ADR 0001 registra a decisão do grupo sobre manter o Ollama como alternativa local sem custo.

## Problema

Implementações específicas de cada provedor poderiam espalhar detalhes de HTTP, formatos de resposta e configuração por `AIChatService` e pela interface. Isso tornaria a troca de provedor e os testes do chat mais difíceis.

## Decisão

Definir um contrato comum `AIClient` com disponibilidade e operação de resposta. Implementar cada provedor separadamente e selecionar o cliente por uma fábrica, usando variáveis de ambiente. Normalizar as respostas para texto e sugestões estruturadas; validar a resposta antes de persistir mensagens ou propostas.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Chamar cada API diretamente do chat ou da interface | Acopla as regras do produto aos protocolos e formatos dos provedores. |
| Adotar um SDK único para todos os provedores | Não oferece um contrato universal para todos os fornecedores e acrescentaria dependências ao protótipo. |
| Adaptadores independentes com contrato comum | Adotada por manter o serviço de chat independente da API concreta e permitir clientes simulados nos testes. |

## Consequências

**Positivas**
- O serviço de chat não precisa conhecer URLs e formatos HTTP específicos de cada provedor.
- Um provedor pode ser selecionado ou substituído sem reescrever as regras de conversa.
- Testes podem usar clientes simulados sem chamadas externas.
- Respostas inválidas podem ser tratadas como falhas, preservando a mensagem para reenvio.

**Negativas e riscos aceitos**
- Cada adaptador precisa acompanhar mudanças próprias do provedor.
- Uma resposta comum limita o uso de recursos específicos de cada API.
- Modelos locais e remotos podem variar em qualidade, latência e suporte à saída estruturada.

**Mitigações já existentes**
- Os clientes convertem falhas de transporte e formato para `AIUnavailable`.
- O chat valida respostas estruturadas e limita propostas a cinco subtarefas.
- O ADR 0001 documenta a escolha do Ollama para uso local e os limites aceitos para tarefas complexas.

## Quando reavaliar

Reavaliar se um provedor exigir operações que não possam ser expressas pelo contrato atual, se for necessário streaming de tokens, ou se as mudanças dos adaptadores deixarem de caber em uma interface comum simples.
