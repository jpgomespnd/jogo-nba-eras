"""Rotação de cada time-temporada: quem joga, quantos minutos e a participação em cada estatística.

É a versão "saudável" do time: os jogadores que terminaram a temporada nele (quem foi trocado sai),
com os minutos médios dos jogos em que estiveram em quadra, ajustados para 240 minutos por jogo.
"""

import numpy as np
import pandas as pd

TAMANHO_ROTACAO = 10
MINIMO_JOGOS = 10
# Minutos nos playoffs e nos jogos decisivos (um time pode ser eliminado) em relação à temporada regular,
# por posição na rotação. Medidos em todos os jogos de playoff desde 1990-91.
FATOR_MINUTOS = {
    "regular": [1.0] * 10,
    "playoffs": [1.07, 1.06, 1.06, 1.02, 0.99, 0.93, 0.87, 0.84, 0.79, 0.72],
    "decisivo": [1.10, 1.09, 1.08, 1.05, 1.00, 0.93, 0.90, 0.82, 0.81, 0.72],
}
# Encolhimento do aproveitamento individual para a média do time (em tentativas).
ENCOLHER_2, ENCOLHER_3, ENCOLHER_LL = 100, 60, 40
TAXAS = ["fg2a", "fg3a", "fta", "tov", "oreb", "dreb", "ast", "stl", "blk", "pf"]

CONSULTA_JOGADORES = """
SELECT p.player_id, p.player_name, p.team_id, g.game_date, p.minutes, p.pts,
       p.fgm, p.fga, p.fg3m, p.fg3a, p.ftm, p.fta, p.oreb, p.dreb, p.ast, p.stl, p.blk, p.tov, p.pf
FROM player_games p JOIN games g USING (game_id)
WHERE g.season = ? AND g.season_type = 'regular'
"""

CONSULTA_TIME = """
SELECT SUM(t.ast) AS ast, SUM(t.stl) AS stl, SUM(t.blk) AS blk, SUM(t.pf) AS pf, COUNT(*) AS jogos
FROM team_games t JOIN games g USING (game_id)
WHERE g.season = ? AND g.season_type = 'regular' AND t.team_id = ?
"""


def rotacao(jogos_temporada, team_id):
    do_time = jogos_temporada[jogos_temporada.team_id == team_id]
    ultimo_no_time = do_time.groupby("player_id").game_date.max()
    # Trocado: jogou por outro time depois do último jogo por este.
    depois = jogos_temporada[jogos_temporada.player_id.isin(ultimo_no_time.index) & (jogos_temporada.team_id != team_id)]
    trocados = {j for j, data in zip(depois.player_id, depois.game_date) if data > ultimo_no_time[j]}

    somas = do_time.groupby(["player_id", "player_name"]).agg(
        jogos=("minutes", "size"), **{c: (c, "sum") for c in ["minutes", "pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
                                                              "oreb", "dreb", "ast", "stl", "blk", "tov", "pf"]}
    ).reset_index()
    somas = somas[(somas.jogos >= MINIMO_JOGOS) & ~somas.player_id.isin(trocados) & (somas.minutes > 0)]
    somas["mpg"] = somas.minutes / somas.jogos
    return somas.nlargest(TAMANHO_ROTACAO, "mpg").reset_index(drop=True)


def distribuir_minutos(mpg, contexto="playoffs", total=240.0):
    """Aplica o fator do contexto a cada posição; os principais mantêm seus minutos e a rotação encurta até fechar 240."""
    ordem = np.argsort(-mpg)
    alvo = np.zeros_like(mpg, dtype=float)
    alvo[ordem] = mpg[ordem] * np.array(FATOR_MINUTOS[contexto][:len(mpg)])
    alvo = np.minimum(alvo, 48.0)
    if alvo.sum() <= total:
        return alvo * total / alvo.sum()
    minutos = np.zeros_like(alvo)
    restante = total
    for i in ordem:
        minutos[i] = min(alvo[i], restante)
        restante -= minutos[i]
    return minutos


def montar_elenco(conexao, temporada, team_id, jogos_temporada=None, contexto="playoffs"):
    if jogos_temporada is None:
        jogos_temporada = pd.read_sql(CONSULTA_JOGADORES, conexao, params=(temporada,))
    r = rotacao(jogos_temporada, team_id)
    r["fg2a"] = r.fga - r.fg3a
    r["fg2m"] = r.fgm - r.fg3m
    r["minutos"] = distribuir_minutos(r.mpg.to_numpy(), contexto)
    r = r[r.minutos >= 1].reset_index(drop=True)
    pesos = {taxa: (r[taxa] / r.minutes * r.minutos).to_numpy() for taxa in TAXAS}

    # Aproveitamento relativo à média do time, encolhido para 1 quando há poucas tentativas.
    # Normalizado pelo volume de cada um, para o aproveitamento do time continuar o mesmo.
    def relativo(acertos, tentativas, k, peso):
        media = acertos.sum() / max(tentativas.sum(), 1)
        rel = ((acertos + k * media) / (tentativas + k) / media).to_numpy()
        return rel / (np.sum(rel * peso) / np.sum(peso)) if np.sum(peso) > 0 else np.ones(len(rel))

    return {
        "jogadores": r[["player_id", "player_name", "jogos", "mpg", "minutos"]],
        "pesos": pesos,
        "rel_2": relativo(r.fg2m, r.fg2a, ENCOLHER_2, pesos["fg2a"]),
        "rel_3": relativo(r.fg3m, r.fg3a, ENCOLHER_3, pesos["fg3a"]),
        "rel_ll": relativo(r.ftm, r.fta, ENCOLHER_LL, pesos["fta"]),
    }


def taxas_do_time(conexao, temporada, team_id, fatores):
    """Taxas de eventos que não estão nos quatro fatores: assistências, roubos, tocos e faltas."""
    time = pd.read_sql(CONSULTA_TIME, conexao, params=(temporada, int(team_id))).iloc[0]
    f = fatores.loc[(temporada, team_id)]
    return {
        "assistencia_por_cesta": float(time.ast / f.fgm),
        "roubo_por_desperdicio": float(time.stl / f.opp_tov),
        "toco_por_erro": float(time.blk / (f.opp_fga - f.opp_fgm)),
        "faltas_extras_por_posse": float(max(0.0, (time.pf - f.opp_fta / 2) / time.jogos) / f.pace),
    }


def escolher(pesos, rng, excluir=None):
    p = np.asarray(pesos, dtype=float).copy()
    if excluir is not None:
        p[excluir] = 0.0
    total = p.sum()
    if total <= 0:
        return None
    return int(rng.choice(p.size, p=p / total))
