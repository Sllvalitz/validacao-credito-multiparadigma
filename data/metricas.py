# Responsavel: Robson Gabriel de Oliveira Lima
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_DATASET = RAIZ / "data" / "propostas.json"
# .git e __pycache__ nao sao codigo da equipe e saida/ e gerada a cada execucao
PASTAS_IGNORADAS = {".git", "__pycache__", "saida"}
MINIMO_DE_CASOS = 5
LINGUAGENS = (("Python", "*.py"), ("Prolog", "*.pl"), ("Lisp", "*.lisp"))
# um predicado e um nome distinto no inicio de linha: varias clausulas do mesmo nome contam uma vez
PADRAO_CLAUSULA_PROLOG = re.compile(r"^([a-z][A-Za-z0-9_]*)")
PADRAO_DEFUN_LISP = re.compile(r"\(defun\s", re.IGNORECASE)
PADRAO_TESTE = re.compile(r"^\s+def test_", re.MULTILINE)


def listar_arquivos(padrao: str) -> list[Path]:
    return sorted(
        caminho for caminho in RAIZ.rglob(padrao)
        if not PASTAS_IGNORADAS.intersection(caminho.relative_to(RAIZ).parts)
    )


def contar_linhas_de_codigo(caminho: Path) -> int:
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    # linhas em branco e de comentario nao contam como codigo (comentarios: #, % e ;)
    return sum(1 for linha in linhas if linha.strip() and not linha.strip().startswith(("#", "%", ";")))


def contar_funcoes_python(caminho: Path) -> int:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    return sum(isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) for no in ast.walk(arvore))


def nomes_de_predicados_prolog(caminho: Path) -> set[str]:
    nomes = set()
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        correspondencia = PADRAO_CLAUSULA_PROLOG.match(linha)
        if correspondencia:
            nomes.add(correspondencia.group(1))
    return nomes


def contar_funcoes_lisp(caminho: Path) -> int:
    return len(PADRAO_DEFUN_LISP.findall(caminho.read_text(encoding="utf-8")))


def contar_unidades(linguagem: str, arquivos: list[Path]) -> int:
    if linguagem == "Python":
        return sum(contar_funcoes_python(a) for a in arquivos)
    if linguagem == "Prolog":
        return sum(len(nomes_de_predicados_prolog(a)) for a in arquivos)
    return sum(contar_funcoes_lisp(a) for a in arquivos)


def contar_testes() -> int:
    arquivos = sorted((RAIZ / "tests").glob("test_*.py"))
    return sum(len(PADRAO_TESTE.findall(a.read_text(encoding="utf-8"))) for a in arquivos)


def mostrar_metricas_de_codigo() -> None:
    print(f"{'Linguagem':<10} {'Arquivos':>8} {'Linhas':>8} {'Funcoes/predicados':>20}")
    for linguagem, padrao in LINGUAGENS:
        arquivos = listar_arquivos(padrao)
        linhas = sum(contar_linhas_de_codigo(a) for a in arquivos)
        print(f"{linguagem:<10} {len(arquivos):>8} {linhas:>8} {contar_unidades(linguagem, arquivos):>20}")
    print(f"\nTestes unitarios e de integracao: {contar_testes()}")


def escolher_casos(quantidade: int) -> list[dict]:
    registros = [r for r in json.loads(CAMINHO_DATASET.read_text(encoding="utf-8")) if isinstance(r, dict)]
    # amostra espacada pelo dataset (e nao so os primeiros) para misturar aprovados, reprovados e erros
    passo = max(1, len(registros) // quantidade)
    return registros[::passo][:quantidade]


def cronometrar(funcao, *argumentos):
    # perf_counter e um relogio monotonico de alta resolucao, proprio para medir duracoes
    inicio = time.perf_counter()
    resultado = funcao(*argumentos)
    return resultado, time.perf_counter() - inicio


def medir_proposta(caso: dict, prolog, lisp) -> tuple[dict[str, float], str]:
    from python.dominio import ErroValidacao, Proposta

    inicio = time.perf_counter()
    try:
        proposta = Proposta.de_registro(caso)
        indicadores = proposta.para_prolog()
    except ErroValidacao:
        return {"Python": time.perf_counter() - inicio}, "erro de validacao"
    tempos = {"Python": time.perf_counter() - inicio}
    parecer, tempos["Prolog"] = cronometrar(prolog.executar, indicadores)
    if not parecer["elegivel"]:
        return tempos, "reprovada"
    _, tempos["Lisp"] = cronometrar(lisp.executar, proposta.para_lisp())
    return tempos, "aprovada"


def medir_tempos(quantidade: int) -> None:
    # sem as ferramentas a medicao e pulada em vez de falhar
    if shutil.which("swipl") is None or shutil.which("sbcl") is None:
        print("Tempo de execucao: swipl e/ou sbcl nao encontrados, medicao nao realizada")
        return
    sys.path.insert(0, str(RAIZ))
    from python.dominio import Proposta
    from python.integracao import criar_modulo_lisp, criar_modulo_prolog

    prolog = criar_modulo_prolog()
    lisp = criar_modulo_lisp()
    # a primeira chamada fica de fora: na primeira execucao o SBCL compila o yason e distorceria a media
    aquecimento = Proposta.de_registro(escolher_casos(1)[0])
    prolog.executar(aquecimento.para_prolog())
    lisp.executar(aquecimento.para_lisp())

    medicoes: dict[str, list[float]] = {"Python": [], "Prolog": [], "Lisp": []}
    print(f"\nTempo de execucao em {quantidade} casos:")
    for caso in escolher_casos(quantidade):
        tempos, desfecho = medir_proposta(caso, prolog, lisp)
        for etapa, duracao in tempos.items():
            medicoes[etapa].append(duracao)
        print(f"  {caso['id']:<10} {desfecho:<18} {sum(tempos.values()) * 1000:8.1f} ms")

    medias = {etapa: sum(valores) / len(valores) for etapa, valores in medicoes.items() if valores}
    soma = sum(medias.values())
    print("\nTempo medio por etapa:")
    for etapa, media in medias.items():
        print(f"  {etapa:<8} {media * 1000:8.1f} ms  ({media / soma:>4.0%} do total, {len(medicoes[etapa])} casos)")
    mais_lenta = max(medias, key=medias.get)
    print(f"Etapa mais lenta: {mais_lenta}")
    print("Obs.: Prolog e Lisp rodam como processos novos a cada proposta, entao o tempo inclui a inicializacao deles.")


def quantidade_de_casos(texto: str) -> int:
    # o enunciado exige o tempo medio em pelo menos 5 casos
    quantidade = int(texto)
    if quantidade < MINIMO_DE_CASOS:
        raise argparse.ArgumentTypeError(f"informe pelo menos {MINIMO_DE_CASOS} casos")
    return quantidade


def main() -> None:
    parser = argparse.ArgumentParser(description="Metricas do projeto para o relatorio")
    parser.add_argument("--casos", type=quantidade_de_casos, default=MINIMO_DE_CASOS)
    argumentos = parser.parse_args()
    mostrar_metricas_de_codigo()
    medir_tempos(argumentos.casos)


if __name__ == "__main__":
    main()
