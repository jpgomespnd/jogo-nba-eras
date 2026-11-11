"""Série entre dois times de quaisquer temporadas, jogada no ambiente de uma era escolhida.

Uso: confronto.py TEMPORADA_A TIME_A TEMPORADA_B TIME_B [ERA]
Exemplo: confronto.py 2009-10 LAL 2016-17 GSW "anos 90"
"""

import sys

import numpy as np

from banco import conectar
from elenco import montar_elenco, taxas_do_time
from eras import ERAS, ambiente, carregar, traduzir
from jogo_detalhado import jogar_detalhado
from simulador import FORMATOS, simular_series


def buscar_time(dados, temporada, texto):
    da_temporada = dados["times"].loc[temporada]
    texto = texto.lower()
    achados = da_temporada[(da_temporada.team_abbreviation.str.lower() == texto)
                           | da_temporada.team_name.str.lower().str.contains(texto, regex=False)]
    if len(achados) != 1:
        opcoes = ", ".join(sorted(da_temporada.team_abbreviation))
        raise ValueError(f"Time '{texto}' não encontrado (ou ambíguo) em {temporada}. Opções: {opcoes}")
    return dados["times"].loc[(temporada, achados.index[0])]


def preparar(dados, time_a, time_b, era):
    liga, espalhamento = ambiente(dados, era)
    return traduzir(time_a, dados, espalhamento), traduzir(time_b, dados, espalhamento), liga


def carregar_elenco(dados, chave):
    """Rotação e taxas de eventos (assistências, roubos, tocos, faltas) de um time-temporada."""
    conexao = conectar()
    try:
        return montar_elenco(conexao, chave[0], chave[1]), taxas_do_time(conexao, chave[0], chave[1], dados["times"])
    finally:
        conexao.close()


def manchete(numero, vencedor, perdedor, box_vencedor, box_perdedor, prorrogacoes):
    destaque = box_vencedor.loc[box_vencedor.PTS.idxmax()]
    bolas_de_3 = int(destaque["3P"].split("-")[0])
    feito = f"{destaque.Jogador} faz {destaque.PTS}"
    if bolas_de_3 >= 5:
        feito += f" com {bolas_de_3} bolas de 3"
    elif destaque.REB >= 12:
        feito += f" e pega {destaque.REB} rebotes"
    elif destaque.AST >= 10:
        feito += f" e dá {destaque.AST} assistências"
    texto = f"{feito} e o {vencedor} vence o jogo {numero}"
    if prorrogacoes:
        texto += " na prorrogação" if prorrogacoes == 1 else f" em {prorrogacoes} prorrogações"
    do_vencedor = list(box_vencedor[box_vencedor.eliminado].Jogador)
    do_perdedor = list(box_perdedor[box_perdedor.eliminado].Jogador)
    if do_vencedor:
        texto += f", mesmo com {' e '.join(do_vencedor)} eliminado{'s' if len(do_vencedor) > 1 else ''} por faltas"
    if do_perdedor:
        texto += f". O {perdedor} perdeu {' e '.join(do_perdedor)} por faltas"
    return texto


def narrar_serie(dados, time_a, time_b, era, elencos, mando="a", siglas=("A", "B"), seed=None):
    """Uma série possível, jogo a jogo, com box score, lances e manchete de cada jogo.

    elencos: ((elenco_a, taxas_a), (elenco_b, taxas_b)), de carregar_elenco.
    """
    a, b, liga = preparar(dados, time_a, time_b, era)
    (elenco_a, taxas_a), (elenco_b, taxas_b) = elencos
    rng = np.random.default_rng(seed)
    neutro = mando == "neutro"
    peso = dados["pesos"].peso_mando
    jogos, vitorias_a, vitorias_b = [], 0, 0
    for numero, primeiro_em_casa in enumerate(FORMATOS["2-2-1-1-1"], start=1):
        a_em_casa = bool(primeiro_em_casa) != (mando == "b")
        if a_em_casa:
            j = jogar_detalhado(a, b, liga, elenco_a, elenco_b, taxas_a, taxas_b, rng, neutro, peso, siglas)
            pts_a, pts_b, box_a, box_b = j["pts_casa"], j["pts_fora"], j["box_casa"], j["box_fora"]
        else:
            j = jogar_detalhado(b, a, liga, elenco_b, elenco_a, taxas_b, taxas_a, rng, neutro, peso, siglas[::-1])
            pts_a, pts_b, box_a, box_b = j["pts_fora"], j["pts_casa"], j["box_fora"], j["box_casa"]
        vitorias_a += pts_a > pts_b
        vitorias_b += pts_b > pts_a
        if pts_a > pts_b:
            titulo = manchete(numero, siglas[0], siglas[1], box_a, box_b, j["prorrogacoes"])
        else:
            titulo = manchete(numero, siglas[1], siglas[0], box_b, box_a, j["prorrogacoes"])
        jogos.append({"jogo": numero, "a_em_casa": None if neutro else a_em_casa, "pts_a": pts_a, "pts_b": pts_b,
                      "vitorias_a": vitorias_a, "vitorias_b": vitorias_b, "box_a": box_a, "box_b": box_b,
                      "lances": j["lances"], "prorrogacoes": j["prorrogacoes"], "manchete": titulo})
        if 4 in (vitorias_a, vitorias_b):
            return jogos
    return jogos


def simular_confronto(dados, time_a, time_b, era, mando="a", n=10000, seed=None):
    """mando: "a" (time a com mando da série), "b" ou "neutro"."""
    a, b, liga = preparar(dados, time_a, time_b, era)
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
