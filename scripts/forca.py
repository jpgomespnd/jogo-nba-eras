"""Força efetiva de cada time, além do que os quatro fatores mostram.

Combina saldo ajustado pelos adversários, saldo contra times bons, aproveitamento e séries vencidas
nas duas temporadas anteriores. O desgaste (jogos de playoff antes da série) entra como contexto da série.
Os pesos vêm de uma regressão da margem dos jogos de playoff reais. Grava a tabela forca_time.
"""

import numpy as np
import pandas as pd

from banco import conectar
from series_reais import montar_series, temporada_anterior

# 10 pontos percentuais de aproveitamento ≈ 3,3 pontos de saldo a cada 100 posses.
ESCALA_APROVEITAMENTO = 33
# Adversário "bom": saldo acima de +2 a cada 100 posses (nível de playoff).
SALDO_TIME_BOM = 2.0
VARIAVEIS_TIME = ["net_adj", "net_vs_bons", "aprov", "series_2anos"]
DESGASTE = "jogos_po"


def saldo_contra_bons(conexao, times):
    jogos = pd.read_sql(
        "SELECT season, team_id, opp_team_id, pts, opp_pts, fga, oreb, tov, fta, opp_fga, opp_oreb, opp_tov, opp_fta "
        "FROM vw_confrontos WHERE season_type = 'regular'",
        conexao,
    )
    saldo_adversario = times.net.reindex(pd.MultiIndex.from_arrays([jogos.season, jogos.opp_team_id])).values
    jogos = jogos[saldo_adversario > SALDO_TIME_BOM]
    posses = ((jogos.fga - jogos.oreb + jogos.tov + 0.44 * jogos.fta)
              + (jogos.opp_fga - jogos.opp_oreb + jogos.opp_tov + 0.44 * jogos.opp_fta)) / 2
    somas = jogos.assign(margem=jogos.pts - jogos.opp_pts, posses=posses).groupby(["season", "team_id"])[["margem", "posses"]].sum()
    return 100 * somas.margem / somas.posses


def carregar(conexao):
    times = pd.read_sql("SELECT * FROM fatores_time", conexao).set_index(["season", "team_id"])
    liga = pd.read_sql("SELECT * FROM liga", conexao).set_index("season")
    series = montar_series(conexao)

    variaveis = times[["team_abbreviation", "net", "net_adj", "rel_pace"]].copy()
    variaveis["net_vs_bons"] = saldo_contra_bons(conexao, times).reindex(variaveis.index).fillna(variaveis.net)
    variaveis["aprov"] = (times.vitorias / times.jogos - 0.5) * ESCALA_APROVEITAMENTO
    vencidas = series.groupby(["season", "vencedor"]).size()
    variaveis["series_2anos"] = [
        vencidas.get((temporada_anterior(s), t), 0) + vencidas.get((temporada_anterior(temporada_anterior(s)), t), 0)
        for s, t in variaveis.index
    ]

    jogos = pd.read_sql(
        "SELECT season, team_id, opp_team_id, is_neutral, pts - opp_pts AS margem "
        "FROM vw_confrontos WHERE season_type = 'playoffs' AND is_home = 1",
        conexao,
    )
    casa = variaveis.reindex(pd.MultiIndex.from_arrays([jogos.season, jogos.team_id]))
    fora = variaveis.reindex(pd.MultiIndex.from_arrays([jogos.season, jogos.opp_team_id]))
    ritmo = jogos.season.map(liga.pace).values + casa.rel_pace.values + fora.rel_pace.values
    jogos["mando"] = np.where(jogos.is_neutral == 1, 0, jogos.season.map(liga.mando) * ritmo / 100)
    for v in VARIAVEIS_TIME:
        jogos[v] = (casa[v].values - fora[v].values) * ritmo / 100

    desgaste = pd.concat([
        series[["season", "mando", "outro", "jogos_po_mando", "jogos_po_outro"]].set_axis(["season", "a", "b", "ja", "jb"], axis=1),
        series[["season", "outro", "mando", "jogos_po_outro", "jogos_po_mando"]].set_axis(["season", "a", "b", "ja", "jb"], axis=1),
    ]).set_index(["season", "a", "b"])
    par = desgaste.reindex(pd.MultiIndex.from_arrays([jogos.season, jogos.team_id, jogos.opp_team_id]))
    jogos[DESGASTE] = (par.ja.values - par.jb.values) * ritmo / 100
    return variaveis, jogos, series


def ajustar(jogos, excluir=None):
    treino = jogos if excluir is None else jogos[jogos.season != excluir]
    colunas = ["mando", *VARIAVEIS_TIME, DESGASTE]
    x = treino[colunas].values
    coeficientes, *_ = np.linalg.lstsq(x, treino.margem.values, rcond=None)
    return {
        "peso_mando": coeficientes[0],
        "pesos": dict(zip(VARIAVEIS_TIME, coeficientes[1:-1].tolist())),
        "peso_desgaste": float(coeficientes[-1]),
        "desvio": float(np.std(treino.margem.values - x @ coeficientes)),
    }


def forca(variaveis, pesos):
    return sum(peso * variaveis[v] for v, peso in pesos["pesos"].items())


def main():
    conexao = conectar()
    try:
        variaveis, jogos, _ = carregar(conexao)
        pesos = ajustar(jogos)
        tabela = variaveis.assign(forca=forca(variaveis, pesos))
        tabela["bonus"] = tabela.forca - tabela.net
        tabela.reset_index().to_sql("forca_time", conexao, if_exists="replace", index=False)
        pd.DataFrame([{"peso_mando": pesos["peso_mando"], "peso_desgaste": pesos["peso_desgaste"],
                       "desvio": pesos["desvio"], **pesos["pesos"]}]).to_sql("pesos_forca", conexao, if_exists="replace", index=False)
    finally:
        conexao.close()

    print(f"Jogos de playoff usados: {len(jogos)}")
    print(f"Peso do mando nos playoffs: {pesos['peso_mando']:.2f}x o da temporada regular")
    print("Pesos:", {k: round(v, 2) for k, v in pesos["pesos"].items()})
    print(f"Desgaste: {pesos['peso_desgaste']:.2f} ponto a cada 100 posses por jogo de playoff a mais que o rival")
    print(f"Desvio da margem em torno do esperado: {pesos['desvio']:.1f} pontos\n")
    print("Mais fortes:")
    print(tabela.nlargest(8, "forca")[["team_abbreviation", "net", "forca", "bonus"]].round(1).to_string())


if __name__ == "__main__":
    main()
