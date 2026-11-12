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


def estilo_na_era(time, liga):
    """Como um time (já traduzido para a era) joga no ambiente dela: ritmo, quatro fatores e força extra."""
    def valor(m):
        return liga[m] + time[f"rel_{m}"]

    def efg(prefixo=""):
        tres = valor(f"{prefixo}fg3a_rate")
        return (1 - tres) * valor(f"{prefixo}fg2_pct") + tres * valor(f"{prefixo}fg3_pct") * 1.5

    return {
        "ritmo": float(valor("pace")),
        "efg": float(efg()),
        "volume_de_3": float(valor("fg3a_rate")),
        "desperdicios": float(valor("tov_pct")),
        "rebote_ofensivo": float(valor("orb_pct")),
        "lances_livres": float(valor("fta_rate")),
        "efg_cedido": float(efg("opp_")),
        "desperdicios_forcados": float(valor("opp_tov_pct")),
        "rebote_defensivo": float(valor("drb_pct")),
        "forca_extra": float(time["bonus"]),
    }


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
            achados.append((0, "50 points", f"{quem} erupts for {j.PTS} points"))
        elif j.PTS >= 40:
            achados.append((2, "40 points", f"{j.PTS}-point night for {quem}"))
        if dois_digitos >= 3:
            achados.append((1, "triple-double", f"Triple-double for {quem}: {j.PTS} pts, {j.REB} reb, {j.AST} ast"))
        elif j.PTS >= 20 and j.REB >= 20:
            achados.append((1, "20-20", f"{quem} owns the paint: {j.PTS} points and {j.REB} rebounds"))
        elif j.REB >= 20:
            achados.append((3, "20 rebounds", f"{quem} grabs {j.REB} rebounds"))
        if j.AST >= 15:
            achados.append((3, "assists", f"{quem} dishes out {j.AST} assists"))
        if bolas_de_3 >= 7:
            achados.append((3, "from downtown", f"{quem} drains {bolas_de_3} threes"))
        if j.TOC >= 5:
            achados.append((4, "blocks", f"{quem} swats {j.TOC} shots"))
        if j.ROB >= 6:
            achados.append((4, "steals", f"{quem} racks up {j.ROB} steals"))
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
    autor = re.match(r"^(.*?) makes ", virada["texto"])
    if not autor:
        return None
    curto = autor.group(1)
    nome = next((n for n in box_vencedor.Jogador if n == curto or n.endswith(" " + curto)), curto)
    return (0, "clutch", f"{nome} ({sigla_vencedor}) puts it away with {virada['relogio']} left")


def destaques_do_jogo(box_a, box_b, lances, a_venceu, siglas, maximo=3):
    achados = atuacoes(box_a, siglas[0]) + atuacoes(box_b, siglas[1])
    no_fim = decidiu_no_fim(lances, a_venceu, siglas, box_a if a_venceu else box_b)
    if no_fim:
        achados.append(no_fim)
    return [(selo, texto) for _, selo, texto in sorted(achados, key=lambda a: a[0])[:maximo]]


def lideres(box):
    return {estat: (box.loc[box[estat].idxmax(), "Jogador"], int(box[estat].max())) for estat in ("PTS", "REB", "AST")}


def game_score(box):
    """Game Score de Hollinger de cada linha do box score (sem separar rebote ofensivo e defensivo: 0,5 por rebote)."""
    def feitos(coluna):
        partes = box[coluna].str.split("-", expand=True).astype(int)
        return partes[0], partes[1]

    fgm, fga = feitos("ARR")
    ftm, fta = feitos("LL")
    return (box.PTS + 0.4 * fgm - 0.7 * fga - 0.4 * (fta - ftm) + 0.5 * box.REB + box.ROB
            + 0.7 * box.AST + 0.7 * box.TOC - 0.4 * box.FAL - box.ERR)


def mvp_da_serie(jogos, a_venceu):
    """Jogador do time campeão com a maior soma de Game Score na série, com suas médias por jogo."""
    boxes = [j["box_a"] if a_venceu else j["box_b"] for j in jogos]
    linhas = pd.concat([box.assign(game_score=game_score(box)) for box in boxes])
    por_jogador = linhas.groupby("Jogador").agg(jogos=("PTS", "size"), total=("game_score", "sum"),
                                                PTS=("PTS", "mean"), REB=("REB", "mean"), AST=("AST", "mean"))
    melhor = por_jogador.total.idxmax()
    m = por_jogador.loc[melhor]
    return {"jogador": melhor, "pontos": round(float(m.PTS), 1), "rebotes": round(float(m.REB), 1),
            "assistencias": round(float(m.AST), 1)}


def manchete(numero, vencedor, box_vencedor, prorrogacoes):
    destaque = box_vencedor.loc[box_vencedor.PTS.idxmax()]
    bolas_de_3 = int(destaque["3P"].split("-")[0])
    feito = f"{destaque.Jogador} scores {destaque.PTS}"
    if bolas_de_3 >= 5:
        feito += f" with {bolas_de_3} threes"
    elif destaque.REB >= 12:
        feito += f" and grabs {destaque.REB} rebounds"
    elif destaque.AST >= 10:
        feito += f" and dishes out {destaque.AST} assists"
    texto = f"{feito} as {vencedor} win Game {numero}"
    if prorrogacoes:
        texto += " in overtime" if prorrogacoes == 1 else f" in {prorrogacoes} overtimes"
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
            titulo = manchete(numero, siglas[0], box_a, j["prorrogacoes"])
        else:
            titulo = manchete(numero, siglas[1], box_b, j["prorrogacoes"])
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
