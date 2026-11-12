# jogo-nba-eras

Simulador de séries melhor de 7 entre times de temporadas diferentes da NBA (1990-91 em diante), jogadas no ambiente de uma era escolhida.

Cada time é descrito pelos quatro fatores de Dean Oliver (eFG%, desperdícios, rebote ofensivo, lances livres), no ataque e na defesa, relativos à média da liga da sua temporada.

## Como rodar

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
cd scripts
..\.venv\Scripts\python coletar_jogos.py
..\.venv\Scripts\python coletar_jogadores.py
..\.venv\Scripts\python quatro_fatores.py
..\.venv\Scripts\python forca.py
cd ..
.venv\Scripts\streamlit run scripts\app.py
```

No Windows, deixe o projeto num caminho curto (ex.: `C:\projetos\jogo-nba-eras`): o Streamlit tem arquivos internos com nomes longos e a instalação falha se o caminho completo passar de 260 caracteres, a menos que o suporte a caminhos longos esteja ativado.

A coleta leva cerca de 15 minutos. Conferências e validações (opcionais): `conferir_jogadores.py`, `validar_playoffs.py`, `validar_jogadores.py`, `testes_eras.py`. Pela linha de comando: `confronto.py 2009-10 LAL 2016-17 GSW "anos 90"`.

API (com o banco já montado), a partir da raiz do projeto:

```powershell
.venv\Scripts\uvicorn --app-dir scripts api:app --reload
.venv\Scripts\python -m pytest tests
```

Documentação interativa em http://localhost:8000/docs.

Front em React (Node.js 20 ou mais novo), com a API ligada, em outro terminal:

```powershell
cd front
npm install
npm run dev
```

Abre em http://localhost:5173. Para apontar para outra API, defina `VITE_API_URL`.

## Como funciona

1. **Coleta** (`coletar_jogos.py`, `coletar_jogadores.py`): box score de cada time e de cada jogador em cada jogo, temporada regular e playoffs, via [`nba_api`](https://github.com/swar/nba_api).
2. **Quatro fatores** (`quatro_fatores.py`): ritmo, eficiência e quatro fatores de cada time-temporada, com a média da liga e o desvio de cada time em relação a ela; vantagem de mando de cada temporada.
3. **Força efetiva** (`forca.py`): saldo ajustado pelos adversários, saldo contra times bons, aproveitamento e séries vencidas nas duas temporadas anteriores, com pesos aprendidos numa regressão dos jogos de playoff. O que os quatro fatores não captam entra no simulador como bônus, junto com o desgaste (jogos de playoff antes da série).
4. **Simulador** (`simulador.py`): jogos posse a posse e séries (2-2-1-1-1, 2-3-2 ou 2-2-1) com mando de quadra. Cada probabilidade da posse é a média da era + o desvio do ataque + o desvio da defesa adversária. Quem abre vantagem além do esperado relaxa, o que deixa o espalhamento dos placares igual ao real (~13 pontos).
5. **Eras** (`eras.py`, `confronto.py`): ambiente médio de cada década (ou de uma temporada). O time leva para a outra era a sua posição relativa entre os times (escore z), que previu melhor as mudanças reais de ambiente do que manter a diferença absoluta.
6. **Jogadores** (`elenco.py`, `jogo_detalhado.py`): rotação "saudável" de cada time (quem terminou a temporada nele) e um jogo posse a posse com as mesmas probabilidades do simulador, decidindo quem fez cada lance: box score, relógio, narração e eliminações por faltas. Os minutos seguem os playoffs reais: o 1º da rotação joga 7% a mais que na temporada e 10% a mais em jogo decisivo; o 10º, 28% a menos.
7. **App** (`app.py`, Streamlit): escolha os times, a era e o mando e assista à série jogo a jogo, com mini-cartões, líderes, box score e atuações de destaque (40 pontos, triplo-duplo, 20-20, 15 assistências, 7 bolas de 3, 5 tocos, 6 roubos, quem decidiu no último minuto). Em jogo apertado, um pop-up oferece acompanhar o final lance a lance. As chances só aparecem quando a série termina.
8. **API** (`api.py`, FastAPI): o mesmo simulador servido para o front em React.
9. **Front** (`front/`, React + Vite): escolha dos times, da era e do mando; a série jogo a jogo, com final narrado lance a lance; e a revelação das chances no fim. A interface veste a era escolhida (TV dos anos 90, metal dos 2000, faixas diagonais dos 2010, escuro dos 2020) ou fica neutra, no modo escuro ou claro. O site é em inglês, pensando no público americano; código e documentação seguem em português.

| Endereço | O que devolve |
|---|---|
| `GET /temporadas` | As 36 temporadas |
| `GET /times?temporada=2016-17` | Times da temporada: campanha, saldo, força, selos de estilo e cestinhas |
| `GET /eras` | As eras com descrição, ritmo, volume de 3 e pontos por arremesso |
| `POST /serie` | Uma série jogo a jogo: placares, box scores, lances, manchetes, líderes e destaques (sem as chances) |
| `POST /revelar` | Chances de cada time, distribuição de 4-0 a 4-3 e o estilo de cada um na era |

Os testes (`tests/test_api.py`) conferem, entre outras coisas, que o box score soma o placar, que a mesma semente repete a série e que pedidos inválidos são recusados.

## Validação

- **Playoffs reais** (`validar_playoffs.py`): 540 séries de 1990-91 a 2025-26, previstas só com a temporada regular e pesos aprendidos sem a temporada prevista. 75,7% de acerto e Brier 0,167; o time com mando vence 73,9%.
- **Jogadores** (`validar_jogadores.py`): pontos, rebotes e assistências por 36 minutos simulados x reais com correlação de 0,93 a 0,96.
- **Eras** (`testes_eras.py`): não existe gabarito entre épocas; os testes checam que um time contra ele mesmo dá 50%, que a ordem dos times não importa, que o ranking quase não muda entre eras e que o garrafão vale mais nos anos 90 do que em 2020.

Não capta lesões, experiência individual em playoffs nem ajustes de técnico.

## Dados

`data/nba_eras.db` (SQLite, fora do Git; esquema em `sql/schema.sql`):

- `games`, `team_games`: box score de time de cada jogo.
- `player_games`: box score de cada jogador (~930 mil linhas). Entre 1990-91 e 1995-96 faltam alguns jogadores em ~4% dos jogos (menos de 1% dos pontos) e não existe +/-.
- `vw_confrontos`: cada time num jogo com as estatísticas do adversário ao lado.
- `fatores_time`, `liga`: quatro fatores por time-temporada (`liga_*` = média da liga, `rel_*` = desvio) e médias de cada temporada, com a vantagem de mando.
- `forca_time`, `pesos_forca`: força efetiva e bônus de cada time; pesos da força, do mando nos playoffs e do desgaste.

Projeto não oficial, sem vínculo com a NBA.
