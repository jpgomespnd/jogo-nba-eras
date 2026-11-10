"""Calcula os quatro fatores de cada time por temporada regular e grava em fatores_time.

Também imprime uma conferência de completude por temporada.
"""

import pandas as pd

from banco import conectar

SOMAS = [
    "minutes", "pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "tov",
    "opp_pts", "opp_fgm", "opp_fga", "opp_fg3m", "opp_fg3a", "opp_ftm", "opp_fta", "opp_oreb", "opp_dreb", "opp_tov",
]
METRICAS = [
    "pace", "ortg", "drtg", "net",
    "efg", "tov_pct", "orb_pct", "ft_rate", "fg3a_rate",
    "opp_efg", "opp_tov_pct", "drb_pct", "opp_ft_rate", "opp_fg3a_rate",
]


def calcular(totais):
    t = totais
    posses = ((t.fga - t.oreb + t.tov + 0.44 * t.fta) + (t.opp_fga - t.opp_oreb + t.opp_tov + 0.44 * t.opp_fta)) / 2
    return t.assign(
        posses=posses,
        pace=posses / (t.minutes / 240),
        ortg=100 * t.pts / posses,
        drtg=100 * t.opp_pts / posses,
        net=100 * (t.pts - t.opp_pts) / posses,
        efg=(t.fgm + 0.5 * t.fg3m) / t.fga,
        tov_pct=t.tov / posses,
        orb_pct=t.oreb / (t.oreb + t.opp_dreb),
        ft_rate=t.ftm / t.fga,
        fg3a_rate=t.fg3a / t.fga,
        opp_efg=(t.opp_fgm + 0.5 * t.opp_fg3m) / t.opp_fga,
        opp_tov_pct=t.opp_tov / posses,
        drb_pct=t.dreb / (t.dreb + t.opp_oreb),
        opp_ft_rate=t.opp_ftm / t.opp_fga,
        opp_fg3a_rate=t.opp_fg3a / t.opp_fga,
    )


def montar_fatores(conexao):
    jogos = pd.read_sql("SELECT * FROM vw_confrontos WHERE season_type = 'regular'", conexao)
    times = (
        jogos.groupby(["season", "team_id"])
        .agg(team_abbreviation=("team_abbreviation", "last"), team_name=("team_name", "last"),
             jogos=("game_id", "size"), vitorias=("won", "sum"), **{c: (c, "sum") for c in SOMAS})
        .reset_index()
    )
    times = calcular(times)

    # Média da liga: calculada sobre os totais da liga, não como média simples dos times.
    liga = calcular(times.groupby("season")[SOMAS].sum().reset_index())[["season", *METRICAS]]
    times = times.merge(liga.add_prefix("liga_").rename(columns={"liga_season": "season"}), on="season")
    for metrica in METRICAS:
        times[f"rel_{metrica}"] = times[metrica] - times[f"liga_{metrica}"]
    return times, liga


def conferir(conexao, times, liga):
    linhas_por_jogo = pd.read_sql(
        "SELECT g.season, g.season_type, COUNT(t.team_id) AS linhas FROM games g "
        "LEFT JOIN team_games t USING (game_id) GROUP BY g.game_id", conexao
    )
    incompletos = linhas_por_jogo[linhas_por_jogo.linhas != 2]
    print(f"Jogos sem exatamente 2 times: {len(incompletos)}")

    zerados = pd.read_sql(
        "SELECT COUNT(*) AS n FROM team_games WHERE fga = 0 OR minutes < 240 OR (oreb = 0 AND dreb = 0)", conexao
    ).n[0]
    print(f"Linhas de time com box score suspeito (sem arremessos, rebotes ou com menos de 240 min): {zerados}\n")

    playoffs = pd.read_sql(
        "SELECT season, COUNT(*) AS jogos_playoffs FROM games WHERE season_type = 'playoffs' GROUP BY season", conexao
    )
    resumo = (
        times.groupby("season")
        .agg(times=("team_id", "size"), jogos_min=("jogos", "min"), jogos_max=("jogos", "max"))
        .reset_index()
        .merge(playoffs, on="season", how="left")
        .merge(liga[["season", "pace", "ortg", "efg", "fg3a_rate", "orb_pct", "ft_rate", "tov_pct"]], on="season")
    )
    print(resumo.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    aproveitamento = times.vitorias / times.jogos
    print(f"\nCorrelação saldo por 100 posses x aproveitamento: {times.net.corr(aproveitamento):.3f}")


def main():
    conexao = conectar()
    try:
        times, liga = montar_fatores(conexao)
        times.to_sql("fatores_time", conexao, if_exists="replace", index=False)
        conferir(conexao, times, liga)
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
