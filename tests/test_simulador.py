"""Propriedades do simulador com dados fabricados (conftest.py): rodam sem o banco, inclusive no CI."""

import numpy as np
import pytest

import pandas as pd

from confronto import mvp_da_serie, narrar_serie, preparar, simular_confronto
from elenco import distribuir_minutos, escolher
from eras import ambiente, traduzir
from jogo_detalhado import LIMITE_FALTAS, jogar_detalhado, relogio
from simulador import FORMATOS, ataque, pontos_esperados, pontos_por_posse, simular_jogos, simular_series

GSW, MEDIO, CHI, FRACO = ("2016-17", 1), ("2016-17", 2), ("1995-96", 3), ("1998-99", 4)


@pytest.fixture(scope="module")
def anos_2010(dados):
    gsw, medio, liga = preparar(dados, dados["times"].loc[GSW], dados["times"].loc[MEDIO], "2016-17")
    return gsw, medio, liga


def test_time_contra_ele_mesmo_da_50(dados):
    time = dados["times"].loc[CHI]
    for era in ["anos 90", "anos 2010"]:
        r = simular_confronto(dados, time, time, era, mando="neutro", n=4000, seed=1)
        assert abs(r["chance_a"] - 0.5) < 0.03


def test_ordem_dos_times_nao_importa(dados):
    a, b = dados["times"].loc[GSW], dados["times"].loc[CHI]
    ida = simular_confronto(dados, a, b, "anos 90", mando="neutro", n=4000, seed=1)["chance_a"]
    volta = simular_confronto(dados, b, a, "anos 90", mando="neutro", n=4000, seed=2)["chance_a"]
    assert abs(ida + volta - 1) < 0.04


def test_mando_b_e_o_espelho_do_mando_a(dados):
    a, b = dados["times"].loc[GSW], dados["times"].loc[CHI]
    com_b = simular_confronto(dados, a, b, "anos 90", mando="b", n=1000, seed=3)
    invertido = simular_confronto(dados, b, a, "anos 90", mando="a", n=1000, seed=3)
    assert com_b["chance_a"] == pytest.approx(1 - invertido["chance_a"])
    assert com_b["placares"]["a em 4"] == invertido["placares"]["b em 4"]


def test_mando_de_quadra_ajuda(anos_2010):
    _, medio, liga = anos_2010
    assert simular_series(medio, medio, liga, n=4000, seed=1)["chance_a"] > 0.52


def test_time_melhor_vence_mais(anos_2010):
    gsw, medio, liga = anos_2010
    assert simular_series(gsw, medio, liga, n=2000, neutro=True, seed=1)["chance_a"] > 0.9


def test_resumo_da_serie_e_coerente(anos_2010):
    gsw, medio, liga = anos_2010
    r = simular_series(gsw, medio, liga, n=2000, seed=1)
    assert sum(r["placares"].values()) == pytest.approx(1)
    assert sum(v for k, v in r["placares"].items() if k.startswith("a")) == pytest.approx(r["chance_a"])
    assert 4 <= r["jogos_medios"] <= 7
    assert 90 < r["media_pts_a"] < 140


def test_mesma_semente_mesmo_resultado(anos_2010):
    gsw, medio, liga = anos_2010
    assert simular_series(gsw, medio, liga, n=500, seed=9) == simular_series(gsw, medio, liga, n=500, seed=9)


def test_jogo_nunca_termina_empatado(anos_2010):
    gsw, medio, liga = anos_2010
    casa, fora = simular_jogos(medio, medio, liga, 5000, np.random.default_rng(1))
    assert not np.any(casa == fora)


def test_pontos_esperados_batem_com_as_posses_sorteadas(anos_2010):
    gsw, medio, liga = anos_2010
    a = ataque(gsw, medio, liga)
    sorteados = pontos_por_posse(a, np.ones(200_000), np.random.default_rng(1)).mean()
    assert sorteados == pytest.approx(pontos_esperados(a, 1.0), abs=0.01)


def test_traduzir_para_a_propria_temporada_nao_muda_nada(dados):
    gsw = dados["times"].loc[GSW]
    _, propria = ambiente(dados, "2016-17")
    assert np.allclose(traduzir(gsw, dados, propria)[propria.index].to_numpy(float), gsw[propria.index].to_numpy(float))


def test_traduzir_mantem_o_escore_z(dados):
    chi = dados["times"].loc[CHI].drop("team_abbreviation").astype(float)
    _, destino = ambiente(dados, "anos 2010")
    origem = dados["espalhamento"].loc["1995-96"]
    traduzido = traduzir(chi, dados, destino)
    assert np.allclose(traduzido[destino.index] / destino, chi[destino.index] / origem)


