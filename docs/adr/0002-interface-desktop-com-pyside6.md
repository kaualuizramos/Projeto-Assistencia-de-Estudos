# ADR 0002: Interface desktop com PySide6 e Qt Widgets

- **Status:** Aceito
- **Data:** 2026-11-04
- **Referência:** Commit a6b9b43

## Contexto

O Estuda+ é um aplicativo local para computadores, com telas de autenticação, tarefas, foco, chat, notificações, histórico e administração. A primeira versão usava Tkinter. A interface foi posteriormente modernizada com PySide6 e Qt Widgets, mantendo Python como linguagem e `app.py` como ponto de entrada.

## Problema

Era necessário oferecer uma interface gráfica apropriada para desktop, com controles nativos, navegação entre áreas e possibilidade de executar chamadas demoradas à IA sem congelar a janela.

## Decisão

Usar PySide6 com Qt Widgets para a interface desktop. Manter a composição das telas em `estuda/ui.py`, iniciar a aplicação por `app.py` e executar as chamadas ao chat em uma thread Qt para preservar a resposta da interface.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Tkinter | Era a tecnologia inicial, mas não atendia à direção de modernização visual solicitada para o protótipo. |
| Aplicação web | Não atende à restrição explícita de entregar um programa desktop local. |
| PySide6 com Qt Widgets | Adotada por fornecer controles e janelas desktop em Python e permitir o uso de threads Qt. |

## Consequências

**Positivas**
- Interface gráfica nativa para computador, sem navegador.
- Controles, navegação e estilos podem ser implementados com Qt Widgets e QSS.
- O trabalho de rede do chat pode ocorrer fora da thread da interface.

**Negativas e riscos aceitos**
- PySide6 passa a ser uma dependência de execução e precisa ser instalada no ambiente Python.
- A interface permanece concentrada em um módulo grande, o que pode dificultar manutenção à medida que o produto cresce.
- A aparência pode variar um pouco entre sistemas operacionais e versões do Qt.

**Mitigações já existentes**
- `requirements.txt` declara `PySide6-Essentials`.
- `app.py` centraliza a inicialização da aplicação Qt.
- O serviço de chat e a integração de IA ficam fora da lógica visual, e a solicitação é executada em `QThread`.

## Quando reavaliar

Reavaliar se o aplicativo precisar suportar uma interface web ou móvel, se a distribuição desktop exigir um framework mais simples de empacotar, ou se `estuda/ui.py` ficar difícil de manter em um único módulo.
