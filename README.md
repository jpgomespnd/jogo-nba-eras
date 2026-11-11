# jogo-nba-eras

Simulador de séries melhor de 7 entre times de temporadas diferentes da NBA (1990-91 em diante), jogadas no ambiente de uma era escolhida.

Cada time é descrito pelos quatro fatores de Dean Oliver (eFG%, desperdícios, rebote ofensivo, lances livres), no ataque e na defesa, relativos à média da liga da sua temporada.

## Como rodar

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd scripts
python coletar_jogos.py
python quatro_fatores.py
python validar_playoffs.py
```

`simulador.py` simula jogos posse a posse e séries (2-2-1-1-1, 2-3-2 ou 2-2-1) com mando de quadra. `validar_playoffs.py` prevê cada série de playoff real usando só a temporada regular.

## Dados

`data/nba_eras.db` (SQLite, fora do Git), via [`nba_api`](https://github.com/swar/nba_api):

- `games` e `team_games`: box score de time de cada jogo, temporada regular e playoffs.
- `vw_confrontos`: cada time num jogo com as estatísticas do adversário ao lado.
- `fatores_time`: quatro fatores, ritmo e eficiência por time e temporada, com a média da liga (`liga_*`) e o desvio em relação a ela (`rel_*`).
- `liga`: médias de cada temporada e a vantagem de mando (pontos a cada 100 posses).

Projeto não oficial, sem vínculo com a NBA.
