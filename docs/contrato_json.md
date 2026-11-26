<!-- Responsavel: Anderson da Silva Pinto. Mudancas exigem aprovacao dos 5 integrantes. -->
# Contrato de Integração JSON — v1.1

Todas as mensagens: JSON em UTF-8, uma por execução, via `stdin` (entrada) e `stdout` (saída).
Chaves sem acentuação. Mudanças deste documento exigem aprovação dos 5 integrantes.

## O que mudou da v1.0
- IDs padronizados como `PROP-001` (a tabela da v1.0 dizia `PROP001`; os exemplos já usavam `PROP-001`).
- Decisões de negócio fechadas (seção 1).
- Comprometimento da renda arredondado a 4 casas para evitar ruído de ponto flutuante.
- Chaves do tratamento de erros mantidas.

## 1. Decisões de negócio (aprovadas pela equipe: ☐ Anderson ☐ Lucy ☐ Pedro ☐ Isabelle ☐ Robson)

| Tema | Decisão |
|---|---|
| Juros | **Compostos, Tabela Price**: `PMT = V·i / (1 − (1+i)^−n)`. Confere com o exemplo do contrato (4200, 12x, 1,5% a.m. → 385,06) |
| Teto de crédito | R$ 20.000,00 |
| Histórico `bom` / `regular` | Aceitos |
| Histórico `ruim` | Aceito só se comprometimento ≤ 15% (cai em risco alto) |
| Risco **baixo** | `bom` e comprometimento ≤ 20% |
| Risco **alto** | `ruim`, ou `regular` com comprometimento > 20% |
| Risco **médio** | demais casos |
| Status | Risco alto → `APROVADO_COM_CONDICOES`; demais → `APROVADO` |
| Prazo | 6 ou 12. Outros valores positivos são **reprovados pelo Prolog** (`prazo_invalido`); prazo ≤ 0 é `ERRO_VALIDACAO` |
| Parcela final > 30% da renda | **Aceito** nesta versão: o limite de 30% vale para a parcela base (sem juros). Registrar como limitação no relatório |

## 2. Entrada: `data/propostas.json` (lista, ≥ 50 registros)

| Chave | Tipo | Regra |
|---|---|---|
| `id` | string | único, formato `PROP-001` |
| `idade` | int | elegível se ≥ 18 |
| `renda_mensal` | float | elegível se ≥ 1500.00 |
| `historico_credito` | string | `"bom"`, `"regular"` ou `"ruim"` |
| `valor_solicitado` | float | > 0 |
| `prazo` | int | 6 ou 12 |

## 3. Fronteira 1: Python → Prolog

Python calcula `parcela_base = valor_solicitado / prazo` e
`comprometimento_percentual = parcela_base / renda_mensal × 100`.

**Entrada:** `id`, `idade`, `renda_mensal`, `historico_credito`, `prazo`, `parcela_base`, `comprometimento_percentual`.

**Saída:** `id`, `elegivel` (bool), `regras_satisfeitas` (list[string]), `impedimentos` (list[string]).

Nomes dos critérios (`regras_satisfeitas`) → impedimento correspondente:

| Critério | Impedimento |
|---|---|
| `renda_minima` | `renda_abaixo_do_minimo` |
| `idade_minima` | `idade_abaixo_do_minimo` |
| `prazo_valido` | `prazo_invalido` |
| `historico_aceito` | `historico_nao_aceito` |
| `comprometimento_renda` | `comprometimento_acima_30_porcento` |

`elegivel = true` ⇔ `impedimentos == []`. Se `false`, Python encerra com `"REPROVADO"` **sem acionar o Lisp**.

```json
{"id":"PROP-001","idade":30,"renda_mensal":3500.0,"historico_credito":"bom","prazo":12,"parcela_base":350.0,"comprometimento_percentual":10.0}
{"id":"PROP-001","elegivel":true,"regras_satisfeitas":["renda_minima","idade_minima","prazo_valido","historico_aceito","comprometimento_renda"],"impedimentos":[]}
```

## 4. Fronteira 2: Python → Lisp (só se elegível)

**Entrada:** `id`, `renda_mensal`, `historico_credito`, `valor_solicitado`, `prazo`, `comprometimento_percentual`.

**Saída:** `id`, `status`, `classificacao_risco` (`baixo`/`medio`/`alto`), `taxa_juros_mensal` (0.015 / 0.025 / 0.035),
`limite_calculado` = min(renda × 0,30 × prazo, teto), `valor_aprovado` = min(valor_solicitado, limite_calculado),
`valor_parcela_final` (Price sobre `valor_aprovado`). Valores monetários com 2 casas.

```json
{"id":"PROP-001","renda_mensal":3500.0,"historico_credito":"bom","valor_solicitado":4200.0,"prazo":12,"comprometimento_percentual":10.0}
{"id":"PROP-001","status":"APROVADO","classificacao_risco":"baixo","taxa_juros_mensal":0.015,"limite_calculado":12600.0,"valor_aprovado":4200.0,"valor_parcela_final":385.06}
```

## 5. Tratamento de erros

| Falha | Onde | Tratamento | Status |
|---|---|---|---|
| Chave ausente / tipo errado | Entrada → Python | `Proposta.de_registro` valida o esquema | `ERRO_VALIDACAO` |
| renda ≤ 0, prazo ≤ 0, idade < 0, valor ≤ 0 | Entrada → Python | Bloqueio nas classes de domínio | `ERRO_VALIDACAO` |
| Saída malformada / chaves faltando / `id` divergente | Prolog/Lisp → Python | `ModuloExterno._validar`; stderr registrado | `ERRO_INTEGRACAO` |
| Código de retorno ≠ 0, timeout, executável ausente | Python → swipl/sbcl | `subprocess.run(timeout=...)` | `ERRO_INTEGRACAO` |

Um registro com erro nunca interrompe o lote.
