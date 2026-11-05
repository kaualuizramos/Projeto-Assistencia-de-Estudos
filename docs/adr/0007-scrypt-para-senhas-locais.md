# ADR 0007: Hash de senhas com scrypt

- **Status:** Aceito
- **Data:** 2026-11-04
- **Referência:** Commit 17c182b; requisito RNF104

## Contexto

O aplicativo mantém contas locais em SQLite e valida o acesso no próprio processo desktop. O requisito RNF104 permite Argon2id, bcrypt ou scrypt e proíbe armazenar senhas em texto puro. O código atual gera hashes scrypt com salt individual e atualiza hashes PBKDF2 legados após um login válido.

## Problema

Senhas em texto puro ou hashes rápidos sem salt adequado seriam vulneráveis caso o arquivo local fosse copiado. A escolha de um algoritmo também precisa ser compatível com as bibliotecas padrão disponíveis no ambiente Python do protótipo.

## Decisão

Usar `hashlib.scrypt` com salt aleatório individual para novos cadastros e redefinições de senha. Manter temporariamente a validação dos hashes PBKDF2 legados e atualizá-los para scrypt após autenticação bem-sucedida.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Armazenar senha em texto puro | Proibido pelo requisito e expõe diretamente a senha se o banco for lido. |
| PBKDF2 para todas as novas senhas | Já existia em registros legados, mas foi substituído por uma opção permitida pelo requisito e disponível na biblioteca padrão. |
| Argon2id ou bcrypt | Também atendem ao requisito, mas exigiriam outra dependência para este protótipo. |
| scrypt da biblioteca padrão | Adotado para atender ao requisito sem adicionar dependência de hash externa. |

## Consequências

**Positivas**
- Senhas não são armazenadas em texto puro.
- Cada senha recebe um salt individual.
- Novos cadastros usam um algoritmo aceito pelo requisito RNF104 sem instalar pacote adicional.
- Contas antigas podem migrar sem exigir redefinição imediata de senha.

**Negativas e riscos aceitos**
- Contas que nunca autenticarem continuam com o hash legado até o próximo login válido.
- Os parâmetros de custo devem ser revistos conforme desempenho e recomendações de segurança evoluam.
- Como o aplicativo é local, a autenticação não protege o banco contra alguém com controle total do computador e do arquivo.

**Mitigações já existentes**
- O algoritmo utilizado é armazenado junto ao hash para distinguir registros legados.
- O hash legado é atualizado dentro do fluxo de login bem-sucedido.
- O serviço aplica limite de tentativas e respostas genéricas de erro de autenticação.

## Quando reavaliar

Reavaliar se as versões de Python suportadas deixarem de oferecer scrypt, se houver requisito de autenticação centralizada, ou se parâmetros atuais precisarem ser elevados por orientação de segurança ou pelo tempo de resposta observado.
