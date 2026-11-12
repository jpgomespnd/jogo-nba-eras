import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Aviso, Rodape, Topo } from "../componentes/Moldura.jsx";
import { comSinal, numero, porcento, rotuloDaEra } from "../formato.js";

const RESULTADOS = ["4-0", "4-1", "4-2", "4-3"];
const ESTILOS = [
  ["ritmo", "Possessions per game", (v) => numero(v, 1)],
  ["efg", "Effective field goal % (eFG)", (v) => porcento(v, 1)],
  ["volume_de_3", "Share of shots from 3", (v) => porcento(v)],
  ["desperdicios", "Turnover rate", (v) => porcento(v, 1)],
  ["rebote_ofensivo", "Offensive rebound rate", (v) => porcento(v)],
  ["lances_livres", "Free throws per shot", (v) => numero(v, 2)],
  ["efg_cedido", "Opponent eFG allowed", (v) => porcento(v, 1)],
  ["desperdicios_forcados", "Turnovers forced", (v) => porcento(v, 1)],
  ["rebote_defensivo", "Defensive rebound rate", (v) => porcento(v)],
  ["forca_extra", "Strength beyond the stats (points)", (v) => comSinal(v)],
];

// Médias de cada jogador na série, a partir dos box scores.
function lideresDaSerie(jogos, lado) {
  const soma = new Map();
  for (const jogo of jogos) {
    for (const l of jogo[`box_${lado}`]) {
      const s = soma.get(l.Jogador) ?? { jogador: l.Jogador, jogos: 0, PTS: 0, REB: 0, AST: 0 };
      s.jogos += 1;
      s.PTS += l.PTS;
      s.REB += l.REB;
      s.AST += l.AST;
      soma.set(l.Jogador, s);
    }
  }
  return [...soma.values()]
    .map((s) => ({ ...s, PTS: s.PTS / s.jogos, REB: s.REB / s.jogos, AST: s.AST / s.jogos }))
    .sort((x, y) => y.PTS - x.PTS)
    .slice(0, 3);
}

