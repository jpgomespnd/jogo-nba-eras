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
python coletar_jogadores.py
python conferir_jogadores.py
python quatro_fatores.py
python forca.py
python validar_playoffs.py
python testes_eras.py
python confronto.py 2009-10 LAL 2016-17 GSW "anos 90"
cd ..
streamlit run scripts/app.py
```

- `app.py`: protótipo em Streamlit. Escolha dois times, a era e o mando; assista a uma série jogo a jogo, com manchete e box score de cada jogo; no fim, veja a chance que cada um tinha, a distribuição de 4-0 a 4-3 e como cada time joga na era escolhida.

- `simulador.py`: jogos posse a posse e séries (2-2-1-1-1, 2-3-2 ou 2-2-1) com mando de quadra. Quem abre vantagem além do esperado relaxa, o que deixa o espalhamento dos placares igual ao real (~13 pontos).
- `forca.py`: força efetiva = saldo ajustado pelos adversários + saldo contra times bons + aproveitamento + séries vencidas nas duas temporadas anteriores, com pesos aprendidos nos jogos de playoff. O que os quatro fatores não captam entra como bônus no simulador, junto com o desgaste (jogos de playoff disputados antes da série).
- `validar_playoffs.py`: prevê cada série de playoff real usando só a temporada regular, com pesos aprendidos sem a temporada prevista.
- `eras.py`: ambiente médio de cada era (anos 90, 2000, 2010, 2020, ou uma temporada específica). O time leva para a outra era a sua posição relativa entre os times (escore z), que previu melhor as mudanças reais de ambiente do que manter a diferença absoluta.
- `confronto.py`: série entre dois times de quaisquer temporadas, jogada na era escolhida (ou em todas).
- `elenco.py`: rotação "saudável" de cada time-temporada (quem terminou a temporada no time, com os minutos médios; como num playoff, os principais mantêm seus minutos e a rotação encurta) e a participação de cada jogador em arremessos, rebotes, assistências, roubos, tocos e faltas.
- `jogo_detalhado.py`: um jogo posse a posse com as mesmas probabilidades do simulador, decidindo quem fez cada lance. Gera box score, relógio, narração e eliminações por faltas (quem está pendurado vai mais para o banco).
- `validar_jogadores.py`: compara a produção dos jogadores simulados com a real (correlação de 0,93 a 0,96 por 36 minutos).
- `testes_eras.py`: testes de coerência entre eras.

## Validação

540 séries de playoff (1990-91 a 2025-26): 75,7% de acerto, Brier 0,167. O time com mando vence 73,9% das séries.

Entre eras não existe gabarito; os testes de coerência checam que um time contra ele mesmo dá 50%, que a ordem dos times não importa, que o ranking dos times quase não muda de era para era e que o aproveitamento de 2 (garrafão) vale mais nos anos 90 do que em 2020. O app não capta experiência individual em playoffs, ajustes de técnico nem lesões.

## Dados

`data/nba_eras.db` (SQLite, fora do Git), via [`nba_api`](https://github.com/swar/nba_api):

- `games` e `team_games`: box score de time de cada jogo, temporada regular e playoffs.
- `player_games`: box score de cada jogador em cada jogo (~930 mil linhas). Entre 1990-91 e 1995-96 faltam alguns jogadores em cerca de 4% dos jogos (menos de 1% dos pontos) e não existe +/-; de 1996-97 em diante os dados batem com os placares.
- `vw_confrontos`: cada time num jogo com as estatísticas do adversário ao lado.
- `fatores_time`: quatro fatores, ritmo e eficiência por time e temporada, com a média da liga (`liga_*`) e o desvio em relação a ela (`rel_*`).
- `liga`: médias de cada temporada e a vantagem de mando (pontos a cada 100 posses).
- `forca_time`: variáveis de força, força efetiva e bônus de cada time.
- `pesos_forca`: pesos da força efetiva, do mando nos playoffs e do desgaste.

Projeto não oficial, sem vínculo com a NBA.
