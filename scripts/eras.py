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
DESCRICOES = {
    "anos 90": "Jogo lento e físico, com hand-checking e poucas bolas de 3. O arremesso de 2 vale 0,96 ponto e o de 3 vale 1,03: quem chutava de longe explorava uma vantagem que a liga ignorava.",
    "anos 2000": "Ritmo mais baixo da história e defesas fortes. O hand-checking acaba em 2004 e o volume de 3 começa a subir.",
    "anos 2010": "Spacing e a revolução da bola de 3, com quase 30% dos arremessos de longe no fim da década.",
    "anos 2020": "Ritmo alto e 40% dos arremessos de 3. Arremesso de 2 e de 3 valem o mesmo: cerca de 1,08 ponto.",
}
# Textos do site, em inglês (o protótipo em Streamlit usa DESCRICOES).
ROTULOS_EN = {"anos 90": "1990s", "anos 2000": "2000s", "anos 2010": "2010s", "anos 2020": "2020s"}
DESCRICOES_EN = {
    "anos 90": "Slow, physical and hand-checking. Few threes: a 2-point shot was worth 0.96 points and a 3 was worth 1.03, so teams that let it fly exploited an edge the league ignored.",
    "anos 2000": "The slowest pace in history and suffocating defenses. Hand-checking ends in 2004 and three-point volume starts to climb.",
    "anos 2010": "Spacing and the three-point revolution, with almost 30% of shots from deep by the end of the decade.",
    "anos 2020": "High pace and 40% of shots from three. A two and a three are worth the same: about 1.08 points per shot.",
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
