# Responsavel: Anderson da Silva Pinto
from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from python.dominio import ErroIntegracao

# caminhos montados a partir da raiz do projeto: funcionam mesmo se o main for chamado de outra pasta
RAIZ = Path(__file__).resolve().parent.parent


# heranca justificada: Prolog e Lisp compartilham a execucao do subprocesso, o timeout e a
# validacao do JSON; as subclasses so definem quais chaves a resposta deve ter (polimorfismo)
class ModuloExterno(ABC):
    def __init__(self, comando: list[str], timeout: float = 10.0) -> None:
        self._comando = comando
        self._timeout = timeout

    @property
    @abstractmethod
    def chaves_saida(self) -> tuple[str, ...]:
        raise NotImplementedError

    def executar(self, mensagem: dict[str, Any]) -> dict[str, Any]:
        # o timeout transforma um processo travado em ErroIntegracao; o subprocess.run encerra o filho
        try:
            processo = subprocess.run(self._comando, input=json.dumps(mensagem),
                                      capture_output=True, text=True,
                                      encoding="utf-8", timeout=self._timeout)
        except FileNotFoundError:
            raise ErroIntegracao(f"executavel nao encontrado: {self._comando[0]}") from None
        except subprocess.TimeoutExpired:
            raise ErroIntegracao(f"tempo limite de {self._timeout}s excedido") from None
        # o stderr do filho vai na mensagem para facilitar o diagnostico
        if processo.returncode != 0:
            raise ErroIntegracao(f"codigo de retorno {processo.returncode}: {processo.stderr.strip()}")
        try:
            resposta = json.loads(processo.stdout)
        except json.JSONDecodeError as erro:
            raise ErroIntegracao(f"saida malformada ({erro}); stderr: {processo.stderr.strip()}") from None
        self._validar(resposta, mensagem)
        return resposta

    def _validar(self, resposta: Any, mensagem: dict[str, Any]) -> None:
        if not isinstance(resposta, dict):
            raise ErroIntegracao("resposta nao e um objeto JSON")
        ausentes = [chave for chave in self.chaves_saida if chave not in resposta]
        if ausentes:
            raise ErroIntegracao("resposta sem as chaves: " + ", ".join(ausentes))
        # conferir o id evita associar a resposta de um processo a outra proposta
        if resposta["id"] != mensagem["id"]:
            raise ErroIntegracao(f"id divergente: enviado {mensagem['id']!r}, recebido {resposta['id']!r}")


class ModuloProlog(ModuloExterno):
    @property
    def chaves_saida(self) -> tuple[str, ...]:
        return ("id", "elegivel", "regras_satisfeitas", "impedimentos")


class ModuloLisp(ModuloExterno):
    @property
    def chaves_saida(self) -> tuple[str, ...]:
        return ("id", "status", "classificacao_risco", "taxa_juros_mensal",
                "limite_calculado", "valor_aprovado", "valor_parcela_final")


def criar_modulo_prolog(timeout: float = 10.0) -> ModuloProlog:
    # -q silencia o banner, -g main executa main/0 e -t halt encerra ao terminar
    return ModuloProlog(["swipl", "-q", "-g", "main", "-t", "halt",
                         str(RAIZ / "prolog" / "elegibilidade.pl")], timeout)


def criar_modulo_lisp(timeout: float = 20.0) -> ModuloLisp:
    # timeout maior: na primeira execucao o SBCL compila o yason antes de responder
    return ModuloLisp(["sbcl", "--script", str(RAIZ / "lisp" / "precificacao.lisp")], timeout)
