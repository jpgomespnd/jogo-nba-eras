"""Eras: ambiente médio de cada década e tradução dos times para ele.

Um time leva para a outra era a sua posição relativa (escore z): quem era o 2º que mais chutava de 3
continua sendo o 2º. Isso previu melhor que manter a diferença absoluta nas mudanças reais de ambiente.
"""

import pandas as pd

ERAS = {
    "anos 90": ("1990-91", "1999-00"),
    "anos 2000": ("2000-01", "2009-10"),
    "anos 2010": ("2010-11", "2019-20"),
    "anos 2020": ("2020-21", "2025-26"),
}
METRICAS = [
    "pace", "tov_pct", "opp_tov_pct", "fta_rate", "opp_fta_rate", "fg3a_rate", "opp_fg3a_rate",
    "fg2_pct", "opp_fg2_pct", "fg3_pct", "opp_fg3_pct", "ft_pct", "orb_pct", "drb_pct",
]


def carregar(conexao):
    times = pd.read_sql("SELECT * FROM fatores_time", conexao).set_index(["season", "team_id"])
    forca = pd.read_sql("SELECT season, team_id, forca, bonus FROM forca_time", conexao).set_index(["season", "team_id"])
    liga = pd.read_sql("SELECT * FROM liga", conexao).set_index("season")
    pesos = pd.read_sql("SELECT * FROM pesos_forca", conexao).iloc[0]
    espalhamento = times.groupby("season")[[f"rel_{m}" for m in METRICAS]].std()
    return {"times": times.join(forca), "liga": liga, "pesos": pesos, "espalhamento": espalhamento}


def temporadas_da_era(dados, era):
    if era in ERAS:
        inicio, fim = ERAS[era]
        return [s for s in dados["liga"].index if inicio <= s <= fim]
    return [era]


def ambiente(dados, era):
    """Médias da liga e espalhamento entre times de uma era (nome da década ou uma temporada)."""
    temporadas = temporadas_da_era(dados, era)
    return dados["liga"].loc[temporadas].mean(), dados["espalhamento"].loc[temporadas].mean()


def traduzir(time, dados, espalhamento_destino):
    traduzido = time.copy()
    origem = dados["espalhamento"].loc[time.name[0]]
    for coluna in origem.index:
        traduzido[coluna] = time[coluna] * espalhamento_destino[coluna] / origem[coluna]
    return traduzido
