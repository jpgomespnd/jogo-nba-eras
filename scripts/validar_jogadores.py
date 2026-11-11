"""Confere o jogo detalhado: os jogadores simulados produzem como os reais?

Em algumas temporadas, cada time joga contra adversários sorteados da mesma temporada. Compara:
- pontos do time no jogo detalhado x no simulador validado;
- pontos, rebotes e assistências por 36 minutos de cada jogador, simulados x reais.
"""

import numpy as np
import pandas as pd

from banco import conectar
from elenco import CONSULTA_JOGADORES, montar_elenco, rotacao, taxas_do_time
from eras import carregar
from jogo_detalhado import jogar_detalhado
from simulador import simular_jogos

TEMPORADAS = ["1995-96", "2003-04", "2009-10", "2016-17", "2024-25"]
JOGOS_POR_TIME = 20


def main():
    conexao = conectar()
    rng = np.random.default_rng(7)
    dados = carregar(conexao)
    times = dados["times"]
    linhas, placares = [], []
    try:
        for temporada in TEMPORADAS:
            jogos_temporada = pd.read_sql(CONSULTA_JOGADORES, conexao, params=(temporada,))
            ids = list(times.loc[temporada].index)
            elencos = {t: montar_elenco(conexao, temporada, t, jogos_temporada, contexto="regular") for t in ids}
            taxas = {t: taxas_do_time(conexao, temporada, t, times) for t in ids}
            liga = dados["liga"].loc[temporada]
            acumulado = {t: [] for t in ids}
            for t in ids:
                for k in range(JOGOS_POR_TIME):
                    rival = ids[rng.integers(len(ids))]
                    if rival == t:
                        continue
                    casa, fora = (t, rival) if k % 2 == 0 else (rival, t)
                    j = jogar_detalhado(times.loc[(temporada, casa)], times.loc[(temporada, fora)], liga,
                                        elencos[casa], elencos[fora], taxas[casa], taxas[fora], rng)
                    acumulado[t].append(j["box_casa"] if casa == t else j["box_fora"])
                    pc, pf = simular_jogos(times.loc[(temporada, casa)], times.loc[(temporada, fora)], liga, 200, rng)
                    placares.append({"detalhado": j["pts_casa"] + j["pts_fora"], "validado": (pc + pf).mean(),
                                     "dif_detalhado": j["pts_casa"] - j["pts_fora"], "dif_validado": (pc - pf).mean()})

            for t in ids:
                box = pd.concat(acumulado[t]).groupby("Jogador")[["MIN", "PTS", "REB", "AST"]].sum()
                real = rotacao(jogos_temporada, t).set_index("player_name")
                for nome, linha in box.iterrows():
                    r = real.loc[nome]
                    linhas.append({
                        "season": temporada, "jogador": nome, "min_real": r.mpg, "min_sim": linha.MIN / JOGOS_POR_TIME,
                        "pts36_real": 36 * r.pts / r.minutes, "pts36_sim": 36 * linha.PTS / linha.MIN,
                        "reb36_real": 36 * (r.oreb + r.dreb) / r.minutes, "reb36_sim": 36 * linha.REB / linha.MIN,
                        "ast36_real": 36 * r.ast / r.minutes, "ast36_sim": 36 * linha.AST / linha.MIN,
                        "ppg_real": r.pts / r.jogos, "ppg_sim": linha.PTS / len(acumulado[t]),
                    })
    finally:
        conexao.close()

    p = pd.DataFrame(placares)
    print(f"Jogos detalhados: {len(p)}")
    print(f"Pontos somados por jogo: detalhado {p.detalhado.mean():.1f} x validado {p.validado.mean():.1f}")
    print(f"Correlação da margem esperada (validado) com a margem do jogo detalhado: {p.dif_detalhado.corr(p.dif_validado):.2f}\n")

    j = pd.DataFrame(linhas)
    j = j[(j.min_real >= 15) & (j.min_sim >= 10)]
    for estat in ["pts36", "reb36", "ast36"]:
        corr = j[f"{estat}_real"].corr(j[f"{estat}_sim"])
        razao = j[f"{estat}_sim"].sum() / j[f"{estat}_real"].sum()
        print(f"{estat}: correlação real x simulado {corr:.3f} | simulado/real {razao:.2f}")
    print(f"\nMinutos: correlação {j.min_real.corr(j.min_sim):.3f}")
    print("\nMaiores pontuadores simulados (pontos por jogo, real x simulado):")
    print(j.nlargest(12, "ppg_sim")[["season", "jogador", "ppg_real", "ppg_sim", "min_real", "min_sim"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
