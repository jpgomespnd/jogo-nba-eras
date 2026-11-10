"""Baixa os box scores de time (temporada regular e playoffs) para o banco.

Temporadas que já estão no banco são puladas; use --refazer para baixar de novo.
"""

import sys
import time

import requests
from nba_api.stats.endpoints import leaguegamelog

from banco import conectar, criar_tabelas
from temporadas import TEMPORADAS

PAUSA_SEGUNDOS = 3
TEMPO_LIMITE_SEGUNDOS = 30
MAXIMO_TENTATIVAS = 3
TIPOS = {"regular": "Regular Season", "playoffs": "Playoffs"}
INICIO_DA_BOLHA = "2020-07-30"

SQL_JOGO = """
    INSERT OR REPLACE INTO games (game_id, season, season_type, game_date, is_neutral)
    VALUES (:game_id, :season, :season_type, :game_date, :is_neutral)
"""

SQL_TIME_NO_JOGO = """
    INSERT OR REPLACE INTO team_games (
        game_id, team_id, team_abbreviation, team_name, is_home, won, minutes, pts,
        fgm, fga, fg3m, fg3a, ftm, fta, oreb, dreb, reb, ast, stl, blk, tov, pf
    ) VALUES (
        :game_id, :team_id, :team_abbreviation, :team_name, :is_home, :won, :minutes, :pts,
        :fgm, :fga, :fg3m, :fg3a, :ftm, :fta, :oreb, :dreb, :reb, :ast, :stl, :blk, :tov, :pf
    )
"""


def com_tentativas(chamada):
    for tentativa in range(1, MAXIMO_TENTATIVAS + 1):
        try:
            return chamada()
        except (requests.exceptions.RequestException, ValueError) as erro:
            if tentativa == MAXIMO_TENTATIVAS:
                raise
            espera = PAUSA_SEGUNDOS * 2**tentativa
            print(f"  Tentativa {tentativa} falhou ({erro}). Nova tentativa em {espera} s.")
            time.sleep(espera)


def buscar(temporada, tipo):
    return com_tentativas(
        lambda: leaguegamelog.LeagueGameLog(
            season=temporada,
            season_type_all_star=TIPOS[tipo],
            timeout=TEMPO_LIMITE_SEGUNDOS,
        ).get_data_frames()[0]
    )


def preparar(jogos, temporada, tipo):
    # Jogos cancelados (ex.: BOS x IND em 16/04/2013) vêm com tudo zerado.
    jogos = jogos[jogos["MIN"] > 0]

    # "LAL vs. GSW" = mandante, "GSW @ LAL" = visitante; em quadra neutra os dois vêm com "@".
    is_home = jogos["MATCHUP"].str.contains("vs.", regex=False).astype(int)
    mandantes_na_partida = is_home.groupby(jogos["GAME_ID"]).transform("sum")
    na_bolha = (temporada == "2019-20") & (jogos["GAME_DATE"] >= INICIO_DA_BOLHA)

    partidas = (
        jogos.assign(is_neutral=((mandantes_na_partida == 0) | na_bolha).astype(int))[["GAME_ID", "GAME_DATE", "is_neutral"]]
        .drop_duplicates()
        .rename(columns={"GAME_ID": "game_id", "GAME_DATE": "game_date"})
        .assign(season=temporada, season_type=tipo)
    )

    times_no_jogo = jogos.rename(columns={"MIN": "minutes"}).rename(columns=str.lower)
    times_no_jogo["is_home"] = is_home
    times_no_jogo["won"] = (jogos["WL"] == "W").astype(int)

    return partidas.to_dict("records"), times_no_jogo.to_dict("records")


def ja_baixada(conexao, temporada, tipo):
    consulta = "SELECT 1 FROM games WHERE season = ? AND season_type = ? LIMIT 1"
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
                print(f"Baixando {temporada} ({tipo})...")
                partidas, times_no_jogo = preparar(buscar(temporada, tipo), temporada, tipo)
                with conexao:
                    conexao.executemany(SQL_JOGO, partidas)
                    conexao.executemany(SQL_TIME_NO_JOGO, times_no_jogo)
                print(f"  {len(partidas)} partidas salvas.")
                time.sleep(PAUSA_SEGUNDOS)
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
