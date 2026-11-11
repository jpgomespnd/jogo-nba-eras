"""Série entre dois times de quaisquer temporadas, jogada no ambiente de uma era escolhida.

Uso: confronto.py TEMPORADA_A TIME_A TEMPORADA_B TIME_B [ERA]
Exemplo: confronto.py 2009-10 LAL 2016-17 GSW "anos 90"
"""

import re
import sys

import numpy as np
import pandas as pd

from banco import conectar
from elenco import CONSULTA_JOGADORES, montar_elenco, taxas_do_time
from eras import ERAS, ambiente, carregar, traduzir
from jogo_detalhado import jogar_detalhado
from simulador import FORMATOS, simular_series

SEGUNDOS_REGULAMENTO = 48 * 60
# Final apertado: até 5 pontos de diferença com 2 minutos para acabar.
SEGUNDOS_FINAL = 120
DIFERENCA_APERTADO = 5


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
        jogos_temporada = pd.read_sql(CONSULTA_JOGADORES, conexao, params=(chave[0],))
        elencos = {contexto: montar_elenco(conexao, chave[0], chave[1], jogos_temporada, contexto)
                   for contexto in ("playoffs", "decisivo")}
        return elencos, taxas_do_time(conexao, chave[0], chave[1], dados["times"])
    finally:
        conexao.close()


def atuacoes(box, sigla):
    """Atuações raras num jogo de playoff (cortes escolhidos pela frequência real desde 1990-91).

    Devolve (prioridade, selo, texto); quanto menor a prioridade, mais rara a atuação.
    """
    achados = []
    for _, j in box.iterrows():
        bolas_de_3 = int(j["3P"].split("-")[0])
        dois_digitos = sum(v >= 10 for v in (j.PTS, j.REB, j.AST, j.ROB, j.TOC))
        quem = f"{j.Jogador} ({sigla})"
        if j.PTS >= 50:
            achados.append((0, "50 pontos", f"{quem} explode com {j.PTS} pontos"))
        elif j.PTS >= 40:
            achados.append((2, "40 pontos", f"Noite de {j.PTS} pontos de {quem}"))
        if dois_digitos >= 3:
            achados.append((1, "triplo-duplo", f"Triplo-duplo de {quem}: {j.PTS} pts, {j.REB} reb, {j.AST} ast"))
        elif j.PTS >= 20 and j.REB >= 20:
            achados.append((1, "20-20", f"{quem} domina o garrafão: {j.PTS} pontos e {j.REB} rebotes"))
        elif j.REB >= 20:
            achados.append((3, "20 rebotes", f"{quem} pega {j.REB} rebotes"))
        if j.AST >= 15:
            achados.append((3, "assistências", f"{quem} distribui {j.AST} assistências"))
        if bolas_de_3 >= 7:
            achados.append((3, "chuva de 3", f"{quem} acerta {bolas_de_3} bolas de 3"))
        if j.TOC >= 5:
            achados.append((4, "tocos", f"{quem} dá {j.TOC} tocos"))
        if j.ROB >= 6:
            achados.append((4, "roubos", f"{quem} rouba {j.ROB} bolas"))
    return achados


def decidiu_no_fim(lances, a_venceu, siglas, box_vencedor):
    """Quem fez a cesta que colocou o vencedor na frente de vez, se foi no último minuto."""
    sigla_vencedor = siglas[0] if a_venceu else siglas[1]
    virada = None
    for lance in lances:
        lider = siglas[0] if lance["pts_a"] > lance["pts_b"] else siglas[1] if lance["pts_b"] > lance["pts_a"] else None
        if lider != sigla_vencedor:
            virada = None
        elif virada is None and lance["pontos"]:
            virada = lance
    fim = lances[-1]["segundo"]
    if virada is None or fim - virada["segundo"] > 60:
        return None
    autor = re.match(r"^(.*?) (acerta|converte)", virada["texto"])
    if not autor:
        return None
    curto = autor.group(1)
    nome = next((n for n in box_vencedor.Jogador if n == curto or n.endswith(" " + curto)), curto)
    return (0, "decidiu no fim", f"{nome} ({sigla_vencedor}) decide o jogo a {virada['relogio']} do fim")


