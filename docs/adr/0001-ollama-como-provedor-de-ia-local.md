# ADR 0001: Ollama como provedor de IA local e manutenção da solução atual

- **Status:** Aceito
- **Data:** 2026-11-04
- **Referência:** Issue #1

## Contexto

O assistente de estudos do Estuda+ (chat, explicações e geração de até cinco subtarefas) depende de um provedor de IA. A aplicação suporta três provedores, escolhidos pela variável de ambiente `ESTUDA_AI_PROVIDER`:

- **Gemini** (Google AI Studio) e **OpenAI** (Responses API): exigem chave de API, e limites e cobrança são definidos pelo fornecedor.
- **Ollama**: modelo executado localmente (padrão `llama3.2`, host `http://localhost:11434`), sem chave de API e sem enviar dados a servidores de terceiros.

O projeto não tem orçamento para pagar por uso de IA e, no momento, não há um provedor de IA gratuito disponível que atenda ao projeto de forma estável.

## Problema

O Ollama foi integrado e funciona para perguntas e pedidos simples. Os modelos locais que o projeto consegue executar, porém, não conseguem responder bem a mensagens muito complexas, como pedidos longos de planejamento ou a divisão de um trabalho grande em etapas. Nesses casos a resposta pode vir incompleta ou fora do formato esperado.

## Decisão

Manter o projeto como está:

1. Ollama permanece integrado como provedor local e sem custo.
2. Não será contratado nem adotado nenhum provedor pago, porque não há provedor de IA gratuito disponível.
3. A limitação com mensagens muito complexas é aceita e documentada, em vez de ser resolvida com mudanças de arquitetura ou de provedor.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Usar Gemini ou OpenAI como provedor padrão | Exige chave própria e pode gerar cobrança, e não há provedor gratuito disponível. |
| Trocar por um modelo local maior no Ollama | Depende do hardware de cada computador e não pode ser exigido de quem usa o aplicativo. |
| Remover a geração de etapas ou o chat | Elimina uma funcionalidade central do assistente. |

## Consequências

**Positivas**
- Custo zero e nenhuma chave de API para configurar.
- Privacidade: com Ollama, o conteúdo do chat não sai do computador.
- O restante do aplicativo (tarefas, foco, notificações, painel) não depende da IA.

**Negativas e riscos aceitos**
- Pedidos muito complexos podem receber respostas fracas, incompletas ou fora do formato esperado.
- Quando a resposta não segue o formato esperado, o serviço trata como falha: a mensagem fica salva com estado de falha e pode ser reenviada pelo usuário.
- A qualidade das respostas varia conforme o modelo instalado no Ollama.

**Mitigações já existentes**
- Quem tiver chave pode usar Gemini ou OpenAI apenas configurando as variáveis de ambiente, sem alterar o código.
- O administrador pode habilitar ou desabilitar o assistente e definir o limite diário de mensagens.
- A geração de etapas só adiciona subtarefas depois que o estudante aceita cada proposta.
- Recomendação de uso: pedir ao assistente tarefas menores e específicas, em vez de um trabalho inteiro de uma vez.

## Quando reavaliar

Esta decisão deve ser revisada se surgir um provedor de IA gratuito e estável, ou se o projeto passar a ter orçamento para um provedor pago.
