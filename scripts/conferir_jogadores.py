"""Confere os box scores de jogadores contra os placares de time, temporada a temporada."""

import pandas as pd

from banco import conectar

CONSULTA = """
SELECT g.season, g.season_type, t.game_id, t.team_id, t.pts, t.minutes,
       COUNT(p.player_id) AS jogadores, SUM(p.pts) AS pts_jogadores, SUM(p.minutes) AS minutos_jogadores,
       SUM(p.plus_minus IS NOT NULL) AS com_mais_menos
FROM team_games t
JOIN games g USING (game_id)
LEFT JOIN player_games p ON p.game_id = t.game_id AND p.team_id = t.team_id
GROUP BY t.game_id, t.team_id
"""


def main():
    conexao = conectar()
    try:
        jogos = pd.read_sql(CONSULTA, conexao)
        distintos = pd.read_sql(
            "SELECT g.season, COUNT(DISTINCT p.player_id) AS jogadores_distintos "
            "FROM player_games p JOIN games g USING (game_id) GROUP BY g.season", conexao
        )
    finally:
        conexao.close()

    jogos["sem_jogadores"] = jogos.jogadores == 0
    jogos["pts_diferentes"] = jogos.pts != jogos.pts_jogadores.fillna(0)
    resumo = (
        jogos.groupby(["season", "season_type"])
        .agg(times_jogo=("game_id", "size"), sem_jogadores=("sem_jogadores", "sum"),
             pts_diferentes=("pts_diferentes", "sum"), pts_time=("pts", "sum"), pts_jogadores=("pts_jogadores", "sum"),
             com_mais_menos=("com_mais_menos", "sum"), jogadores=("jogadores", "sum"))
        .reset_index()
    )
    resumo["pts_cobertos"] = resumo.pts_jogadores / resumo.pts_time
    resumo["mais_menos"] = resumo.com_mais_menos / resumo.jogadores
    resumo = resumo.merge(distintos, on="season")
    colunas = ["season", "season_type", "times_jogo", "sem_jogadores", "pts_diferentes", "pts_cobertos", "mais_menos",
               "jogadores_distintos"]
    print(resumo[colunas].to_string(index=False, formatters={"pts_cobertos": "{:.2%}".format, "mais_menos": "{:.0%}".format}))
    print(f"\nTotal: {jogos.jogadores.sum():,} linhas de jogador | times-jogo com pontos diferentes: "
          f"{jogos.pts_diferentes.sum()} de {len(jogos):,}".replace(",", "."))


if __name__ == "__main__":
    main()
