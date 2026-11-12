"""Checagens de coerência das eras com os times reais (as de scripts/testes_eras.py).

Precisam do banco: sem ele (como no CI), são puladas.
"""

import pandas as pd

from confronto import simular_confronto
from eras import ERAS, METRICAS, ambiente, traduzir
from testes_eras import saldo_contra_medio

BULLS_96, WARRIORS_17 = ("1995-96", 1610612741), ("2016-17", 1610612744)


def saldos_por_era(dados):
    times = dados["times"]
    colunas = {}
    for era in ERAS:
        liga, espalhamento = ambiente(dados, era)
        colunas[era] = [saldo_contra_medio(traduzir(times.loc[k], dados, espalhamento), liga) for k in times.index]
    return pd.DataFrame(colunas, index=times.index)


def test_time_real_contra_ele_mesmo_da_50(dados_reais):
    for chave in (BULLS_96, WARRIORS_17):
        time = dados_reais["times"].loc[chave]
        for era in ERAS:
            r = simular_confronto(dados_reais, time, time, era, mando="neutro", n=4000, seed=1)
            assert abs(r["chance_a"] - 0.5) < 0.02


def test_ranking_estavel_entre_eras_e_garrafao_vale_mais_nos_anos_90(dados_reais):
    saldos = saldos_por_era(dados_reais)
    assert saldos.corr(method="spearman").min().min() > 0.95

    times = dados_reais["times"]
    z = times[[f"rel_{m}" for m in METRICAS]] / dados_reais["espalhamento"].reindex(times.index.get_level_values(0)).values
    ganho_indo_para_2020 = saldos["anos 2020"] - saldos["anos 90"]
    assert z["rel_fg2_pct"].corr(ganho_indo_para_2020) < 0
