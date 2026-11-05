# ADR 0003: Módulos de serviço e integrações isoladas

- **Status:** Aceito
- **Data:** 2026-11-04
- **Referência:** Commit 17c182b; requisitos RNF121 e RNF126

## Contexto

O protótipo inicial concentrava interface, persistência e regras em `app.py`. A implementação atual separa autenticação, tarefas, chat, sessões de foco e notificações em módulos próprios. As integrações com IA e e-mail também possuem componentes dedicados.

## Problema

Um arquivo único tornava difícil alterar regras de negócio, testar operações isoladamente e substituir integrações sem afetar telas e outros serviços. As especificações também pedem módulos funcionais e isolamento das integrações externas.

## Decisão

Organizar o aplicativo em módulos de serviço por área funcional. A interface chama os serviços públicos; os serviços concentram as regras e usam a camada SQLite. Provedores de IA e entrega de e-mail ficam atrás de componentes de integração próprios.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Manter toda a aplicação em `app.py` | Mistura responsabilidades e torna mudanças e testes mais arriscados. |
| Separar apenas por telas | Não isola regras de negócio da interface nem os adaptadores externos. |
| Criar serviços por domínio e adaptadores de integração | Adotada por corresponder aos módulos do produto e aos limites definidos nos requisitos. |
| Introduzir uma arquitetura distribuída com serviços remotos | Desnecessária para um aplicativo desktop local e acrescentaria implantação e operação de servidor. |

## Consequências

**Positivas**
- Regras de tarefas, autenticação, chat, foco e notificações podem ser exercitadas sem abrir a interface.
- Provedores de IA e e-mail podem ser trocados sem espalhar chamadas HTTP pela aplicação.
- As responsabilidades ficam mais claras para manutenção incremental.

**Negativas e riscos aceitos**
- A separação exige mais módulos e interfaces do que um protótipo de arquivo único.
- A interface ainda mantém código de apresentação e coordenação em `estuda/ui.py`; ela não é uma camada completamente independente.
- Os serviços compartilham a persistência SQLite e precisam respeitar limites de propriedade dos dados.

**Mitigações já existentes**
- Há módulos dedicados em `estuda/` para cada serviço e uma pasta `estuda/integrations/` para adaptadores.
- Os testes de serviço usam banco em memória e clientes simulados.
- O chat verifica a propriedade de conversas e os serviços filtram dados pelo usuário.

## Quando reavaliar

Reavaliar se os módulos passarem a exigir implantação independente, se a interface precisar de uma API pública, ou se o compartilhamento de acesso ao banco criar acoplamento que impeça testar ou alterar um domínio separadamente.
