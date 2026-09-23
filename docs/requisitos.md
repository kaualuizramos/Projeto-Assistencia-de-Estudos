# Especificação de Requisitos do Sistema

## 1. Requisitos Funcionais (RF)

### 1.1 Autenticação e Gestão de Contas
- **RF01:** O Sistema DEVE permitir que um usuário crie uma conta fornecendo nome, e-mail e senha.
- **RF02:** QUANDO o usuário enviar credenciais de autenticação válidas, o Sistema DEVE autenticá-lo e criar uma sessão autenticada.
- **RF03:** SE as credenciais de autenticação forem inválidas, ENTÃO o Sistema DEVE negar o acesso e exibir uma mensagem de erro de autenticação.
- **RF04:** O Sistema NÃO PODE permitir que um usuário não autenticado acesse recursos protegidos.
- **RF34:** QUANDO o usuário solicitar a recuperação de senha, o Sistema DEVE enviar um mecanismo de recuperação para o e-mail cadastrado.
- **RF35:** QUANDO o usuário solicitar a exclusão da conta, o Sistema DEVE exigir confirmação antes de excluí-la.
- **RF36:** SE o usuário confirmar a exclusão da conta, ENTÃO o Sistema DEVE excluir ou anonimizar seus dados de acordo com a política de retenção de dados da aplicação.
- **RF37:** O Sistema NÃO PODE permitir que um usuário acesse, modifique ou exclua tarefas, conversas ou sessões de foco de outro usuário.

### 1.2 Gestão de Tarefas
- **RF05:** QUANDO um usuário autenticado criar uma tarefa, o Sistema DEVE armazená-la e atribuir-lhe um identificador único.
- **RF06:** O Sistema DEVE permitir que o usuário informe título, descrição, prioridade e prazo ao criar ou editar uma tarefa.
- **RF07:** SE um campo obrigatório da tarefa estiver ausente, ENTÃO o Sistema DEVE rejeitar o envio e identificar a informação faltante.
- **RF08:** O Sistema DEVE permitir que o usuário edite uma tarefa existente pertencente ao usuário autenticado.
- **RF09:** O Sistema DEVE permitir que o usuário exclua uma tarefa existente pertencente ao usuário autenticado.
- **RF10:** QUANDO o usuário marcar uma tarefa como concluída, o Sistema DEVE alterar o status da tarefa para "Concluída" e registrar a data e hora de conclusão.
- **RF11:** O Sistema DEVE permitir que o usuário crie uma ou mais subtarefas associadas a uma tarefa existente.
- **RF12:** QUANDO todas as subtarefas associadas a uma tarefa forem concluídas, o Sistema DEVE notificar o usuário de que todas as subtarefas foram concluídas.
- **RF27:** O Sistema DEVE permitir que o usuário configure um lembrete para uma tarefa existente.
- **RF28:** QUANDO o horário agendado de um lembrete ativo for atingido, o Sistema DEVE enviar uma notificação ao usuário.
- **RF29:** SE o prazo de uma tarefa tiver passado e a tarefa permanecer incompleta, ENTÃO o Sistema DEVE identificá-la como atrasada.
- **RF32:** O Sistema DEVE permitir que o usuário filtre tarefas por status, prioridade e prazo.

### 1.3 Assistente de Produtividade (IA)
- **RF13:** O Sistema DEVE permitir que o usuário inicie uma conversa com o assistente de produtividade.
- **RF14:** QUANDO o usuário enviar uma mensagem através do chat, o Sistema DEVE enviá-la ao serviço de IA configurado para processamento.
- **RF15:** QUANDO o serviço de IA retornar uma resposta, o Sistema DEVE exibi-la na conversa atual.
- **RF16:** SE o serviço de IA falhar ao processar uma mensagem, ENTÃO o Sistema DEVE exibir uma mensagem de erro e NÃO DEVE descartar a mensagem do usuário.
- **RF17:** ENQUANTO uma conversa estiver ativa, o Sistema DEVE manter o contexto necessário para gerar respostas contextuais.
- **RF18:** O Sistema DEVE armazenar o histórico de conversas do usuário associado à sua conta.
- **RF19:** QUANDO o usuário descrever uma tarefa complexa ao assistente, o Sistema DEVE permitir que o assistente sugira subtarefas menores com base nas informações fornecidas.
- **RF20:** QUANDO o usuário solicitar ajuda para iniciar uma tarefa, o Sistema DEVE permitir que o assistente sugira uma próxima ação concreta.
- **RF21:** O Sistema DEVE permitir que o usuário aceite, modifique ou rejeite uma subtarefa sugerida antes de adicioná-la à sua lista de tarefas.

### 1.4 Sessões de Foco
- **RF22:** QUANDO o usuário iniciar uma sessão de foco, o Sistema DEVE associar a sessão a uma tarefa selecionada e iniciar o cronômetro de foco.
- **RF23:** ENQUANTO uma sessão de foco estiver ativa, o Sistema DEVE exibir o tempo decorrido ou restante.
- **RF24:** O Sistema DEVE permitir que o usuário pause, retome e encerre uma sessão de foco ativa.
- **RF25:** QUANDO uma sessão de foco for encerrada, o Sistema DEVE registrar seu horário de início, horário de término, duração e tarefa associada.
- **RF26:** SE o cronômetro de foco atingir a duração configurada, ENTÃO o Sistema DEVE notificar o usuário e alterar o status da sessão para "Concluída".

