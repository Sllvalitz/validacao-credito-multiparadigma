<!-- Responsavel: Robson -->
# Validação de crédito multiparadigma

Trabalho final de Laboratório de Programação 2026/2 (opção 2: validação de crédito).

O sistema lê propostas de crédito (dados fictícios), verifica a elegibilidade, calcula o risco, a taxa de juros, o limite e a parcela. Cada linguagem cuida de um paradigma:

| Linguagem | Paradigma | Responsabilidade |
|---|---|---|
| Python | Orientado a objetos | Orquestra o fluxo, valida a entrada e consolida o resultado |
| Prolog (SWI-Prolog) | Lógico | Elegibilidade e compliance |
| Common Lisp (SBCL) | Funcional | Precificação: risco, taxa, limite, valor aprovado e parcela (Tabela Price) |

## Fluxo

1. O Python lê uma proposta e valida o esquema (erros viram `ERRO_VALIDACAO`).
2. O Python envia a proposta ao Prolog (JSON via `stdin`/`stdout`, uma proposta por execução).
3. Se o Prolog devolver `"elegivel": false`, o status final é `REPROVADO` e o Lisp **não** é acionado.
4. Se for elegível, o Python envia a proposta ao Lisp, que devolve a precificação (`APROVADO` ou `APROVADO_COM_CONDICOES`).
5. Falhas de processo, timeout ou resposta inválida viram `ERRO_INTEGRACAO`. Um registro com erro nunca interrompe o lote.

O contrato completo das mensagens e as decisões de negócio estão em [`docs/contrato_json.md`](docs/contrato_json.md).

## Estrutura

```
main.py                    ponto de entrada único
python/dominio.py          classes de domínio e validações
python/integracao.py       chamadas aos processos externos
python/orquestrador.py     fluxo Prolog -> Lisp
python/tests/              testes unitarios e de integração
prolog/elegibilidade.pl    módulo lógico
lisp/precificacao.lisp     módulo funcional
data/gerar_dataset.py      gerador do dataset
data/propostas.json        dataset (87 registros, com casos de borda)
data/metricas.py           métricas para o relatório
docs/contrato_json.md      contrato JSON
```

## Versões de referência

| Ferramenta | Versão |
|---|---|
| Python | 3.12 |
| SWI-Prolog | 9.0.4 |
| SBCL | 2.2.9 |

## Dependências

- Python: apenas a biblioteca padrão (nenhum `pip install` necessário).
- SWI-Prolog: `library(http/json)`, que já acompanha a instalação.
- SBCL: biblioteca `yason` (JSON em Common Lisp), carregada via ASDF/Quicklisp.
- `swipl` e `sbcl` precisam estar no `PATH`.

## Como executar

Execute todos os comandos na raiz do repositório.

```
python main.py
python main.py --entrada data/propostas.json --saida saida/resultados.json
```

O programa imprime uma linha por proposta, um resumo por status e grava o resultado completo em `saida/resultados.json`.

Exemplo de linha:

```
PROP-001   APROVADO                 risco baixo, aprovado R$ 4200.00, parcela R$ 385.06
```

### Testes

```
python -m unittest discover
```

Os testes que dependem de `swipl` e `sbcl` (ponta a ponta) são ignorados automaticamente quando as ferramentas não estão instaladas. Os demais rodam sempre.

### Dataset

```
python data/gerar_dataset.py
```

Regenera `data/propostas.json` de forma determinística (semente fixa). O dataset tem 87 registros: casos típicos, 30 propostas aleatórias e casos de borda (renda exatamente 1500, comprometimento exatamente 30% e 15%, idade 18 e 17, prazos inválidos, chaves ausentes, tipos errados, valores zero ou negativos, histórico fora do domínio e teto de crédito).

### Métricas

```
python data/metricas.py
python data/metricas.py --casos 10
```

Mostra linhas de código (não vazias), número de funções ou predicados por linguagem, quantidade de testes e o tempo médio de execução (mínimo de 5 casos). A medição de tempo exige `swipl` e `sbcl`. Para Prolog, o número conta os nomes distintos de predicados.

## Equipe

| Integrante | Responsabilidade | Arquivos |
|---|---|---|
| Anderson | Líder, orquestrador e integração | `main.py`, `python/orquestrador.py`, `python/integracao.py`, `docs/contrato_json.md`, `.gitignore` |
| Lucy | Classes de domínio em Python e testes unitários | `python/dominio.py`, `python/tests/test_dominio.py` |
| Chico | Módulo lógico em Prolog | `prolog/elegibilidade.pl` |
| Isabelle | Módulo funcional em Common Lisp | `lisp/precificacao.lisp` |
| Robson | Dados, testes de integração, métricas e README | `data/gerar_dataset.py`, `data/propostas.json`, `data/metricas.py`, `python/tests/test_orquestrador.py`, `README.md` |

## Limitações conhecidas

- O limite de 30% de comprometimento vale para a parcela base (sem juros). A parcela final com juros pode passar de 30% da renda e ainda assim é aceita nesta versão.
- O prazo aceito é apenas 6 ou 12 meses.
