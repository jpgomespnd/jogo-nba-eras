"""Protótipo: escolha dois times de quaisquer temporadas e a era em que eles jogam.

Rodar da raiz do projeto: streamlit run scripts/app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

from banco import conectar
from confronto import narrar_serie, preparar, simular_confronto
from eras import ERAS, carregar

SIMULACOES = 10000
COR_A, COR_B = "#2a78d6", "#eb6834"
DESCRICAO_ERAS = {
    "anos 90": "Jogo lento e físico, com hand-checking e poucas bolas de 3. O arremesso de 2 vale 0,96 ponto e o de 3 vale 1,03: quem chutava de longe explorava uma vantagem que a liga ignorava.",
    "anos 2000": "Ritmo mais baixo da história e defesas fortes. O hand-checking acaba em 2004 e o volume de 3 começa a subir.",
    "anos 2010": "Spacing e a revolução da bola de 3, com quase 30% dos arremessos de longe no fim da década.",
    "anos 2020": "Ritmo alto e 40% dos arremessos de 3. Arremesso de 2 e de 3 valem o mesmo: cerca de 1,08 ponto.",
}


@st.cache_resource
def dados():
    conexao = conectar()
    try:
        return carregar(conexao)
    finally:
        conexao.close()


@st.cache_data
def simular(chave_a, chave_b, era, mando):
    d = dados()
    return simular_confronto(d, d["times"].loc[chave_a], d["times"].loc[chave_b], era, mando, n=SIMULACOES, seed=1)


def escolher_time(rotulo, coluna, temporada_padrao, sigla_padrao):
    d = dados()
    temporadas = sorted(d["liga"].index, reverse=True)
    temporada = coluna.selectbox(f"Temporada do {rotulo}", temporadas, index=temporadas.index(temporada_padrao))
    da_temporada = d["times"].loc[temporada].sort_values("team_name")
    ids = list(da_temporada.index)
    padrao = da_temporada.index[da_temporada.team_abbreviation == sigla_padrao]
    team_id = coluna.selectbox(
        rotulo, ids, index=ids.index(padrao[0]) if len(padrao) else 0,
        format_func=lambda i: f"{da_temporada.loc[i, 'team_name']} ({da_temporada.loc[i, 'vitorias']}-"
                              f"{da_temporada.loc[i, 'jogos'] - da_temporada.loc[i, 'vitorias']})",
    )
    return temporada, team_id


def nome(chave):
    time = dados()["times"].loc[chave]
    return f"{time.team_name} {chave[0]}", time.team_abbreviation


def grafico_placares(r, sigla_a, sigla_b):
    linhas = []
    for jogos in range(4, 8):
        linhas.append({"placar": f"4-{jogos - 4}", "time": sigla_a, "chance": r["placares"][f"a em {jogos}"]})
        linhas.append({"placar": f"4-{jogos - 4}", "time": sigla_b, "chance": r["placares"][f"b em {jogos}"]})
    tabela = pd.DataFrame(linhas)
    return (
        alt.Chart(tabela)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("placar:N", title="Resultado da série", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("time:N", sort=[sigla_a, sigla_b]),
            y=alt.Y("chance:Q", title=None, axis=alt.Axis(format="%", grid=True, tickCount=4)),
            color=alt.Color("time:N", sort=[sigla_a, sigla_b], scale=alt.Scale(range=[COR_A, COR_B]),
                            legend=alt.Legend(title=None, orient="top")),
            tooltip=[alt.Tooltip("time:N", title="Vence"), alt.Tooltip("placar:N", title="Série"),
                     alt.Tooltip("chance:Q", title="Chance", format=".1%")],
        )
        .properties(height=260)
    )


def comparar_estilos(chave_a, chave_b, era):
    d = dados()
    a, b, liga = preparar(d, d["times"].loc[chave_a], d["times"].loc[chave_b], era)

    def na_era(time):
        valor = lambda m: liga[m] + time[f"rel_{m}"]
        efg = (1 - valor("fg3a_rate")) * valor("fg2_pct") + valor("fg3a_rate") * valor("fg3_pct") * 1.5
        opp_efg = (1 - valor("opp_fg3a_rate")) * valor("opp_fg2_pct") + valor("opp_fg3a_rate") * valor("opp_fg3_pct") * 1.5
        return {
            "Ritmo (posses por jogo)": f"{valor('pace'):.1f}",
            "Ataque: aproveitamento efetivo (eFG%)": f"{100 * efg:.1f}%",
            "Ataque: arremessos de 3": f"{100 * valor('fg3a_rate'):.1f}%",
            "Ataque: desperdícios por posse": f"{100 * valor('tov_pct'):.1f}%",
            "Ataque: rebote ofensivo": f"{100 * valor('orb_pct'):.1f}%",
            "Ataque: lances livres por arremesso": f"{100 * valor('fta_rate'):.1f}%",
            "Defesa: eFG% cedido": f"{100 * opp_efg:.1f}%",
            "Defesa: desperdícios forçados": f"{100 * valor('opp_tov_pct'):.1f}%",
            "Defesa: rebote defensivo": f"{100 * valor('drb_pct'):.1f}%",
            "Força extra (saldo a cada 100 posses)": f"{time['bonus']:+.1f}",
        }

    return pd.DataFrame({nome(chave_a)[1]: na_era(a), nome(chave_b)[1]: na_era(b)})


def serie_narrada(chave_a, chave_b, era, mando, sigla_a, sigla_b):
    contexto = (chave_a, chave_b, era, mando)
    estado = st.session_state
    if estado.get("contexto") != contexto:
        estado.contexto, estado.semente, estado.mostrados = contexto, 0, 0

    d = dados()
    jogos = narrar_serie(d, d["times"].loc[chave_a], d["times"].loc[chave_b], era, mando, seed=estado.semente)

    def mostrar(quantidade):
        estado.mostrados = quantidade

    def nova_serie():
        estado.semente += 1
        estado.mostrados = 0

    acabou = estado.mostrados >= len(jogos)
    botoes = st.columns(3)
    botoes[0].button("Começar a série" if estado.mostrados == 0 else "Próximo jogo", disabled=acabou,
                     on_click=mostrar, args=(estado.mostrados + 1,), use_container_width=True)
    botoes[1].button("Ver a série inteira", disabled=acabou, on_click=mostrar, args=(len(jogos),),
                     use_container_width=True)
    botoes[2].button("Nova série", on_click=nova_serie, use_container_width=True)

    for j in jogos[:estado.mostrados]:
        vencedor = sigla_a if j["pts_a"] > j["pts_b"] else sigla_b
        local = "quadra neutra" if j["a_em_casa"] is None else f"em casa: {sigla_a if j['a_em_casa'] else sigla_b}"
        st.markdown(
            f"**Jogo {j['jogo']}** · {sigla_a} **{j['pts_a']}** x **{j['pts_b']}** {sigla_b} · {local} · "
            f"vitória do {vencedor} · série {sigla_a} {j['vitorias_a']}-{j['vitorias_b']} {sigla_b}"
        )
    if estado.mostrados < len(jogos):
        return None
    ultimo = jogos[-1]
    a_venceu = ultimo["vitorias_a"] == 4
    st.success(f"{sigla_a if a_venceu else sigla_b} vence a série por {max(ultimo['vitorias_a'], ultimo['vitorias_b'])}-"
               f"{min(ultimo['vitorias_a'], ultimo['vitorias_b'])}.")
    return a_venceu


def revelar(chave_a, chave_b, era, mando, sigla_a, sigla_b, a_venceu):
    r = simular(chave_a, chave_b, era, mando)
    chance_vencedor = r["chance_a"] if a_venceu else 1 - r["chance_a"]
    vencedor = sigla_a if a_venceu else sigla_b
    st.divider()
    st.subheader("O que a simulação dizia")
    if chance_vencedor < 0.5:
        st.markdown(f"**Zebra!** Antes da série, o {vencedor} tinha só **{100 * chance_vencedor:.0f}%** de chance.")
    else:
        st.markdown(f"Deu a lógica: o {vencedor} era favorito, com **{100 * chance_vencedor:.0f}%** de chance.")

    m1, m2, m3 = st.columns(3)
    m1.metric(f"Chance do {sigla_a}", f"{100 * r['chance_a']:.0f}%")
    m2.metric(f"Chance do {sigla_b}", f"{100 * (1 - r['chance_a']):.0f}%")
    m3.metric("Placar médio por jogo", f"{r['media_pts_a']:.0f} x {r['media_pts_b']:.0f}")
    st.altair_chart(grafico_placares(r, sigla_a, sigla_b), use_container_width=True)
    st.caption(f"{SIMULACOES:,} séries simuladas posse a posse. Duração média: {r['jogos_medios']:.1f} jogos.".replace(",", "."))

    with st.expander(f"Como cada time joga nos {era}"):
        st.table(comparar_estilos(chave_a, chave_b, era))
        st.caption("Cada time mantém sua posição relativa entre os times da própria temporada, aplicada ao ambiente da era escolhida.")


def main():
    st.set_page_config(page_title="jogo-nba-eras", page_icon="🏀", layout="centered")
    st.title("jogo-nba-eras")
    st.caption("Dois times de quaisquer temporadas desde 1990-91, numa série melhor de 7 jogada na era que você escolher.")

    col_a, col_b = st.columns(2)
    chave_a = escolher_time("Time A", col_a, "2009-10", "LAL")
    chave_b = escolher_time("Time B", col_b, "2016-17", "GSW")
    nome_a, sigla_a = nome(chave_a)
    nome_b, sigla_b = nome(chave_b)
    if sigla_a == sigla_b:
        sigla_a, sigla_b = f"{sigla_a} {chave_a[0][2:4]}", f"{sigla_b} {chave_b[0][2:4]}"

    era = st.radio("Era em que a série é jogada", list(ERAS), index=1, horizontal=True)
    st.caption(DESCRICAO_ERAS[era])
    opcoes_mando = {"a": f"{nome_a}", "b": f"{nome_b}", "neutro": "Quadra neutra"}
    mando = st.radio("Mando de quadra da série", list(opcoes_mando), format_func=opcoes_mando.get, horizontal=True)

    st.divider()
    st.subheader(f"{nome_a} x {nome_b}")
    st.caption("Assista à série jogo a jogo. As chances aparecem quando ela terminar.")
    a_venceu = serie_narrada(chave_a, chave_b, era, mando, sigla_a, sigla_b)
    if a_venceu is not None:
        revelar(chave_a, chave_b, era, mando, sigla_a, sigla_b, a_venceu)

    st.divider()
    st.caption("Não capta lesões, experiência individual em playoffs nem ajustes de técnico. "
               "Projeto não oficial, sem vínculo com a NBA. Dados: nba_api.")


main()
