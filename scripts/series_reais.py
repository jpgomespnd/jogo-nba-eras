import numpy as np
import pandas as pd

ULTIMA_FINAL_2_3_2 = "2012-13"


def temporada_anterior(temporada):
    ano = int(temporada[:4]) - 1
    return f"{ano}-{str(ano + 1)[-2:]}"


def montar_series(conexao):
    """Uma linha por série de playoff: quem tinha o mando, quem venceu, formato e duração."""
    jogos = pd.read_sql(
        "SELECT season, game_id, game_date, is_neutral, team_id, opp_team_id, is_home, won "
        "FROM vw_confrontos WHERE season_type = 'playoffs'",
        conexao,
    )
    jogos["par"] = list(zip(jogos[["team_id", "opp_team_id"]].min(axis=1), jogos[["team_id", "opp_team_id"]].max(axis=1)))
    jogos = jogos.sort_values(["game_date", "game_id"])

    series = []
    for (temporada, par), grupo in jogos.groupby(["season", "par"], sort=False):
        vitorias = grupo[grupo.won == 1].team_id.value_counts()
        primeiro_jogo = grupo[grupo.game_id == grupo.game_id.iloc[0]]
        com_mando = primeiro_jogo[primeiro_jogo.is_home == 1].team_id
        mando = int(com_mando.iloc[0]) if len(com_mando) else par[0]
        series.append({
            "season": temporada,
            "inicio": grupo.game_date.min(),
            "mando": mando,
            "outro": par[1] if mando == par[0] else par[0],
            "vencedor": int(vitorias.index[0]),
            "jogos": grupo.game_id.nunique(),
            "melhor_de": 5 if vitorias.max() == 3 else 7,
            "neutro": bool(grupo.is_neutral.all()),
        })
    series = pd.DataFrame(series)
    final = series.groupby("season").inicio.transform("max") == series.inicio

    # Desgaste: jogos de playoff que cada time já tinha disputado antes da série.
    datas = jogos.groupby(["season", "team_id"]).game_date.agg(list)
    for papel in ("mando", "outro"):
        series[f"jogos_po_{papel}"] = [
            sum(d < inicio for d in datas[(s, t)]) for s, t, inicio in zip(series.season, series[papel], series.inicio)
        ]
    series["formato"] = np.select(
        [series.melhor_de == 5, final & (series.season <= ULTIMA_FINAL_2_3_2)], ["2-2-1", "2-3-2"], "2-2-1-1-1"
    )
    return series