def destaques_do_jogo(box_a, box_b, lances, a_venceu, siglas, maximo=3):
    achados = atuacoes(box_a, siglas[0]) + atuacoes(box_b, siglas[1])
    no_fim = decidiu_no_fim(lances, a_venceu, siglas, box_a if a_venceu else box_b)
    if no_fim:
        achados.append(no_fim)
    return [(selo, texto) for _, selo, texto in sorted(achados, key=lambda a: a[0])[:maximo]]


def lideres(box):
    return {estat: (box.loc[box[estat].idxmax(), "Jogador"], int(box[estat].max())) for estat in ("PTS", "REB", "AST")}


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


def inicio_do_final(lances):
    """Índice do primeiro lance dos 2 minutos finais se o jogo estava apertado (até 5 pontos); senão None."""
    antes = (0, 0)
    for k, lance in enumerate(lances):
        if lance["segundo"] >= SEGUNDOS_REGULAMENTO - SEGUNDOS_FINAL:
            return k if abs(antes[0] - antes[1]) <= DIFERENCA_APERTADO else None
        antes = (lance["pts_a"], lance["pts_b"])
    return None


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
        # Jogo decisivo: um dos times pode ser eliminado; a rotação encurta ainda mais.
        decisivo = 3 in (vitorias_a, vitorias_b)
        contexto = "decisivo" if decisivo else "playoffs"
        ea, eb = elenco_a[contexto], elenco_b[contexto]
        if a_em_casa:
            j = jogar_detalhado(a, b, liga, ea, eb, taxas_a, taxas_b, rng, neutro, peso, siglas)
            pts_a, pts_b, box_a, box_b = j["pts_casa"], j["pts_fora"], j["box_casa"], j["box_fora"]
        else:
            j = jogar_detalhado(b, a, liga, eb, ea, taxas_b, taxas_a, rng, neutro, peso, siglas[::-1])
            pts_a, pts_b, box_a, box_b = j["pts_fora"], j["pts_casa"], j["box_fora"], j["box_casa"]
        vitorias_a += pts_a > pts_b
        vitorias_b += pts_b > pts_a
        if pts_a > pts_b:
            titulo = manchete(numero, siglas[0], siglas[1], box_a, box_b, j["prorrogacoes"])
        else:
            titulo = manchete(numero, siglas[1], siglas[0], box_b, box_a, j["prorrogacoes"])
        lances = [{**l, "pts_a": l["placar_casa"] if a_em_casa else l["placar_fora"],
                   "pts_b": l["placar_fora"] if a_em_casa else l["placar_casa"]} for l in j["lances"]]
        jogos.append({"jogo": numero, "a_em_casa": None if neutro else a_em_casa, "pts_a": pts_a, "pts_b": pts_b,
                      "vitorias_a": vitorias_a, "vitorias_b": vitorias_b, "box_a": box_a, "box_b": box_b,
                      "lances": lances, "inicio_final": inicio_do_final(lances),
                      "prorrogacoes": j["prorrogacoes"], "manchete": titulo,
                      "decisivo": decisivo, "lideres": (lideres(box_a), lideres(box_b)),
                      "destaques": destaques_do_jogo(box_a, box_b, lances, pts_a > pts_b, siglas)})
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
        # A simulação rodou com B no lugar de A: desfaz a troca nos resultados.
        trocar = {"a": "b", "b": "a"}
        r["chance_a"] = 1 - r["chance_a"]
        r["placares"] = {f"{trocar[k[0]]}{k[1:]}": v for k, v in r["placares"].items()}
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
