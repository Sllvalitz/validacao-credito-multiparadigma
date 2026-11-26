# Responsavel: Anderson da Silva Pinto
import unittest

from python import apresentacao as ap

APROVADA = {"id": "PROP-001", "status": "APROVADO", "impedimentos": [], "erro": None,
            "precificacao": {"status": "APROVADO", "classificacao_risco": "baixo",
                             "taxa_juros_mensal": 0.015, "limite_calculado": 12600.0,
                             "valor_aprovado": 4200.0, "valor_parcela_final": 385.06}}
REPROVADA = {"id": "PROP-002", "status": "REPROVADO", "impedimentos": ["idade_abaixo_do_minimo"],
             "erro": None, "precificacao": None}
COM_ERRO = {"id": "PROP-003", "status": "ERRO_VALIDACAO", "impedimentos": [],
            "erro": "chave ausente: prazo", "precificacao": None}
RESULTADOS = [APROVADA, REPROVADA, COM_ERRO]


class TestFormatacao(unittest.TestCase):
    def test_moeda_no_formato_brasileiro(self):
        self.assertEqual(ap.moeda(4200), "R$ 4.200,00")
        self.assertEqual(ap.moeda(385.06), "R$ 385,06")
        self.assertEqual(ap.moeda(1234567.5), "R$ 1.234.567,50")

    def test_percentual_com_virgula(self):
        self.assertEqual(ap.percentual(1.5), "1,5%")
        self.assertEqual(ap.percentual(10, 2), "10,00%")

    def test_barra_proporcional(self):
        self.assertEqual(ap.barra(0, 10, 10), "░" * 10)
        self.assertEqual(ap.barra(5, 10, 10), "█" * 5 + "░" * 5)
        self.assertEqual(ap.barra(10, 10, 10), "█" * 10)

    # total zero nao pode causar divisao por zero (lote vazio)
    def test_barra_com_total_zero(self):
        self.assertEqual(ap.barra(0, 0, 4), "░" * 4)

    def test_cor_so_quando_ativa(self):
        self.assertEqual(ap.colorir("x", "verde", False), "x")
        self.assertIn("\033[", ap.colorir("x", "verde", True))

    def test_status_desconhecido_nao_quebra(self):
        self.assertEqual(ap.estilo("NAO_PROCESSADO")[4], "Desconhecido")


class TestTerminal(unittest.TestCase):
    def test_tabela_tem_cabecalho_separador_e_uma_linha_por_proposta(self):
        linhas = ap.tabela(RESULTADOS, False).splitlines()
        self.assertEqual(len(linhas), 2 + len(RESULTADOS))
        self.assertIn("PROP-001", linhas[2])
        self.assertIn("R$ 385,06", linhas[2])
        self.assertIn("idade_abaixo_do_minimo", linhas[3])
        self.assertIn("chave ausente: prazo", linhas[4])

    def test_resumo_conta_e_calcula_porcentagem(self):
        texto = ap.resumo(RESULTADOS, False)
        self.assertIn("3 propostas", texto)
        self.assertIn("33%", texto)

    def test_resumo_de_lote_vazio(self):
        self.assertIn("nenhuma proposta", ap.resumo([], False))

    def test_ranking_numera_as_posicoes(self):
        texto = ap.ranking([APROVADA], False)
        self.assertIn("1. PROP-001", texto)
        self.assertIn("R$ 4.200,00", texto)

    def test_ranking_sem_aprovadas(self):
        self.assertIn("nenhuma proposta aprovada", ap.ranking([], False))

    def test_cabecalho_cita_os_tres_paradigmas(self):
        texto = ap.cabecalho(False)
        self.assertIn("Python orquestra", texto)
        self.assertIn("Prolog decide", texto)
        self.assertIn("Lisp precifica", texto)


class TestFluxo(unittest.TestCase):
    def test_proposta_aprovada_passa_pelos_tres_modulos(self):
        rastro = {"indicadores": {"parcela_base": 350.0, "comprometimento_percentual": 10.0},
                  "parecer": {"elegivel": True, "regras_satisfeitas": ["renda_minima"], "impedimentos": []},
                  "preco": APROVADA["precificacao"]}
        texto = ap.fluxo(APROVADA, rastro, False)
        self.assertIn("ELEGÍVEL", texto)
        self.assertIn("risco baixo", texto)
        self.assertIn("R$ 385,06", texto)

    def test_reprovada_nao_executa_o_lisp(self):
        rastro = {"indicadores": {"parcela_base": 500.0, "comprometimento_percentual": 20.0},
                  "parecer": {"elegivel": False, "regras_satisfeitas": [],
                              "impedimentos": ["idade_abaixo_do_minimo"]}}
        texto = ap.fluxo(REPROVADA, rastro, False)
        self.assertIn("NÃO ELEGÍVEL", texto)
        self.assertIn("reprovado pelo Prolog", texto)

    def test_erro_de_validacao_mostra_o_motivo_e_nao_executa_o_resto(self):
        texto = ap.fluxo(COM_ERRO, {}, False)
        self.assertIn("chave ausente: prazo", texto)
        self.assertEqual(texto.count("não executado"), 2)


class TestHtml(unittest.TestCase):
    def test_pagina_tem_as_propostas_e_o_resumo(self):
        pagina = ap.pagina_html(RESULTADOS, [APROVADA])
        self.assertTrue(pagina.startswith("<!DOCTYPE html>"))
        for texto in ("PROP-001", "PROP-002", "PROP-003", "R$ 385,06", "Propostas (3)"):
            self.assertIn(texto, pagina)

    # o detalhe vem de dados externos: precisa ser escapado para nao injetar HTML
    def test_html_e_escapado(self):
        perigosa = dict(COM_ERRO, erro="<script>alert(1)</script>")
        pagina = ap.pagina_html([perigosa], [])
        self.assertNotIn("<script>alert(1)", pagina)
        self.assertIn("&lt;script&gt;", pagina)

    def test_pagina_de_lote_vazio(self):
        pagina = ap.pagina_html([], [])
        self.assertIn("Nenhuma proposta aprovada", pagina)


if __name__ == "__main__":
    unittest.main()