export default function Revelacao({ confronto, serie, aoNovaSerie, aoOutraEra, aoTrocarTimes }) {
  const [chances, setChances] = useState(null);
  const [erro, setErro] = useState(null);
  const [tentativa, setTentativa] = useState(0);

  const chave = JSON.stringify(confronto);
  useEffect(() => {
    api
      .revelar(JSON.parse(chave))
      .then(setChances)
      .catch((e) => setErro(e.message));
  }, [chave, tentativa]);

  const { time_a: a, time_b: b, jogos } = serie;
  const ultimo = jogos.at(-1);
  const lado = serie.vencedor;
  const vencedor = lado === "a" ? a : b;
  const perdedor = lado === "a" ? b : a;
  const resultado = `4-${Math.min(ultimo.vitorias_a, ultimo.vitorias_b)}`;
  const media = (campo) => jogos.reduce((t, j) => t + j[campo], 0) / jogos.length;

  return (
    <div className="tela">
      <Topo>
        <span className="topo-info">Series over · {rotuloDaEra(serie.era)}</span>
      </Topo>
      <main className="conteudo revelacao">
        <header className="revelacao-cabeca">
          <h1 className="revelacao-titulo">
            {vencedor.nome} {vencedor.temporada} win {resultado}
          </h1>
          <p className="revelacao-sub">
            Against the {perdedor.nome} {perdedor.temporada}, in {jogos.length} games under {rotuloDaEra(serie.era)} conditions.
          </p>
        </header>

        {!chances ? (
          <Aviso erro={erro} aoTentar={() => {
            setErro(null);
            setTentativa((n) => n + 1);
          }}>
            Simulating 10,000 series to find out who was favored…
          </Aviso>
        ) : (
          <>
            <Zebrometro chances={chances} lado={lado} vencedor={vencedor} />
            <div className="revelacao-grade">
              <Distribuicao chances={chances} a={a} b={b} lado={lado} resultado={resultado} />
              <section className="painel">
                <h2 className="titulo-secao">Average score</h2>
                <div className="comparacao">
                  <span className="lado-a">{a.sigla}</span>
                  <span>Across 10,000 series</span>
                  <span className="lado-b">{b.sigla}</span>
                  <b className="placar-numero">{numero(chances.media_pts_a, 1)}</b>
                  <span />
                  <b className="placar-numero">{numero(chances.media_pts_b, 1)}</b>
                  <b className="placar-numero">{numero(media("pts_a"), 1)}</b>
                  <span>This series</span>
                  <b className="placar-numero">{numero(media("pts_b"), 1)}</b>
                </div>
                <p className="nota">A series lasts {numero(chances.jogos_medios, 1)} games on average.</p>
              </section>
            </div>

            <section className="painel">
              <h2 className="titulo-secao">How each team plays in the <span className="era-rotulo">{rotuloDaEra(serie.era)}</span></h2>
              <div className="tabela-rolavel">
                <table className="estilos">
                  <thead>
                    <tr>
                      <th scope="col">
                        <span className="visualmente-oculto">Stat</span>
                      </th>
                      <th scope="col" className="lado-a">
                        {a.sigla} {a.temporada}
                      </th>
                      <th scope="col" className="lado-b">
                        {b.sigla} {b.temporada}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {ESTILOS.map(([campo, nome, formato]) => (
                      <tr key={campo}>
                        <th scope="row">{nome}</th>
                        <td className="placar-numero">{formato(chances.estilos.a[campo])}</td>
                        <td className="placar-numero">{formato(chances.estilos.b[campo])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        <section className="painel">
          <h2 className="titulo-secao">Who carried the series</h2>
          <div className="lideres-serie">
            {[
              ["a", a],
              ["b", b],
            ].map(([l, time]) => (
              <table key={l}>
                <caption className={`faixa-${l}`}>
                  {time.sigla} {time.temporada}, per game
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Player</th>
                    <th scope="col">PTS</th>
                    <th scope="col">REB</th>
                    <th scope="col">AST</th>
                  </tr>
                </thead>
                <tbody>
                  {lideresDaSerie(jogos, l).map((s) => (
                    <tr key={s.jogador}>
                      <th scope="row">{s.jogador}</th>
                      <td className="placar-numero">{numero(s.PTS, 1)}</td>
                      <td className="placar-numero">{numero(s.REB, 1)}</td>
                      <td className="placar-numero">{numero(s.AST, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ))}
          </div>
        </section>

        <div className="acoes acoes-fim">
          <button className="botao botao-principal" onClick={aoNovaSerie}>
            Play again
          </button>
          <button className="botao" onClick={aoOutraEra}>
            Play in another era
          </button>
          <button className="botao" onClick={aoTrocarTimes}>
            Change teams
          </button>
        </div>
      </main>
      <Rodape>Odds from 10,000 simulated series with the same teams, era and home court.</Rodape>
    </div>
  );
}

function Zebrometro({ chances, lado, vencedor }) {
  const chance = lado === "a" ? chances.chance_a : chances.chance_b;
  const zebra = chance < 0.5;
  return (
    <section className={`zebrometro ${zebra ? "zebra" : "logica"}`}>
      <p className="zebrometro-veredito">{zebra ? "Upset!" : "Chalk"}</p>
      <p>
        {zebra
          ? `Before the series, the ${vencedor.nome} were given only ${porcento(chance)} odds.`
          : `The ${vencedor.nome} were the favorites, at ${porcento(chance)}.`}
      </p>
      <div
        className="medidor"
        role="img"
        aria-label={`Each team's chance: ${porcento(chances.chance_a)} vs ${porcento(chances.chance_b)}`}
      >
        <span className="medidor-a" style={{ width: `${100 * chances.chance_a}%` }}>
          {porcento(chances.chance_a)}
        </span>
        <span className="medidor-b">{porcento(chances.chance_b)}</span>
      </div>
    </section>
  );
}

function Distribuicao({ chances, a, b, lado, resultado }) {
  const maior = Math.max(...RESULTADOS.flatMap((r) => [chances.placares.a[r], chances.placares.b[r]]));
  return (
    <section className="painel">
      <h2 className="titulo-secao">How the series usually ends</h2>
      <div className="distribuicao">
        {RESULTADOS.map((r) => (
          <div key={r} className="distribuicao-grupo">
            <div className="distribuicao-barras">
              {["a", "b"].map((l) => {
                const p = chances.placares[l][r];
                const aconteceu = l === lado && r === resultado;
                return (
                  <div key={l} className={`barra-coluna ${aconteceu ? "aconteceu" : ""}`}>
                    <span className="barra-valor">{porcento(p, p < 0.1 ? 1 : 0)}</span>
                    <span className={`barra lado-${l}`} style={{ height: `${(100 * p) / maior}%` }} />
                  </div>
                );
              })}
            </div>
            <span className="distribuicao-rotulo">{r}</span>
          </div>
        ))}
      </div>
      <p className="legenda">
        <span className="ponto lado-a" /> {a.sigla} wins <span className="ponto lado-b" /> {b.sigla} wins{" "}
        <span className="legenda-aconteceu">outlined: what happened</span>
      </p>
    </section>
  );
}
