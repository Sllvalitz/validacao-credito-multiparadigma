from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

DESTINO = Path(__file__).resolve().parent / "propostas.json"
TOTAL_DE_REGISTROS = 60
# semente fixa: todos os integrantes geram exatamente o mesmo dataset
SEMENTE = 42


def registro(idade: Any, renda: Any, historico: Any, valor: Any, prazo: Any) -> dict[str, Any]:
    return {
        "id": "",
        "idade": idade,
        "renda_mensal": renda,
        "historico_credito": historico,
        "valor_solicitado": valor,
        "prazo": prazo,
    }


def casos_aceitos_no_limite() -> list[dict[str, Any]]:
    return [
        registro(30, 3500.00, "bom", 4200.00, 12),  # exemplo do contrato: parcela final 385.06
        registro(25, 1500.00, "bom", 4000.00, 12),  # renda exatamente no minimo
        registro(40, 3000.00, "regular", 10800.00, 12),  # comprometimento exatamente 30%
        registro(18, 2500.00, "bom", 3000.00, 6),  # idade exatamente 18
        registro(35, 4000.00, "ruim", 7200.00, 12),  # historico ruim com 15%: aceito, risco alto
        registro(45, 10000.00, "bom", 36000.00, 12),  # limite pela renda passaria do teto de R$ 20.000
        registro(28, 2000.00, "regular", 2400.00, 12),  # regular com 10%: risco medio
        registro(28, 2000.00, "regular", 6000.00, 12),  # regular com 25%: risco alto
    ]


def casos_reprovados_por_regra() -> list[dict[str, Any]]:
    return [
        registro(17, 2500.00, "bom", 3000.00, 6),  # menor de idade
        registro(30, 1499.99, "bom", 1000.00, 6),  # renda 1 centavo abaixo do minimo
        registro(30, 5000.00, "bom", 6000.00, 24),  # prazo fora de 6 e 12: o Prolog reprova
        registro(35, 4000.00, "ruim", 9600.00, 12),  # historico ruim com 20%: acima do limite de 15%
        registro(33, 3000.00, "regular", 11000.00, 12),  # comprometimento de 30,56%
        registro(50, 6000.00, "excelente", 5000.00, 6),  # historico fora do dominio
        registro(29, 3000.00, "bom", 9000.00, 6),  # comprometimento de 50%
    ]


def casos_com_erro_de_validacao() -> list[dict[str, Any]]:
    sem_prazo = registro(30, 3000.00, "bom", 3000.00, 12)
    del sem_prazo["prazo"]
    return [
        sem_prazo,  # chave obrigatoria ausente
        registro(30, "abc", "bom", 3000.00, 12),  # tipo incompativel
        registro(30, 0, "bom", 3000.00, 12),  # renda zero
        registro(30, 3000.00, "bom", 3000.00, 0),  # prazo zero: evita divisao por zero na parcela
        registro(-5, 3000.00, "bom", 3000.00, 12),  # idade negativa
        registro(30, 3000.00, "bom", -100.00, 12),  # valor solicitado negativo
    ]


def casos_aleatorios(quantidade: int) -> list[dict[str, Any]]:
    sorteio = random.Random(SEMENTE)
    casos = []
    for _ in range(quantidade):
        renda = round(sorteio.uniform(1200, 12000), 2)
        prazo = sorteio.choice([6, 12])
        # comprometimento sorteado de 5% a 40%, para gerar aprovados e reprovados por comprometimento
        comprometimento = sorteio.uniform(5, 40)
        valor = round(renda * comprometimento / 100 * prazo, 2)
        # bom e regular aparecem duas vezes: historico ruim e menos frequente
        historico = sorteio.choice(["bom", "bom", "regular", "regular", "ruim"])
        casos.append(registro(sorteio.randint(17, 70), renda, historico, valor, prazo))
    return casos


# ids sequenciais atribuidos no fim, no formato PROP-NNN exigido pelo contrato
def numerar(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for posicao, item in enumerate(registros, start=1):
        item["id"] = f"PROP-{posicao:03d}"
    return registros


def main() -> None:
    fixos = (casos_aceitos_no_limite()
             + casos_reprovados_por_regra()
             + casos_com_erro_de_validacao())
    registros = numerar(fixos + casos_aleatorios(TOTAL_DE_REGISTROS - len(fixos)))
    DESTINO.write_text(json.dumps(registros, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(registros)} registros gravados em {DESTINO}")


if __name__ == "__main__":
    main()
