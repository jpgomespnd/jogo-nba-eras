import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PASTA_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(PASTA_SCRIPTS))

from banco import CAMINHO_BANCO  # noqa: E402
from elenco import TAXAS  # noqa: E402
from eras import METRICAS  # noqa: E402


@pytest.fixture(scope="session")
def cliente():
    if not CAMINHO_BANCO.exists():
        pytest.skip("Banco não encontrado: rode a coleta e os scripts de estatística antes dos testes")
    from fastapi.testclient import TestClient

    from api import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def dados_reais():
    if not CAMINHO_BANCO.exists():
        pytest.skip("Banco não encontrado: rode a coleta e os scripts de estatística antes dos testes")
    from banco import conectar
    from eras import carregar

    conexao = conectar()
    try:
        return carregar(conexao)
    finally:
        conexao.close()


# Dados fabricados, no mesmo formato de eras.carregar, para testar o simulador sem o banco (o banco não vai para o GitHub).
# Valores próximos dos reais: médias da liga dos anos 2010 e dos anos 90, desvios de times bons e ruins.
LIGA_2010 = {"pace": 97.7, "ortg": 104.9, "tov_pct": 0.146, "orb_pct": 0.245, "drb_pct": 0.755, "fta_rate": 0.272,
             "fg3a_rate": 0.290, "fg2_pct": 0.497, "fg3_pct": 0.356, "ft_pct": 0.761, "mando": 2.76}
LIGA_90 = {**LIGA_2010, "pace": 91.5, "ortg": 107.0, "tov_pct": 0.155, "orb_pct": 0.305, "drb_pct": 0.695,
           "fta_rate": 0.330, "fg3a_rate": 0.160, "fg2_pct": 0.480, "mando": 3.6}
TIMES = {
    ("2016-17", 1): {"rel_pace": 3.5, "rel_tov_pct": 0.003, "rel_opp_tov_pct": 0.011, "rel_fta_rate": -0.012,
                     "rel_opp_fta_rate": -0.010, "rel_fg3a_rate": 0.043, "rel_opp_fg3a_rate": -0.005,
                     "rel_fg2_pct": 0.054, "rel_opp_fg2_pct": -0.018, "rel_fg3_pct": 0.026, "rel_opp_fg3_pct": -0.034,
                     "rel_ft_pct": 0.016, "rel_orb_pct": -0.005, "rel_drb_pct": -0.018, "bonus": 0.3},
    ("2016-17", 2): {},
    ("1995-96", 3): {"rel_pace": -1.0, "rel_tov_pct": -0.012, "rel_opp_tov_pct": 0.020, "rel_fta_rate": 0.010,
                     "rel_opp_fta_rate": -0.020, "rel_fg3a_rate": 0.020, "rel_opp_fg3a_rate": 0.0,
                     "rel_fg2_pct": 0.030, "rel_opp_fg2_pct": -0.025, "rel_fg3_pct": 0.020, "rel_opp_fg3_pct": -0.015,
                     "rel_ft_pct": 0.0, "rel_orb_pct": 0.040, "rel_drb_pct": 0.020, "bonus": 1.0},
    ("1998-99", 4): {"rel_tov_pct": 0.015, "rel_opp_tov_pct": -0.010, "rel_fg2_pct": -0.030, "rel_opp_fg2_pct": 0.025,
                     "rel_fg3_pct": -0.020, "rel_orb_pct": -0.020, "rel_drb_pct": -0.015, "bonus": -1.0},
}


@pytest.fixture(scope="session")
def dados():
    colunas = [f"rel_{m}" for m in METRICAS] + ["bonus"]
    times = pd.DataFrame([{c: v.get(c, 0.0) for c in colunas} for v in TIMES.values()],
                         index=pd.MultiIndex.from_tuples(TIMES, names=["season", "team_id"]))
    times["team_abbreviation"] = ["GSW", "MED", "CHI", "FRA"]
    liga = pd.DataFrame([LIGA_90, {**LIGA_90, "pace": 88.9}, LIGA_2010], index=["1995-96", "1998-99", "2016-17"])
    for m in ["tov_pct", "fta_rate", "fg3a_rate", "fg2_pct", "fg3_pct"]:
        liga[f"opp_{m}"] = liga[m]
    espalhamento = pd.DataFrame([[0.02] * len(METRICAS), [0.018] * len(METRICAS), [0.025] * len(METRICAS)],
                                index=liga.index, columns=[f"rel_{m}" for m in METRICAS])
    espalhamento["rel_pace"] = [2.0, 1.8, 2.2]
    return {"times": times, "liga": liga, "pesos": pd.Series({"peso_mando": 1.32}), "espalhamento": espalhamento}


@pytest.fixture(scope="session")
def elenco():
    """Rotação de 9 jogadores e taxas de eventos, no formato de elenco.montar_elenco e elenco.taxas_do_time."""
    minutos = np.array([38, 36, 34, 32, 30, 26, 20, 14, 10], dtype=float)
    jogadores = pd.DataFrame({"player_name": [f"Jogador {i}" for i in range(1, 10)], "minutos": minutos})
    pesos = {taxa: minutos / 240 for taxa in TAXAS}
    um = np.ones(len(minutos))
    taxas = {"assistencia_por_cesta": 0.6, "roubo_por_desperdicio": 0.5, "toco_por_erro": 0.08,
             "faltas_extras_por_posse": 0.1}
    return {"jogadores": jogadores, "pesos": pesos, "rel_2": um, "rel_3": um, "rel_ll": um}, taxas
