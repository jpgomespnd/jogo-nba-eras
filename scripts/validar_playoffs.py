"""Prevê cada série de playoff real (1990-91 em diante) usando só a temporada regular e mede o acerto.

Grava o resultado série a série em data/validacao_playoffs.csv.
"""

import numpy as np
import pandas as pd

from banco import RAIZ_DO_PROJETO, conectar
from simulador import simular_series

SIMULACOES = 2000
ULTIMA_FINAL_2_3_2 = "2012-13"
CAMINHO_SAIDA = RAIZ_DO_PROJETO / "data" / "validacao_playoffs.csv"


def montar_series(conexao):
    jogos = pd.read_sql(
        "SELECT g.season, g.game_id, g.game_date, g.is_neutral, t.team_id, t.is_home, t.won "
        "FROM games g JOIN team_games t USING (game_id) WHERE g.season_type = 'playoffs'",
        conexao,
    )
    pares = jogos.groupby("game_id").team_id.agg(lambda ids: tuple(sorted(ids))).rename("par")
    jogos = jogos.join(pares, on="game_id").sort_values(["game_date", "game_id"])

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
    series["formato"] = np.select(
        [series.melhor_de == 5, final & (series.season <= ULTIMA_FINAL_2_3_2)], ["2-2-1", "2-3-2"], "2-2-1-1-1"
    )
    return series


def prever(series, times, liga):
    previsoes = []
    for i, s in enumerate(series.itertuples()):
        a, b = times.loc[(s.season, s.mando)], times.loc[(s.season, s.outro)]
        r = simular_series(a, b, liga.loc[s.season], n=SIMULACOES, formato=s.formato, neutro=s.neutro, seed=i)
        previsoes.append({
            "time_mando": a.team_abbreviation,
            "time_outro": b.team_abbreviation,
            "prob_mando": r["chance_a"],
            "jogos_previstos": r["jogos_medios"],
            "net_mando": a.net,
            "net_outro": b.net,
        })
    return pd.concat([series.reset_index(drop=True), pd.DataFrame(previsoes)], axis=1)


def relatorio(r):
    venceu_mando = (r.vencedor == r.mando).astype(int)
    acerto_modelo = ((r.prob_mando >= 0.5).astype(int) == venceu_mando)
    acerto_net = ((r.net_mando >= r.net_outro).astype(int) == venceu_mando)
    p = r.prob_mando.clip(0.01, 0.99)

    print(f"Séries: {len(r)} ({r.season.min()} a {r.season.max()})\n")
    print(f"Acerto do simulador:           {100 * acerto_modelo.mean():.1f}%")
    print(f"Time com mando sempre vence:   {100 * venceu_mando.mean():.1f}%")
    print(f"Melhor saldo sempre vence:     {100 * acerto_net.mean():.1f}%")
    print(f"Brier do simulador:            {np.mean((p - venceu_mando) ** 2):.3f} (chutar 50% dá 0.250)")
    print(f"Log loss do simulador:         {-np.mean(venceu_mando * np.log(p) + (1 - venceu_mando) * np.log(1 - p)):.3f}")
    print(f"Jogos por série, real x prev.: {r.jogos.mean():.2f} x {r.jogos_previstos.mean():.2f}\n")

    faixas = pd.cut(r.prob_mando, [0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], include_lowest=True)
    calibracao = pd.DataFrame({"faixa": faixas, "previsto": r.prob_mando, "real": venceu_mando})
    print("Calibração (chance prevista do time com mando x quanto ele venceu de fato):")
    print(calibracao.groupby("faixa", observed=True).agg(series=("real", "size"), previsto=("previsto", "mean"),
                                                         real=("real", "mean")).round(3).to_string())

    decada = r.season.str[:3] + "0s"
    print("\nAcerto por década:")
    print(pd.DataFrame({"decada": decada, "acerto": acerto_modelo, "mando": venceu_mando})
          .groupby("decada").agg(series=("acerto", "size"), simulador=("acerto", "mean"), mando=("mando", "mean"))
          .round(3).to_string())

    surpresas = r.assign(prob_vencedor=np.where(venceu_mando == 1, r.prob_mando, 1 - r.prob_mando))
    surpresas["vencedor_sigla"] = np.where(venceu_mando == 1, r.time_mando, r.time_outro)
    surpresas["perdedor_sigla"] = np.where(venceu_mando == 1, r.time_outro, r.time_mando)
    print("\nMaiores zebras (vencedor com menor chance prevista):")
    print(surpresas.nsmallest(8, "prob_vencedor")[["season", "vencedor_sigla", "perdedor_sigla", "jogos", "prob_vencedor"]]
          .round(3).to_string(index=False))


def main():
    conexao = conectar()
    try:
        series = montar_series(conexao)
        times = pd.read_sql("SELECT * FROM fatores_time", conexao).set_index(["season", "team_id"])
        liga = pd.read_sql("SELECT * FROM liga", conexao).set_index("season")
    finally:
        conexao.close()

    resultado = prever(series, times, liga)
    resultado.to_csv(CAMINHO_SAIDA, index=False)
    relatorio(resultado)


if __name__ == "__main__":
    main()