def test_ambiente_da_era_e_a_media_das_temporadas(dados):
    liga, _ = ambiente(dados, "anos 90")
    assert liga["pace"] == pytest.approx(dados["liga"].loc[["1995-96", "1998-99"], "pace"].mean())


@pytest.fixture(scope="module")
def jogo(anos_2010, elenco):
    gsw, medio, liga = anos_2010
    escalacao, taxas = elenco
    return jogar_detalhado(gsw, medio, liga, escalacao, escalacao, taxas, taxas, np.random.default_rng(5))


def test_box_score_soma_o_placar(jogo):
    assert jogo["box_casa"].PTS.sum() == jogo["pts_casa"]
    assert jogo["box_fora"].PTS.sum() == jogo["pts_fora"]
    assert sum(lance["pontos"] for lance in jogo["lances"]) == jogo["pts_casa"] + jogo["pts_fora"]
    assert jogo["pts_casa"] != jogo["pts_fora"]


def test_box_score_tem_minutos_e_faltas_validos(jogo):
    duracao = 48 + 5 * jogo["prorrogacoes"]
    for box in (jogo["box_casa"], jogo["box_fora"]):
        assert abs(box.MIN.sum() - 5 * duracao) <= len(box)
        assert box.FAL.max() <= LIMITE_FALTAS
        assert list(box.eliminado) == list(box.FAL == LIMITE_FALTAS)


def test_placar_dos_lances_so_cresce(jogo):
    casa = [lance["placar_casa"] for lance in jogo["lances"]]
    assert casa == sorted(casa) and casa[-1] == jogo["pts_casa"]


@pytest.mark.parametrize("mando", ["a", "b", "neutro"])
def test_serie_narrada_termina_com_4_vitorias(dados, elenco, mando):
    escalacao, taxas = elenco
    elencos = (({"playoffs": escalacao, "decisivo": escalacao}, taxas),) * 2
    jogos = narrar_serie(dados, dados["times"].loc[GSW], dados["times"].loc[CHI], "anos 2010", elencos, mando, ("GSW", "CHI"), seed=2)
    assert 4 <= len(jogos) <= 7
    ultimo = jogos[-1]
    assert max(ultimo["vitorias_a"], ultimo["vitorias_b"]) == 4
    assert min(ultimo["vitorias_a"], ultimo["vitorias_b"]) == len(jogos) - 4
    esperado = [None] * len(jogos) if mando == "neutro" else \
        [bool(c) != (mando == "b") for c in FORMATOS["2-2-1-1-1"][:len(jogos)]]
    assert [j["a_em_casa"] for j in jogos] == esperado
    a_venceu = ultimo["vitorias_a"] == 4
    assert mvp_da_serie(jogos, a_venceu)["jogador"] in set(ultimo["box_a" if a_venceu else "box_b"].Jogador)


def test_mvp_e_do_campeao_e_pesa_eficiencia():
    def linha(jogador, pts, arr, reb=5, ast=3):
        return {"Jogador": jogador, "PTS": pts, "REB": reb, "AST": ast, "ROB": 1, "TOC": 0, "ERR": 2, "FAL": 2,
                "ARR": arr, "LL": "4-4"}

    # O cestinha ineficiente (30 pontos em 30 arremessos) perde para quem fez 28 em 17.
    campeao = pd.DataFrame([linha("Eficiente", 28, "12-17"), linha("Chutador", 30, "13-30")])
    vice = pd.DataFrame([linha("Vice", 50, "23-30", reb=15, ast=10)])
    jogos = [{"box_a": campeao, "box_b": vice}] * 4
    mvp = mvp_da_serie(jogos, a_venceu=True)
    assert mvp == {"jogador": "Eficiente", "pontos": 28.0, "rebotes": 5.0, "assistencias": 3.0}


def test_relogio():
    assert relogio(0) == ("Q1", "12:00")
    assert relogio(4 * 720 - 30) == ("Q4", "0:30")
    assert relogio(4 * 720) == ("OT", "5:00")
    assert relogio(4 * 720 + 300) == ("2OT", "5:00")


def test_distribuir_minutos_fecha_240():
    mpg = np.array([40, 38, 35, 33, 30, 25, 20, 15, 12, 10], dtype=float)
    for contexto in ["regular", "playoffs", "decisivo"]:
        minutos = distribuir_minutos(mpg, contexto)
        assert minutos.sum() == pytest.approx(240)
        assert minutos.max() <= 48


def test_escolher_respeita_exclusao_e_pesos_zerados():
    rng = np.random.default_rng(1)
    assert escolher([0, 0, 0], rng) is None
    assert escolher([1, 0, 0], rng, excluir=0) is None
    assert {escolher([1, 1, 0], rng, excluir=0) for _ in range(50)} == {1}
