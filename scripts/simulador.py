"""Simula jogos e séries posse a posse.

Cada probabilidade do confronto = média da era + desvio do ataque + desvio da defesa adversária.
Os desvios de cada time são relativos à própria temporada; a média vem da era em que o jogo acontece.
"""

from dataclasses import dataclass

import numpy as np

DESVIO_RITMO = 4.0
# Calibrado para a margem simulada do mandante bater com a real de cada temporada.
CALIBRACAO_MANDO = 0.65
FORMATOS = {
    "2-2-1-1-1": [1, 1, 0, 0, 1, 0, 1],
    "2-3-2": [1, 1, 0, 0, 0, 1, 1],
    "2-2-1": [1, 1, 0, 0, 1],
}


@dataclass
class Ataque:
    tov: float
    lance_livre: float
    tentativa_3: float
    acerto_2: float
    acerto_3: float
    acerto_ll: float
    rebote_of: float


def ataque(atacante, defensor, liga, ajuste_mando=0.0):
    fta_rate = liga["fta_rate"] + atacante["rel_fta_rate"] + defensor["rel_opp_fta_rate"]
    # Cada ida à linha vale dois lances livres; fta_rate é lances livres por arremesso de quadra.
    idas_por_arremesso = fta_rate / 2
    return Ataque(
        tov=liga["tov_pct"] + atacante["rel_tov_pct"] + defensor["rel_opp_tov_pct"],
        lance_livre=idas_por_arremesso / (1 + idas_por_arremesso),
        tentativa_3=liga["fg3a_rate"] + atacante["rel_fg3a_rate"] + defensor["rel_opp_fg3a_rate"],
        acerto_2=(liga["fg2_pct"] + atacante["rel_fg2_pct"] + defensor["rel_opp_fg2_pct"]) * (1 + ajuste_mando),
        acerto_3=(liga["fg3_pct"] + atacante["rel_fg3_pct"] + defensor["rel_opp_fg3_pct"]) * (1 + ajuste_mando),
        acerto_ll=liga["ft_pct"] + atacante["rel_ft_pct"],
        rebote_of=liga["orb_pct"] + atacante["rel_orb_pct"] - defensor["rel_drb_pct"],
    )


def pontos_por_posse(a, quantidade, rng):
    pontos = np.zeros(quantidade, dtype=np.int16)
    ativa = rng.random(quantidade) >= a.tov
    while ativa.any():
        idx = np.flatnonzero(ativa)
        n = idx.size
        foi_a_linha = rng.random(n) < a.lance_livre
        lances = (rng.random(n) < a.acerto_ll).astype(np.int16) + (rng.random(n) < a.acerto_ll)
        de_3 = rng.random(n) < a.tentativa_3
        acertou = rng.random(n) < np.where(de_3, a.acerto_3, a.acerto_2)
        pontos[idx] += np.where(foi_a_linha, lances, np.where(acertou, np.where(de_3, 3, 2), 0)).astype(np.int16)
        pegou_rebote = ~foi_a_linha & ~acertou & (rng.random(n) < a.rebote_of)
        ativa[:] = False
        ativa[idx[pegou_rebote]] = True
    return pontos


def somar_posses(a, posses, rng):
    maximo = int(posses.max())
    pontos = pontos_por_posse(a, posses.size * maximo, rng).reshape(posses.size, maximo)
    return (pontos * (np.arange(maximo) < posses[:, None])).sum(axis=1)


def simular_jogos(casa, fora, liga, n, rng, neutro=False):
    """Devolve (pontos da casa, pontos de fora) de n jogos."""
    mando = 0.0 if neutro else liga["mando"] / (2 * CALIBRACAO_MANDO * liga["ortg"])
    a_casa = ataque(casa, fora, liga, +mando)
    a_fora = ataque(fora, casa, liga, -mando)
    ritmo = liga["pace"] + casa["rel_pace"] + fora["rel_pace"]

    posses = np.maximum(rng.normal(ritmo, DESVIO_RITMO, n).round().astype(int), 60)
    pts_casa = somar_posses(a_casa, posses, rng)
    pts_fora = somar_posses(a_fora, posses, rng)

    empate = pts_casa == pts_fora
    posses_prorrogacao = np.full(n, round(ritmo * 5 / 48))
    while empate.any():
        k = int(empate.sum())
        pts_casa[empate] += somar_posses(a_casa, posses_prorrogacao[:k], rng)
        pts_fora[empate] += somar_posses(a_fora, posses_prorrogacao[:k], rng)
        empate = pts_casa == pts_fora
    return pts_casa, pts_fora


def simular_series(a, b, liga, n=2000, formato="2-2-1-1-1", neutro=False, seed=None):
    """Time a tem o mando da série. Devolve a chance de a vencer e o resumo das séries."""
    rng = np.random.default_rng(seed)
    mandos = FORMATOS[formato]
    pts_a = np.empty((n, len(mandos)), dtype=int)
    pts_b = np.empty_like(pts_a)
    for jogo, a_em_casa in enumerate(mandos):
        if a_em_casa:
            pts_a[:, jogo], pts_b[:, jogo] = simular_jogos(a, b, liga, n, rng, neutro)
        else:
            pts_b[:, jogo], pts_a[:, jogo] = simular_jogos(b, a, liga, n, rng, neutro)

    precisa = len(mandos) // 2 + 1
    vitorias_a = np.cumsum(pts_a > pts_b, axis=1)
    vitorias_b = np.cumsum(pts_b > pts_a, axis=1)
    fim = np.argmax((vitorias_a == precisa) | (vitorias_b == precisa), axis=1)
    a_venceu = vitorias_a[np.arange(n), fim] == precisa
    jogados = np.arange(len(mandos)) <= fim[:, None]

    placares = {}
    for jogos in range(precisa, len(mandos) + 1):
        placares[f"a em {jogos}"] = float(np.mean(a_venceu & (fim + 1 == jogos)))
        placares[f"b em {jogos}"] = float(np.mean(~a_venceu & (fim + 1 == jogos)))
    return {
        "chance_a": float(a_venceu.mean()),
        "placares": placares,
        "media_pts_a": float(pts_a[jogados].mean()),
        "media_pts_b": float(pts_b[jogados].mean()),
        "jogos_medios": float((fim + 1).mean()),
    }
