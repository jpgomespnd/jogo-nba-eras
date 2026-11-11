"""Testes de coerência da camada de eras (não existe gabarito para jogos entre épocas).

1. Um time contra ele mesmo, em quadra neutra, dá ~50%.
2. Trocar a ordem dos times em quadra neutra não muda o resultado.
3. Traduzir um time para a própria temporada não muda nada.
4. A força de cada time contra um time médio muda pouco de era para era (ranking estável).
5. O garrafão (aproveitamento de 2) vale mais nos anos 90 do que em 2020.

Volume de 3 rende mais indo para o passado: nos anos 90 a bola de 3 valia 1,03 ponto por arremesso
contra 0,96 da de 2; em 2020 as duas valem ~1,08. Quem chutava muito de 3 explorava uma vantagem
que a liga ignorava.
"""

import numpy as np
import pandas as pd

from banco import conectar
from confronto import simular_confronto
from eras import ERAS, METRICAS, ambiente, carregar, traduzir
from simulador import CALIBRACAO_MANDO, ataque, pontos_esperados

TOLERANCIA = 0.02


def saldo_contra_medio(time, liga):
    """Saldo esperado a cada 100 posses contra um time médio da era, em quadra neutra."""
    medio = pd.Series(0.0, index=time.index)
    vantagem = time.bonus / (2 * CALIBRACAO_MANDO * liga["ortg"])
    return 100 * (pontos_esperados(ataque(time, medio, liga), 1 + vantagem)
                  - pontos_esperados(ataque(medio, time, liga), 1 - vantagem))


def checar(nome, ok, detalhe):
    print(f"[{'ok' if ok else 'FALHOU'}] {nome}: {detalhe}")


def main():
    conexao = conectar()
    try:
        dados = carregar(conexao)
    finally:
        conexao.close()
    times = dados["times"]
    exemplos = [("1995-96", 1610612741), ("2016-17", 1610612744), ("2009-10", 1610612747), ("2003-04", 1610612765)]

    piores = []
    for chave in exemplos:
        for era in ERAS:
            r = simular_confronto(dados, times.loc[chave], times.loc[chave], era, mando="neutro", n=4000, seed=1)
            piores.append(abs(r["chance_a"] - 0.5))
    checar("1. time contra ele mesmo", max(piores) < TOLERANCIA, f"maior desvio de 50%: {100 * max(piores):.1f} p.p.")

    somas = []
    for i, x in enumerate(exemplos):
        for y in exemplos[i + 1:]:
            for era in ERAS:
                ida = simular_confronto(dados, times.loc[x], times.loc[y], era, mando="neutro", n=4000, seed=1)
                volta = simular_confronto(dados, times.loc[y], times.loc[x], era, mando="neutro", n=4000, seed=2)
                somas.append(abs(ida["chance_a"] + volta["chance_a"] - 1))
    checar("2. ordem dos times", max(somas) < 2 * TOLERANCIA, f"maior diferença: {100 * max(somas):.1f} p.p.")

    _, propria = ambiente(dados, "2016-17")
    gsw = times.loc[("2016-17", 1610612744)]
    diferenca = max(abs(traduzir(gsw, dados, propria)[c] - gsw[c]) for c in propria.index)
    checar("3. tradução para a própria temporada", diferenca < 1e-12, f"maior mudança: {diferenca:.1e}")

    saldos = {}
    for era in ERAS:
        liga, espalhamento = ambiente(dados, era)
        saldos[era] = [saldo_contra_medio(traduzir(times.loc[k], dados, espalhamento), liga) for k in times.index]
    saldos = pd.DataFrame(saldos, index=times.index)
    menor_correlacao = saldos.corr(method="spearman").min().min()
    checar("4. ranking estável entre eras", menor_correlacao > 0.95, f"menor correlação de ranking: {menor_correlacao:.3f}")

    z = (times[[f"rel_{m}" for m in METRICAS]] / dados["espalhamento"].reindex(times.index.get_level_values(0)).values)
    ganho = saldos["anos 2020"] - saldos["anos 90"]
    correlacoes = z.corrwith(ganho).sort_values()
    garrafao = correlacoes["rel_fg2_pct"]
    checar("5. aproveitamento de 2 vale mais nos anos 90 que em 2020", garrafao < 0, f"correlação com o ganho ao ir para 2020: {garrafao:.2f}")

    print("\nO que faz um time ganhar ao ir dos anos 90 para os anos 2020 (correlação com o ganho de saldo):")
    print(correlacoes.round(2).to_string())

    rotulo = times.team_abbreviation + " " + times.index.get_level_values(0)
    print("\nOs 10 mais fortes em cada era (saldo esperado contra um time médio da era, a cada 100 posses):")
    tabela = {era: [f"{rotulo[k]} {saldos.loc[k, era]:+.1f}" for k in saldos[era].nlargest(10).index] for era in ERAS}
    print(pd.DataFrame(tabela, index=range(1, 11)).to_string())


if __name__ == "__main__":
    main()
