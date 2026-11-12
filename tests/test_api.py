LAKERS, WARRIORS = 1610612747, 1610612744
CONFRONTO = {"temporada_a": "2009-10", "time_a": LAKERS, "temporada_b": "2016-17", "time_b": WARRIORS,
             "era": "anos 90", "mando": "a"}


def test_saude(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "temporadas": 36}


def test_temporadas_vao_de_1990_a_2025(cliente):
    temporadas = cliente.get("/temporadas").json()
    assert temporadas[0] == "2025-26"
    assert temporadas[-1] == "1990-91"


def test_times_traz_campanha_selos_e_destaques(cliente):
    times = {t["sigla"]: t for t in cliente.get("/times", params={"temporada": "2016-17"}).json()}
    gsw = times["GSW"]
    assert (gsw["vitorias"], gsw["derrotas"]) == (67, 15)
    assert 1 <= len(gsw["selos"]) <= 3
    assert {d["jogador"] for d in gsw["destaques"]} & {"Stephen Curry", "Kevin Durant"}


def test_temporada_inexistente_da_404(cliente):
    assert cliente.get("/times", params={"temporada": "1980-81"}).status_code == 404


def test_eras(cliente):
    eras = cliente.get("/eras").json()
    assert [e["nome"] for e in eras] == ["anos 90", "anos 2000", "anos 2010", "anos 2020"]
    assert eras[0]["volume_de_3"] < eras[-1]["volume_de_3"]


def test_serie_termina_quando_alguem_faz_4(cliente):
    serie = cliente.post("/serie", json=CONFRONTO).json()
    jogos = serie["jogos"]
    assert 4 <= len(jogos) <= 7
    ultimo = jogos[-1]
    assert max(ultimo["vitorias_a"], ultimo["vitorias_b"]) == 4
    assert serie["vencedor"] == ("a" if ultimo["vitorias_a"] == 4 else "b")
    box_do_campeao = ultimo["box_a"] if serie["vencedor"] == "a" else ultimo["box_b"]
    assert serie["mvp"]["jogador"] in {j["Jogador"] for j in box_do_campeao}


def test_box_score_soma_o_placar(cliente):
    jogo = cliente.post("/serie", json=CONFRONTO).json()["jogos"][0]
    assert sum(j["PTS"] for j in jogo["box_a"]) == jogo["pts_a"]
    assert sum(j["PTS"] for j in jogo["box_b"]) == jogo["pts_b"]
    assert sum(lance["pontos"] for lance in jogo["lances"]) == jogo["pts_a"] + jogo["pts_b"]


def test_mesma_semente_mesma_serie(cliente):
    pedido = {**CONFRONTO, "semente": 7}
    placares = lambda s: [(j["pts_a"], j["pts_b"]) for j in s["jogos"]]
    assert placares(cliente.post("/serie", json=pedido).json()) == placares(cliente.post("/serie", json=pedido).json())


def test_time_inexistente_da_404(cliente):
    assert cliente.post("/serie", json={**CONFRONTO, "time_a": 123}).status_code == 404


def test_era_inexistente_da_422(cliente):
    assert cliente.post("/serie", json={**CONFRONTO, "era": "anos 70"}).status_code == 422


def test_mando_invalido_da_422(cliente):
    assert cliente.post("/serie", json={**CONFRONTO, "mando": "casa"}).status_code == 422


def test_revelar_chances_e_placares(cliente):
    r = cliente.post("/revelar", json=CONFRONTO).json()
    assert abs(r["chance_a"] + r["chance_b"] - 1) < 1e-9
    total = sum(r["placares"]["a"].values()) + sum(r["placares"]["b"].values())
    assert abs(total - 1) < 1e-9
    assert abs(sum(r["placares"]["a"].values()) - r["chance_a"]) < 1e-9
    assert set(r["estilos"]["a"]) == set(r["estilos"]["b"])


def test_revelar_bate_com_a_validacao_conhecida(cliente):
    # Lakers 2009-10 x Warriors 2016-17 nos anos 90, mando do Lakers: 18,9% (semente fixa).
    assert round(cliente.post("/revelar", json=CONFRONTO).json()["chance_a"], 3) == 0.189


def test_trocar_o_mando_favorece_quem_joga_em_casa(cliente):
    com_mando = cliente.post("/revelar", json=CONFRONTO).json()["chance_a"]
    sem_mando = cliente.post("/revelar", json={**CONFRONTO, "mando": "b"}).json()["chance_a"]
    assert com_mando > sem_mando
