"""Simula jogos e séries posse a posse.

Cada probabilidade do confronto = média da era + desvio do ataque + desvio da defesa adversária.
Os desvios de cada time são relativos à própria temporada; a média vem da era em que o jogo acontece.
"""

from dataclasses import dataclass

import numpy as np

DESVIO_RITMO = 4.0
# Calibrados para a margem do mandante e o espalhamento dos placares baterem com os jogos reais.
CALIBRACAO_MANDO = 0.65
AMORTECIMENTO = 0.3
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


def ataque(atacante, defensor, liga):
    fta_rate = liga["fta_rate"] + atacante["rel_fta_rate"] + defensor["rel_opp_fta_rate"]
    # Cada ida à linha vale dois lances livres; fta_rate é lances livres por arremesso de quadra.
    idas_por_arremesso = fta_rate / 2
    return Ataque(
        tov=liga["tov_pct"] + atacante["rel_tov_pct"] + defensor["rel_opp_tov_pct"],
        lance_livre=idas_por_arremesso / (1 + idas_por_arremesso),
        tentativa_3=liga["fg3a_rate"] + atacante["rel_fg3a_rate"] + defensor["rel_opp_fg3a_rate"],
        acerto_2=liga["fg2_pct"] + atacante["rel_fg2_pct"] + defensor["rel_opp_fg2_pct"],
        acerto_3=liga["fg3_pct"] + atacante["rel_fg3_pct"] + defensor["rel_opp_fg3_pct"],
        acerto_ll=liga["ft_pct"] + atacante["rel_ft_pct"],
        rebote_of=liga["orb_pct"] + atacante["rel_orb_pct"] - defensor["rel_drb_pct"],
    )


def pontos_por_posse(a, fator_acerto, rng):
    """Uma posse para cada jogo; fator_acerto multiplica o aproveitamento dos arremessos."""
    quantidade = fator_acerto.size
    pontos = np.zeros(quantidade, dtype=np.int64)
    ativa = rng.random(quantidade) >= a.tov
    while ativa.any():
        idx = np.flatnonzero(ativa)
        n = idx.size
        foi_a_linha = rng.random(n) < a.lance_livre
        lances = (rng.random(n) < a.acerto_ll).astype(np.int64) + (rng.random(n) < a.acerto_ll)
        de_3 = rng.random(n) < a.tentativa_3
        acertou = rng.random(n) < np.where(de_3, a.acerto_3, a.acerto_2) * fator_acerto[idx]
        pontos[idx] += np.where(foi_a_linha, lances, np.where(acertou, np.where(de_3, 3, 2), 0))
        pegou_rebote = ~foi_a_linha & ~acertou & (rng.random(n) < a.rebote_of)
        ativa[:] = False
        ativa[idx[pegou_rebote]] = True
    return pontos


def pontos_esperados(a, fator_acerto):
    acerto = a.tentativa_3 * a.acerto_3 * fator_acerto + (1 - a.tentativa_3) * a.acerto_2 * fator_acerto
    por_tentativa = a.lance_livre * 2 * a.acerto_ll + (1 - a.lance_livre) * (
        a.tentativa_3 * 3 * a.acerto_3 + (1 - a.tentativa_3) * 2 * a.acerto_2) * fator_acerto
    erro = (1 - a.lance_livre) * (1 - acerto)
    return (1 - a.tov) * por_tentativa / (1 - erro * a.rebote_of)


def vantagem_da_casa(casa, fora, liga, neutro=False, peso_mando=1.0):
    """Mando + diferença de bônus, convertidos num multiplicador do aproveitamento dos arremessos."""
    mando = 0.0 if neutro else peso_mando * liga["mando"]
    bonus = casa.get("bonus", 0.0) - fora.get("bonus", 0.0)
    return (mando + bonus) / (2 * CALIBRACAO_MANDO * liga["ortg"])


def jogar(a_casa, a_fora, vantagem, posses, pts_casa, pts_fora, rng):
    # Quem abre vantagem além do esperado relaxa (ou põe os reservas) e o placar volta para perto do esperado.
    saldo_por_posse = pontos_esperados(a_casa, 1 + vantagem) - pontos_esperados(a_fora, 1 - vantagem)
    inicio = pts_casa - pts_fora
    for posse in range(int(posses.max())):
        em_jogo = np.flatnonzero(posse < posses)
        sorte = (pts_casa[em_jogo] - pts_fora[em_jogo] - inicio[em_jogo] - posse * saldo_por_posse) / 100
        ajuste = vantagem - AMORTECIMENTO * sorte
        pts_casa[em_jogo] += pontos_por_posse(a_casa, 1 + ajuste, rng)
        pts_fora[em_jogo] += pontos_por_posse(a_fora, 1 - ajuste, rng)


def simular_jogos(casa, fora, liga, n, rng, neutro=False, peso_mando=1.0):
    """Devolve (pontos da casa, pontos de fora) de n jogos.

    "bonus" de cada time (pontos a cada 100 posses) soma força que os quatro fatores não captam.
    """
    vantagem = vantagem_da_casa(casa, fora, liga, neutro, peso_mando)
    a_casa, a_fora = ataque(casa, fora, liga), ataque(fora, casa, liga)
    ritmo = liga["pace"] + casa["rel_pace"] + fora["rel_pace"]

    pts_casa, pts_fora = np.zeros(n, dtype=np.int64), np.zeros(n, dtype=np.int64)
    posses = np.maximum(rng.normal(ritmo, DESVIO_RITMO, n).round().astype(int), 60)
    jogar(a_casa, a_fora, vantagem, posses, pts_casa, pts_fora, rng)

    empate = np.flatnonzero(pts_casa == pts_fora)
    while empate.size:
        pc, pf = pts_casa[empate], pts_fora[empate]
        jogar(a_casa, a_fora, vantagem, np.full(empate.size, round(ritmo * 5 / 48)), pc, pf, rng)
        pts_casa[empate], pts_fora[empate] = pc, pf
        empate = np.flatnonzero(pts_casa == pts_fora)
    return pts_casa, pts_fora


def simular_series(a, b, liga, n=2000, formato="2-2-1-1-1", neutro=False, peso_mando=1.0, seed=None):
    """Time a tem o mando da série. Devolve a chance de a vencer e o resumo das séries."""
    rng = np.random.default_rng(seed)
    mandos = FORMATOS[formato]
    pts_a = np.empty((n, len(mandos)), dtype=int)
    pts_b = np.empty_like(pts_a)
    for jogo, a_em_casa in enumerate(mandos):
        if a_em_casa:
            pts_a[:, jogo], pts_b[:, jogo] = simular_jogos(a, b, liga, n, rng, neutro, peso_mando)
        else:
            pts_b[:, jogo], pts_a[:, jogo] = simular_jogos(b, a, liga, n, rng, neutro, peso_mando)

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
