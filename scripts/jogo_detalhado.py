"""Um jogo posse a posse com jogadores: box score, relógio e a narração de cada lance.

As probabilidades de cada posse são as mesmas do simulador validado; o elenco só decide quem fez cada coisa.
"""

import numpy as np
import pandas as pd

from elenco import escolher
from simulador import AMORTECIMENTO, CALIBRACAO_MANDO, DESVIO_RITMO, ataque, pontos_esperados

LIMITE_FALTAS = 6
FICA_NO_BANCO = 0.5
SEGUNDOS_QUARTO = 720
SEGUNDOS_PRORROGACAO = 300
ESTATISTICAS = ["pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "pf"]


class Lado:
    def __init__(self, sigla, time, adversario, liga, elenco, taxas):
        self.sigla = sigla
        self.ataque = ataque(time, adversario, liga)
        self.elenco = elenco
        self.taxas = taxas
        completos = list(elenco["jogadores"].player_name)
        sobrenomes = [n.split(" ")[-1] for n in completos]
        self.nomes = [s if sobrenomes.count(s) == 1 else n for s, n in zip(sobrenomes, completos)]
        self.box = {e: np.zeros(len(self.nomes), dtype=int) for e in ESTATISTICAS}
        self.eliminado_em = {}
        self.segundo = 0.0

    def peso(self, taxa):
        p = self.elenco["pesos"][taxa].copy()
        # Pendurado em faltas (2 no 1º quarto, 3 no 2º, 4 no 3º, 5 no 4º): vai mais para o banco.
        limite = min(int(self.segundo // SEGUNDOS_QUARTO) + 2, LIMITE_FALTAS - 1)
        p[self.box["pf"] >= limite] *= FICA_NO_BANCO
        for i in self.eliminado_em:
            p[i] = 0.0
        return p


def falta(defesa, segundo, lances, contexto):
    i = escolher(defesa.peso("pf"), contexto["rng"])
    if i is None:
        return
    defesa.box["pf"][i] += 1
    if defesa.box["pf"][i] == LIMITE_FALTAS:
        defesa.eliminado_em[i] = segundo
        lances.append(f"{defesa.nomes[i]} ({defesa.sigla}) comete a 6ª falta e está eliminado")


def posse(atk, defesa, fator, segundo, contexto):
    """Joga uma posse; devolve os pontos e o texto do lance."""
    rng, a = contexto["rng"], atk.ataque
    atk.segundo = defesa.segundo = segundo
    lances = []
    if rng.random() < defesa.taxas["faltas_extras_por_posse"]:
        falta(defesa, segundo, lances, contexto)

    if rng.random() < a.tov:
        i = escolher(atk.peso("tov"), rng)
        atk.box["tov"][i] += 1
        texto = f"Desperdício de {atk.nomes[i]}"
        if rng.random() < defesa.taxas["roubo_por_desperdicio"]:
            j = escolher(defesa.peso("stl"), rng)
            defesa.box["stl"][j] += 1
            texto += f", roubo de {defesa.nomes[j]}"
        return 0, lances + [texto]

    while True:
        if rng.random() < a.lance_livre:
            i = escolher(atk.peso("fta"), rng)
            falta(defesa, segundo, lances, contexto)
            chance = min(a.acerto_ll * atk.elenco["rel_ll"][i], 0.98)
            acertos = int(rng.random() < chance) + int(rng.random() < chance)
            atk.box["fta"][i] += 2
            atk.box["ftm"][i] += acertos
            atk.box["pts"][i] += acertos
            return acertos, lances + [f"{atk.nomes[i]} converte {acertos} de 2 lances livres"]

        de_3 = rng.random() < a.tentativa_3
        i = escolher(atk.peso("fg3a" if de_3 else "fg2a"), rng)
        base = a.acerto_3 * atk.elenco["rel_3"][i] if de_3 else a.acerto_2 * atk.elenco["rel_2"][i]
        atk.box["fga"][i] += 1
        atk.box["fg3a"][i] += de_3
        tipo = "de 3" if de_3 else "de 2"
        if rng.random() < min(base * fator, 0.95):
            valor = 3 if de_3 else 2
            atk.box["fgm"][i] += 1
            atk.box["fg3m"][i] += de_3
            atk.box["pts"][i] += valor
            texto = f"{atk.nomes[i]} acerta {tipo}"
            if rng.random() < atk.taxas["assistencia_por_cesta"]:
                j = escolher(atk.peso("ast"), rng, excluir=i)
                if j is not None:
                    atk.box["ast"][j] += 1
                    texto += f" (assistência de {atk.nomes[j]})"
            return valor, lances + [texto]

        texto = f"{atk.nomes[i]} erra {tipo}"
        if rng.random() < defesa.taxas["toco_por_erro"]:
            j = escolher(defesa.peso("blk"), rng)
            defesa.box["blk"][j] += 1
            texto += f", toco de {defesa.nomes[j]}"
        if rng.random() < a.rebote_of:
            j = escolher(atk.peso("oreb"), rng)
            atk.box["oreb"][j] += 1
            lances.append(texto + f"; rebote ofensivo de {atk.nomes[j]}")
            continue
        j = escolher(defesa.peso("dreb"), rng)
        defesa.box["dreb"][j] += 1
        return 0, lances + [texto + f"; rebote de {defesa.nomes[j]}"]


def relogio(segundo):
    if segundo < 4 * SEGUNDOS_QUARTO:
        periodo, restante = int(segundo // SEGUNDOS_QUARTO) + 1, SEGUNDOS_QUARTO - segundo % SEGUNDOS_QUARTO
        nome = f"{periodo}º quarto"
    else:
        extra = segundo - 4 * SEGUNDOS_QUARTO
        periodo, restante = int(extra // SEGUNDOS_PRORROGACAO) + 1, SEGUNDOS_PRORROGACAO - extra % SEGUNDOS_PRORROGACAO
        nome = f"{periodo}ª prorrogação"
    restante = int(round(restante))
    return nome, f"{restante // 60}:{restante % 60:02d}"


def montar_box(lado, duracao_minutos):
    jogadores = lado.elenco["jogadores"]
    minutos = jogadores.minutos.to_numpy() * duracao_minutos / 48
    for i, segundo in lado.eliminado_em.items():
        minutos[i] *= segundo / (duracao_minutos * 60)
    livres = [i for i in range(len(minutos)) if i not in lado.eliminado_em]
    falta_distribuir = 5 * duracao_minutos - minutos.sum()
    minutos[livres] += falta_distribuir * minutos[livres] / minutos[livres].sum()

    box = pd.DataFrame({"Jogador": jogadores.player_name, "MIN": np.round(minutos).astype(int)})
    b = lado.box
    box["PTS"] = b["pts"]
    box["REB"] = b["oreb"] + b["dreb"]
    box["AST"] = b["ast"]
    box["ROB"] = b["stl"]
    box["TOC"] = b["blk"]
    box["ERR"] = b["tov"]
    box["FAL"] = b["pf"]
    box["ARR"] = [f"{m}-{t}" for m, t in zip(b["fgm"], b["fga"])]
    box["3P"] = [f"{m}-{t}" for m, t in zip(b["fg3m"], b["fg3a"])]
    box["LL"] = [f"{m}-{t}" for m, t in zip(b["ftm"], b["fta"])]
    box["eliminado"] = [i in lado.eliminado_em for i in range(len(box))]
    return box


def jogar_detalhado(casa, fora, liga, elenco_casa, elenco_fora, taxas_casa, taxas_fora, rng,
                    neutro=False, peso_mando=1.0, siglas=("CASA", "FORA")):
    mando = 0.0 if neutro else peso_mando * liga["mando"]
    bonus = casa.get("bonus", 0.0) - fora.get("bonus", 0.0)
    vantagem = (mando + bonus) / (2 * CALIBRACAO_MANDO * liga["ortg"])
    lado_casa = Lado(siglas[0], casa, fora, liga, elenco_casa, taxas_casa)
    lado_fora = Lado(siglas[1], fora, casa, liga, elenco_fora, taxas_fora)
    saldo_por_posse = (pontos_esperados(lado_casa.ataque, 1 + vantagem)
                       - pontos_esperados(lado_fora.ataque, 1 - vantagem))
    ritmo = liga["pace"] + casa["rel_pace"] + fora["rel_pace"]
    contexto = {"rng": rng}

    placar = {"casa": 0, "fora": 0}
    lances = []

    def jogar_periodo(inicio, segundos, posses):
        duracao = segundos / (2 * posses)
        diferenca_inicial = placar["casa"] - placar["fora"]
        for k in range(posses):
            for quem, atk, defesa in (("casa", lado_casa, lado_fora), ("fora", lado_fora, lado_casa)):
                segundo = inicio + (2 * k + (quem == "fora") + 1) * duracao
                sorte = (placar["casa"] - placar["fora"] - diferenca_inicial - k * saldo_por_posse) / 100
                ajuste = vantagem - AMORTECIMENTO * sorte
                fator = 1 + ajuste if quem == "casa" else 1 - ajuste
                pontos, textos = posse(atk, defesa, fator, segundo, contexto)
                placar[quem] += pontos
                segundo = min(segundo, inicio + segundos - 1)
                periodo, tempo = relogio(segundo)
                for texto in textos:
                    lances.append({"segundo": segundo, "periodo": periodo, "relogio": tempo, "time": atk.sigla, "texto": texto,
                                   "pontos": pontos if texto is textos[-1] else 0,
                                   "placar_casa": placar["casa"], "placar_fora": placar["fora"]})

    posses = max(int(round(rng.normal(ritmo, DESVIO_RITMO))), 60)
    jogar_periodo(0, 4 * SEGUNDOS_QUARTO, posses)
    prorrogacoes = 0
    while placar["casa"] == placar["fora"]:
        jogar_periodo(4 * SEGUNDOS_QUARTO + prorrogacoes * SEGUNDOS_PRORROGACAO, SEGUNDOS_PRORROGACAO,
                      max(int(round(ritmo * 5 / 48)), 1))
        prorrogacoes += 1

    duracao = 48 + 5 * prorrogacoes
    return {
        "pts_casa": placar["casa"], "pts_fora": placar["fora"], "prorrogacoes": prorrogacoes,
        "box_casa": montar_box(lado_casa, duracao), "box_fora": montar_box(lado_fora, duracao), "lances": lances,
    }
