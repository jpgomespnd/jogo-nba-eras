"""Baixa o box score de cada jogador em cada jogo (temporada regular e playoffs) para o banco.

Rode coletar_jogos.py antes: só entram jogos que já estão na tabela games.
Temporadas que já estão no banco são puladas; use --refazer para baixar de novo.
"""

import sys
import time

from nba_api.stats.endpoints import leaguegamelog

from banco import conectar, criar_tabelas
from coletar_jogos import PAUSA_SEGUNDOS, TIPOS, com_tentativas
from temporadas import TEMPORADAS

TEMPO_LIMITE_SEGUNDOS = 60
ESTATISTICAS = ["fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "reb", "ast", "stl", "blk", "tov", "pf"]
COLUNAS = ["game_id", "player_id", "player_name", "team_id", "minutes", "pts", *ESTATISTICAS, "plus_minus"]

SQL_JOGADOR_NO_JOGO = f"""
    INSERT OR REPLACE INTO player_games ({", ".join(COLUNAS)})
    VALUES ({", ".join(":" + c for c in COLUNAS)})
"""


def buscar(temporada, tipo):
    return com_tentativas(
        lambda: leaguegamelog.LeagueGameLog(
            season=temporada,
            season_type_all_star=TIPOS[tipo],
            player_or_team_abbreviation="P",
            timeout=TEMPO_LIMITE_SEGUNDOS,
        ).get_data_frames()[0]
    )


def preparar(jogadores, jogos_conhecidos):
    jogadores = jogadores.rename(columns={"MIN": "minutes"}).rename(columns=str.lower)
    jogadores = jogadores[jogadores.game_id.isin(jogos_conhecidos)].copy()
    jogadores[ESTATISTICAS] = jogadores[ESTATISTICAS].fillna(0).astype(int)
    jogadores["plus_minus"] = jogadores.plus_minus.astype(object).where(jogadores.plus_minus.notna(), None)
    return jogadores[COLUNAS].to_dict("records")


def ja_baixada(conexao, temporada, tipo):
    consulta = ("SELECT 1 FROM player_games p JOIN games g USING (game_id) "
                "WHERE g.season = ? AND g.season_type = ? LIMIT 1")
    return conexao.execute(consulta, (temporada, tipo)).fetchone() is not None


def main():
    refazer = "--refazer" in sys.argv
    conexao = conectar()
    try:
        criar_tabelas(conexao)
        for temporada in TEMPORADAS:
            for tipo in TIPOS:
                if not refazer and ja_baixada(conexao, temporada, tipo):
                    continue
                jogos_conhecidos = {linha[0] for linha in conexao.execute(
                    "SELECT game_id FROM games WHERE season = ? AND season_type = ?", (temporada, tipo))}
                print(f"Baixando jogadores {temporada} ({tipo})...")
                linhas = preparar(buscar(temporada, tipo), jogos_conhecidos)
                with conexao:
                    conexao.executemany(SQL_JOGADOR_NO_JOGO, linhas)
                print(f"  {len(linhas)} linhas salvas.")
                time.sleep(PAUSA_SEGUNDOS)
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
