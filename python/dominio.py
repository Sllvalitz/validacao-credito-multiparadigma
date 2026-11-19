# Responsavel: Lucy
from __future__ import annotations

import math
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class ErroCredito(Exception):
    pass


class ErroValidacao(ErroCredito):
    pass


class ErroIntegracao(ErroCredito):
    pass


def _exigir_chave(registro: dict[str, Any], chave: str) -> Any:
    if chave not in registro:
        raise ErroValidacao(f"chave ausente: {chave}")
    return registro[chave]


def _exigir_texto(valor: Any, nome: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ErroValidacao(f"{nome} deve ser um texto nao vazio")
    return valor


def _exigir_inteiro(valor: Any, nome: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ErroValidacao(f"{nome} deve ser um numero inteiro")
    return valor


def _exigir_numero(valor: Any, nome: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErroValidacao(f"{nome} deve ser um numero")
    if not math.isfinite(valor):
        raise ErroValidacao(f"{nome} deve ser um numero finito")
    return float(valor)


class Cliente:
    def __init__(self, idade: int, renda_mensal: float, historico_credito: str) -> None:
        self._idade = _exigir_inteiro(idade, "idade")
        if self._idade < 0:
            raise ErroValidacao("idade nao pode ser negativa")
        self._renda_mensal = _exigir_numero(renda_mensal, "renda_mensal")
        if self._renda_mensal <= 0:
            raise ErroValidacao("renda_mensal deve ser maior que zero")
        self._historico_credito = _exigir_texto(historico_credito, "historico_credito")

    @property
    def idade(self) -> int:
        return self._idade

    @property
    def renda_mensal(self) -> float:
        return self._renda_mensal

    @property
    def historico_credito(self) -> str:
        return self._historico_credito


class Proposta:
    def __init__(self, id_proposta: str, cliente: Cliente,
                 valor_solicitado: float, prazo: int) -> None:
        self._id_proposta = _exigir_texto(id_proposta, "id")
        self._cliente = cliente
        self._valor_solicitado = _exigir_numero(valor_solicitado, "valor_solicitado")
        if self._valor_solicitado <= 0:
            raise ErroValidacao("valor_solicitado deve ser maior que zero")
        self._prazo = _exigir_inteiro(prazo, "prazo")
        if self._prazo <= 0:
            raise ErroValidacao("prazo deve ser maior que zero")

    @classmethod
    def de_registro(cls, registro: Any) -> Proposta:
        if not isinstance(registro, dict):
            raise ErroValidacao("registro deve ser um objeto JSON")
        id_proposta = _exigir_chave(registro, "id")
        idade = _exigir_chave(registro, "idade")
        renda_mensal = _exigir_chave(registro, "renda_mensal")
        historico_credito = _exigir_chave(registro, "historico_credito")
        valor_solicitado = _exigir_chave(registro, "valor_solicitado")
        prazo = _exigir_chave(registro, "prazo")
        cliente = Cliente(idade, renda_mensal, historico_credito)
        return cls(id_proposta, cliente, valor_solicitado, prazo)

    @property
    def id_proposta(self) -> str:
        return self._id_proposta

    @property
    def cliente(self) -> Cliente:
        return self._cliente

    @property
    def valor_solicitado(self) -> float:
        return self._valor_solicitado

    @property
    def prazo(self) -> int:
        return self._prazo

    @property
    def parcela_base(self) -> float:
        return self._valor_solicitado / self._prazo

    @property
    def comprometimento_percentual(self) -> float:
        return round(self.parcela_base / self._cliente.renda_mensal * 100, 4)

    def para_prolog(self) -> dict[str, Any]:
        return {
            "id": self._id_proposta,
            "idade": self._cliente.idade,
            "renda_mensal": self._cliente.renda_mensal,
            "historico_credito": self._cliente.historico_credito,
            "prazo": self._prazo,
            "parcela_base": self.parcela_base,
            "comprometimento_percentual": self.comprometimento_percentual,
        }

    def para_lisp(self) -> dict[str, Any]:
        return {
            "id": self._id_proposta,
            "renda_mensal": self._cliente.renda_mensal,
            "historico_credito": self._cliente.historico_credito,
            "valor_solicitado": self._valor_solicitado,
            "prazo": self._prazo,
            "comprometimento_percentual": self.comprometimento_percentual,
        }


class AnaliseRisco:
    def __init__(self, id_proposta: str) -> None:
        self._id_proposta = id_proposta
        self._status = "PENDENTE"
        self._impedimentos: list[str] = []
        self._precificacao: dict[str, Any] | None = None
        self._erro: str | None = None

    @property
    def id_proposta(self) -> str:
        return self._id_proposta

    @property
    def status(self) -> str:
        return self._status

    @property
    def aprovada(self) -> bool:
        return self._precificacao is not None

    @property
    def valor_aprovado(self) -> float:
        if self._precificacao is None:
            return 0.0
        return float(self._precificacao["valor_aprovado"])

    def reprovar(self, impedimentos: list[str]) -> None:
        self._status = "REPROVADO"
        self._impedimentos = list(impedimentos)
        self._precificacao = None
        self._erro = None

    def aprovar(self, precificacao: dict[str, Any]) -> None:
        self._status = precificacao["status"]
        self._impedimentos = []
        self._precificacao = dict(precificacao)
        self._erro = None

    def registrar_erro(self, status: str, mensagem: str) -> None:
        self._status = status
        self._impedimentos = []
        self._precificacao = None
        self._erro = mensagem

    def para_dict(self) -> dict[str, Any]:
        return {
            "id": self._id_proposta,
            "status": self._status,
            "impedimentos": list(self._impedimentos),
            "precificacao": None if self._precificacao is None else dict(self._precificacao),
            "erro": self._erro,
        }


def _intercalar(esquerda: list[T], direita: list[T], chave: Callable[[T], float]) -> list[T]:
    resultado: list[T] = []
    i = 0
    j = 0
    while i < len(esquerda) and j < len(direita):
        if chave(esquerda[i]) <= chave(direita[j]):
            resultado.append(esquerda[i])
            i += 1
        else:
            resultado.append(direita[j])
            j += 1
    resultado.extend(esquerda[i:])
    resultado.extend(direita[j:])
    return resultado


def merge_sort(itens: list[T], chave: Callable[[T], float]) -> list[T]:
    if len(itens) <= 1:
        return list(itens)
    meio = len(itens) // 2
    return _intercalar(merge_sort(itens[:meio], chave), merge_sort(itens[meio:], chave), chave)


def ordenar_aprovadas_por_valor(analises: list[AnaliseRisco]) -> list[AnaliseRisco]:
    aprovadas = [analise for analise in analises if analise.aprovada]
    return merge_sort(aprovadas, lambda analise: analise.valor_aprovado)
