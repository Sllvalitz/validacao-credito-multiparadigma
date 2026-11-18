# Responsavel: Anderson
"""Fronteiras com os processos externos (SWI-Prolog e SBCL) via JSON em stdin/stdout.

Heranca justificada: ModuloExterno concentra o que Prolog e Lisp tem em comum
(rodar subprocesso, timeout, parse do JSON, validar a resposta). Cada subclasse
so diz QUAL comando roda e QUAIS chaves a resposta deve ter (polimorfismo).
"""
from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from python.dominio import ErroIntegracao

RAIZ = Path(__file__).resolve().parent.parent


class ModuloExterno(ABC):
    def __init__(self, comando: list[str], timeout: float = 10.0) -> None:
        self._comando = comando
        self._timeout = timeout

    @property
    @abstractmethod
    def chaves_saida(self) -> tuple[str, ...]:
        """Chaves obrigatorias na resposta, conforme o contrato."""

    def executar(self, mensagem: dict[str, Any]) -> dict[str, Any]:
        try:
            # subprocess.run mata o processo filho ao estourar o timeout.
            proc = subprocess.run(self._comando, input=json.dumps(mensagem),
                                  capture_output=True, text=True,
                                  encoding="utf-8", timeout=self._timeout)
        except FileNotFoundError:
            raise ErroIntegracao(f"executavel nao encontrado: {self._comando[0]}") from None
        except subprocess.TimeoutExpired:
            raise ErroIntegracao(f"tempo limite de {self._timeout}s excedido") from None
        if proc.returncode != 0:
            raise ErroIntegracao(f"codigo de retorno {proc.returncode}: {proc.stderr.strip()}")
        try:
            resposta = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise ErroIntegracao(f"saida malformada ({e}); stderr: {proc.stderr.strip()}") from None
        self._validar(resposta, mensagem)
        return resposta

    def _validar(self, resposta: Any, mensagem: dict[str, Any]) -> None:
        if not isinstance(resposta, dict):
            raise ErroIntegracao("resposta nao e um objeto JSON")
        ausentes = [c for c in self.chaves_saida if c not in resposta]
        if ausentes:
            raise ErroIntegracao("resposta sem as chaves: " + ", ".join(ausentes))
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
    return ModuloProlog(["swipl", "-q", "-g", "main", "-t", "halt",
                         str(RAIZ / "prolog" / "elegibilidade.pl")], timeout)


def criar_modulo_lisp(timeout: float = 20.0) -> ModuloLisp:
    # Timeout maior: na primeira execucao o ASDF compila o yason.
    return ModuloLisp(["sbcl", "--script", str(RAIZ / "lisp" / "precificacao.lisp")], timeout)
