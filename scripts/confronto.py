"""Série entre dois times de quaisquer temporadas, jogada no ambiente de uma era escolhida.

Uso: confronto.py TEMPORADA_A TIME_A TEMPORADA_B TIME_B [ERA]
Exemplo: confronto.py 2009-10 LAL 2016-17 GSW "anos 90"
"""

import sys

from banco import conectar
from eras import ERAS, ambiente, carregar, traduzir
from simulador import simular_series


def buscar_time(dados, temporada, texto):
    da_temporada = dados["times"].loc[temporada]
    texto = texto.lower()
    achados = da_temporada[(da_temporada.team_abbreviation.str.lower() == texto)
                           | da_temporada.team_name.str.lower().str.contains(texto, regex=False)]
    if len(achados) != 1:
        opcoes = ", ".join(sorted(da_temporada.team_abbreviation))
        raise ValueError(f"Time '{texto}' não encontrado (ou ambíguo) em {temporada}. Opções: {opcoes}")
    return dados["times"].loc[(temporada, achados.index[0])]


def simular_confronto(dados, time_a, time_b, era, mando="a", n=10000, seed=None):
    """mando: "a" (time a com mando da série), "b" ou "neutro"."""
    liga, espalhamento = ambiente(dados, era)
    a, b = traduzir(time_a, dados, espalhamento), traduzir(time_b, dados, espalhamento)
    if mando == "b":
        a, b = b, a
    r = simular_series(a, b, liga, n=n, neutro=mando == "neutro", peso_mando=dados["pesos"].peso_mando, seed=seed)
    if mando == "b":
        r["chance_a"] = 1 - r["chance_a"]
        r["placares"] = {k.replace("a em", "x").replace("b em", "a em").replace("x", "b em"): v for k, v in r["placares"].items()}
        r["media_pts_a"], r["media_pts_b"] = r["media_pts_b"], r["media_pts_a"]
    return r


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return
    conexao = conectar()
    try:
        dados = carregar(conexao)
    finally:
        conexao.close()

    a = buscar_time(dados, sys.argv[1], sys.argv[2])
    b = buscar_time(dados, sys.argv[3], sys.argv[4])
    eras = [sys.argv[5]] if len(sys.argv) > 5 else list(ERAS)
    nome_a, nome_b = f"{a.team_name} {a.name[0]}", f"{b.team_name} {b.name[0]}"
    print(f"{nome_a} x {nome_b} (mando: {nome_a})\n")
    for era in eras:
        r = simular_confronto(dados, a, b, era, seed=1)
        print(f"{era:>10}: {100 * r['chance_a']:5.1f}% para {a.team_abbreviation} | "
              f"placar médio {r['media_pts_a']:.0f} x {r['media_pts_b']:.0f} | {r['jogos_medios']:.1f} jogos")


if __name__ == "__main__":
    main()
