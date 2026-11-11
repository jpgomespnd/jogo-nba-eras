"""API do jogo-nba-eras: o simulador servido em endereços para o front.

Rodar da raiz do projeto: uvicorn --app-dir scripts api:app --reload
Documentação interativa: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from banco import conectar
from confronto import carregar_elenco, estilo_na_era, narrar_serie, preparar, simular_confronto
from elenco import CONSULTA_JOGADORES, rotacao
from eras import DESCRICOES, ERAS, ambiente, carregar

SIMULACOES = 10000
# Endereço do front em desenvolvimento (Vite); só ele pode chamar a API pelo navegador.
ORIGENS_DO_FRONT = ["http://localhost:5173", "http://127.0.0.1:5173"]
# Selos de estilo: coluna, sentido (+1 = acima da média é bom) e texto. Entram os desvios de 1 espalhamento ou mais.
SELOS = [
    ("rel_ortg", 1, "Ataque de elite"),
    ("rel_drtg", -1, "Defesa de elite"),
    ("rel_fg3a_rate", 1, "Bombardeiro de 3"),
    ("rel_fg3_pct", 1, "Mão calibrada de 3"),
    ("rel_orb_pct", 1, "Dono do rebote ofensivo"),
    ("rel_drb_pct", 1, "Fecha o rebote defensivo"),
    ("rel_pace", 1, "Ritmo acelerado"),
    ("rel_pace", -1, "Ritmo cadenciado"),
    ("rel_tov_pct", -1, "Cuida da bola"),
    ("rel_opp_tov_pct", 1, "Defesa que rouba bolas"),
    ("rel_fta_rate", 1, "Vive na linha de lance livre"),
    ("rel_opp_fg2_pct", -1, "Muralha no garrafão"),
    ("rel_opp_fg3_pct", -1, "Fecha o perímetro"),
]
MAXIMO_SELOS = 3
DADOS = {}


@asynccontextmanager
async def ciclo_de_vida(_app):
    conexao = conectar()
    try:
        DADOS.update(carregar(conexao))
    finally:
        conexao.close()
    yield


app = FastAPI(title="jogo-nba-eras", description="Séries melhor de 7 entre times de épocas diferentes da NBA.",
              lifespan=ciclo_de_vida)
app.add_middleware(CORSMiddleware, allow_origins=ORIGENS_DO_FRONT, allow_methods=["*"], allow_headers=["*"])


class Confronto(BaseModel):
    temporada_a: str = Field(examples=["2009-10"])
    time_a: int = Field(description="team_id, como vem de /times", examples=[1610612747])
    temporada_b: str = Field(examples=["2016-17"])
    time_b: int = Field(examples=[1610612744])
    era: str = Field(default="anos 2000", description="Nome da década (de /eras) ou uma temporada, como 2004-05")
    mando: Literal["a", "b", "neutro"] = "a"


class PedidoSerie(Confronto):
    semente: int = Field(default=0, description="A mesma semente devolve a mesma série")


def nativo(valor):
    """Converte números do numpy e tabelas do pandas para tipos que viram JSON."""
    if isinstance(valor, dict):
        return {k: nativo(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [nativo(v) for v in valor]
    if isinstance(valor, pd.DataFrame):
        return nativo(valor.to_dict("records"))
    if isinstance(valor, np.generic):
        return valor.item()
    return valor


def buscar_time(temporada, team_id):
    try:
        return DADOS["times"].loc[(temporada, team_id)]
    except KeyError:
        raise HTTPException(404, f"Time {team_id} não encontrado em {temporada}") from None


def validar_era(era):
    if era not in ERAS and era not in DADOS["liga"].index:
        raise HTTPException(422, f"Era '{era}' não existe. Use uma de {list(ERAS)} ou uma temporada.")


def siglas(a, b):
    sigla_a, sigla_b = a.team_abbreviation, b.team_abbreviation
    if sigla_a == sigla_b:
        return f"{sigla_a} {a.name[0][2:4]}", f"{sigla_b} {b.name[0][2:4]}"
    return sigla_a, sigla_b


def resumo_do_time(time, sigla):
    return {"id": time.name[1], "temporada": time.name[0], "sigla": sigla, "nome": time.team_name,
            "vitorias": time.vitorias, "derrotas": time.jogos - time.vitorias}


def preparar_confronto(pedido):
    validar_era(pedido.era)
    a = buscar_time(pedido.temporada_a, pedido.time_a)
    b = buscar_time(pedido.temporada_b, pedido.time_b)
    return a, b, siglas(a, b)


@lru_cache(maxsize=64)
def elenco(temporada, team_id):
    return carregar_elenco(DADOS, (temporada, team_id))


@lru_cache(maxsize=8)
def cestinhas_da_temporada(temporada):
    conexao = conectar()
    try:
        return pd.read_sql(CONSULTA_JOGADORES, conexao, params=(temporada,))
    finally:
        conexao.close()


def selos(time, da_temporada):
    escores = []
    for coluna, sentido, texto in SELOS:
        z = sentido * (time[coluna] - da_temporada[coluna].mean()) / da_temporada[coluna].std()
        if z >= 1:
            escores.append((z, texto))
    return [texto for _, texto in sorted(escores, reverse=True)[:MAXIMO_SELOS]]


@app.get("/saude")
def saude():
    return {"status": "ok", "temporadas": len(DADOS["liga"])}


@app.get("/temporadas")
def temporadas():
    return sorted(DADOS["liga"].index, reverse=True)


@app.get("/times")
def times(temporada: str = Query(examples=["2016-17"])):
    if temporada not in DADOS["liga"].index:
        raise HTTPException(404, f"Temporada '{temporada}' não existe")
    da_temporada = DADOS["times"].loc[temporada]
    jogos = cestinhas_da_temporada(temporada)
    resposta = []
    for team_id, time in da_temporada.sort_values("team_name").iterrows():
        rot = rotacao(jogos, team_id).assign(ppg=lambda r: r.pts / r.jogos).nlargest(3, "ppg")
        resposta.append({
            "id": team_id, "sigla": time.team_abbreviation, "nome": time.team_name,
            "vitorias": time.vitorias, "derrotas": time.jogos - time.vitorias,
            "saldo": round(float(time.net), 1), "forca": round(float(time.forca), 1),
            "selos": selos(time, da_temporada),
            "destaques": [{"jogador": n, "pontos_por_jogo": round(float(p), 1)} for n, p in zip(rot.player_name, rot.ppg)],
        })
    return nativo(resposta)


@app.get("/eras")
def eras():
    resposta = []
    for nome, (inicio, fim) in ERAS.items():
        liga, _ = ambiente(DADOS, nome)
        resposta.append({
            "nome": nome, "descricao": DESCRICOES[nome], "inicio": inicio, "fim": fim,
            "ritmo": round(float(liga.pace), 1), "volume_de_3": round(float(liga.fg3a_rate), 3),
            "pontos_por_arremesso_de_2": round(float(2 * liga.fg2_pct), 2),
            "pontos_por_arremesso_de_3": round(float(3 * liga.fg3_pct), 2),
        })
    return resposta


def jogo_para_json(j):
    return {
        "numero": j["jogo"], "a_em_casa": j["a_em_casa"], "pts_a": j["pts_a"], "pts_b": j["pts_b"],
        "vitorias_a": j["vitorias_a"], "vitorias_b": j["vitorias_b"], "prorrogacoes": j["prorrogacoes"],
        "decisivo": j["decisivo"], "manchete": j["manchete"],
        "lideres": [{e: {"jogador": n, "valor": v} for e, (n, v) in lado.items()} for lado in j["lideres"]],
        "destaques": [{"selo": s, "texto": t} for s, t in j["destaques"]],
        "box_a": j["box_a"], "box_b": j["box_b"],
        "lances": j["lances"], "inicio_do_final": j["inicio_final"],
    }


@app.post("/serie")
def serie(pedido: PedidoSerie):
    """Uma série possível, jogo a jogo. Não traz chances: elas ficam para /revelar, no fim."""
    a, b, (sigla_a, sigla_b) = preparar_confronto(pedido)
    elencos = (elenco(pedido.temporada_a, pedido.time_a), elenco(pedido.temporada_b, pedido.time_b))
    jogos = narrar_serie(DADOS, a, b, pedido.era, elencos, pedido.mando, (sigla_a, sigla_b), seed=pedido.semente)
    ultimo = jogos[-1]
    return nativo({
        "time_a": resumo_do_time(a, sigla_a), "time_b": resumo_do_time(b, sigla_b),
        "era": pedido.era, "mando": pedido.mando, "semente": pedido.semente,
        "vencedor": "a" if ultimo["vitorias_a"] == 4 else "b",
        "jogos": [jogo_para_json(j) for j in jogos],
    })


@lru_cache(maxsize=128)
def simular(temporada_a, time_a, temporada_b, time_b, era, mando):
    return simular_confronto(DADOS, DADOS["times"].loc[(temporada_a, time_a)], DADOS["times"].loc[(temporada_b, time_b)],
                             era, mando, n=SIMULACOES, seed=1)


@app.post("/revelar")
def revelar(pedido: Confronto):
    """As chances de cada time, a distribuição de 4-0 a 4-3 e como cada um joga na era escolhida."""
    a, b, (sigla_a, sigla_b) = preparar_confronto(pedido)
    r = simular(pedido.temporada_a, pedido.time_a, pedido.temporada_b, pedido.time_b, pedido.era, pedido.mando)
    ta, tb, liga = preparar(DADOS, a, b, pedido.era)
    return nativo({
        "time_a": resumo_do_time(a, sigla_a), "time_b": resumo_do_time(b, sigla_b),
        "simulacoes": SIMULACOES,
        "chance_a": r["chance_a"], "chance_b": 1 - r["chance_a"],
        "placares": {lado: {f"4-{j - 4}": r["placares"][f"{lado} em {j}"] for j in range(4, 8)} for lado in ("a", "b")},
        "media_pts_a": r["media_pts_a"], "media_pts_b": r["media_pts_b"], "jogos_medios": r["jogos_medios"],
        "estilos": {"a": estilo_na_era(ta, liga), "b": estilo_na_era(tb, liga)},
    })