### 1.5 Painel e Histórico
- **RF30:** QUANDO o usuário acessar o painel de progresso, o Sistema DEVE exibir o número de tarefas concluídas, pendentes e atrasadas.
- **RF31:** O Sistema DEVE exibir o número e a duração total das sessões de foco concluídas nas informações de progresso do usuário.
- **RF33:** O Sistema DEVE permitir que o usuário visualize seu histórico de tarefas e histórico de sessões de foco.

---

## 2. Requisitos Não-Funcionais (RNF)

| Código | Categoria | Descrição |
| :--- | :--- | :--- |
| **RNF01** | Desempenho | O Sistema DEVE processar pelo menos 95% das requisições padrão de API em até 2 segundos sob carga normal definida. |
| **RNF02** | Desempenho | QUANDO uma resposta for recebida do serviço externo de IA, o Sistema DEVE exibi-la ao usuário em até 1 segundo. |
| **RNF03** | Disponibilidade | O Sistema DEVE fornecer pelo menos 99% de disponibilidade mensal, excluindo períodos de manutenção programada. |
| **RNF04** | Segurança | O Sistema DEVE armazenar as senhas dos usuários utilizando um algoritmo criptográfico seguro de hash. |
| **RNF05** | Segurança | O Sistema NÃO PODE armazenar senhas de usuários em texto claro. |
| **RNF06** | Segurança | O Sistema DEVE utilizar HTTPS para toda a comunicação entre o cliente e os serviços de backend. |
| **RNF07** | Segurança | SE um usuário tentar acessar um recurso protegido sem autenticação, ENTÃO o Sistema DEVE negar a requisição. |
| **RNF08** | Segurança | SE um usuário tentar acessar um recurso pertencente a outro usuário, ENTÃO o Sistema DEVE negar a requisição. |
| **RNF09** | Segurança | O Sistema DEVE validar e sanitizar todas as entradas fornecidas pelo usuário antes de processá-las ou armazená-las. |
| **RNF10** | Segurança | O Sistema DEVE implementar limitação de taxa (*rate limiting*) nos endpoints de autenticação. |
| **RNF11** | Segurança | ENQUANTO a sessão do usuário estiver ativa, o Sistema DEVE aplicar regras de autorização para cada requisição de recurso protegido. |
| **RNF12** | Privacidade | O Sistema DEVE processar dados pessoais de acordo com a legislação aplicável, incluindo a LGPD brasileira. |
| **RNF13** | Privacidade | O Sistema NÃO PODE expor dados pessoais do usuário a outros usuários sem autorização explícita. |
| **RNF14** | Privacidade | QUANDO um usuário solicitar a exclusão da conta, o Sistema DEVE executar o processo de exclusão ou anonimização definido pela política de retenção. |
| **RNF15** | Confiabilidade | O Sistema DEVE persistir os dados da tarefa antes de confirmar a criação bem-sucedida ao usuário. |
| **RNF16** | Confiabilidade | O Sistema DEVE preservar os dados persistidos das tarefas após a reinicialização da aplicação. |
| **RNF17** | Tolerância a falhas | SE o serviço externo de IA ficar indisponível, ENTÃO o Sistema DEVE continuar fornecendo as funcionalidades de gestão de tarefas e sessões de foco. |
| **RNF18** | Tolerância a falhas | SE uma requisição externa de IA falhar, ENTÃO o Sistema DEVE informar ao usuário que o serviço de IA está temporariamente indisponível. |
| **RNF19** | Tolerância a falhas | O Sistema NÃO PODE perder tarefas, subtarefas ou sessões de foco previamente persistidas devido a falhas no serviço externo de IA. |
| **RNF20** | Usabilidade | O Sistema DEVE permitir que um usuário iniciante crie uma tarefa e envie uma mensagem no chat sem exigir documentação de treinamento externa. |
| **RNF21** | Acessibilidade | O Sistema DEVE suportar navegação por teclado para todos os elementos interativos principais. |
| **RNF22** | Acessibilidade | O Sistema DEVE fornecer alternativas em texto para elementos significativos não textuais da interface. |
| **RNF23** | Responsividade | O Sistema DEVE fornecer uma interface utilizável para larguras de tela de 360 pixels a 1920 pixels. |
| **RNF24** | Compatibilidade | O Sistema DEVE suportar as duas versões estáveis mais recentes do Google Chrome, Mozilla Firefox, Microsoft Edge e Safari. |
| **RNF25** | Manutenibilidade | O Sistema DEVE separar as responsabilidades de autenticação, gestão de tarefas, chat, sessão de foco e notificações em módulos independentes. |
| **RNF26** | Testabilidade | O Sistema DEVE fornecer testes automatizados para todas as operações críticas de negócio. |
| **RNF27** | Observabilidade | O Sistema DEVE registrar erros da aplicação e eventos relevantes sem armazenar senhas, tokens de autenticação ou chaves de API nos logs. |
| **RNF28** | Segurança | O Sistema NÃO PODE expor chaves de API da IA externa ou outras credenciais de serviços no código do lado do cliente (*client-side*). |
| **RNF29** | Escalabilidade | O Sistema DEVE suportar pelo menos 100 usuários autenticados concorrentes mantendo o requisito de desempenho definido no RNF01. |
| **RNF30** | Integração | O Sistema DEVE isolar a comunicação com serviços externos por meio de componentes de integração dedicados. |