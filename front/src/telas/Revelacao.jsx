import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Aviso, Rodape, Topo } from "../componentes/Moldura.jsx";
import { comSinal, numero, porcento } from "../formato.js";

const RESULTADOS = ["4-0", "4-1", "4-2", "4-3"];
const ESTILOS = [
  ["ritmo", "Posses por jogo", (v) => numero(v, 1)],
  ["efg", "Aproveitamento efetivo (eFG)", (v) => porcento(v, 1)],
  ["volume_de_3", "Arremessos que são de 3", (v) => porcento(v)],
  ["desperdicios", "Posses desperdiçadas", (v) => porcento(v, 1)],
  ["rebote_ofensivo", "Rebotes ofensivos pegos", (v) => porcento(v)],
  ["lances_livres", "Lances livres por arremesso", (v) => numero(v, 2)],
  ["efg_cedido", "eFG que a defesa cede", (v) => porcento(v, 1)],
  ["desperdicios_forcados", "Desperdícios que a defesa força", (v) => porcento(v, 1)],
  ["rebote_defensivo", "Rebotes defensivos pegos", (v) => porcento(v)],
  ["forca_extra", "Força além dos números (pontos)", (v) => comSinal(v)],
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
        <span className="topo-info">Fim de série · {serie.era}</span>
      </Topo>
      <main className="conteudo revelacao">
        <header className="revelacao-cabeca">
          <h1 className="revelacao-titulo">
            {vencedor.nome} {vencedor.temporada} vence por {resultado}
          </h1>
          <p className="revelacao-sub">
            Contra o {perdedor.nome} {perdedor.temporada}, em {jogos.length} jogos nos {serie.era}.
          </p>
        </header>

        {!chances ? (
          <Aviso erro={erro} aoTentar={() => {
            setErro(null);
            setTentativa((n) => n + 1);
          }}>
            Simulando 10 mil séries para saber quem era o favorito…
          </Aviso>
        ) : (
          <>
            <Zebrometro chances={chances} lado={lado} vencedor={vencedor} />
            <div className="revelacao-grade">
              <Distribuicao chances={chances} a={a} b={b} lado={lado} resultado={resultado} />
              <section className="painel">
                <h2 className="titulo-secao">Placar médio</h2>
                <div className="comparacao">
                  <span className="lado-a">{a.sigla}</span>
                  <span>Nas 10 mil séries</span>
                  <span className="lado-b">{b.sigla}</span>
                  <b className="placar-numero">{numero(chances.media_pts_a, 1)}</b>
                  <span />
                  <b className="placar-numero">{numero(chances.media_pts_b, 1)}</b>
                  <b className="placar-numero">{numero(media("pts_a"), 1)}</b>
                  <span>Nesta série</span>
                  <b className="placar-numero">{numero(media("pts_b"), 1)}</b>
                </div>
                <p className="nota">Uma série dura em média {numero(chances.jogos_medios, 1)} jogos.</p>
              </section>
            </div>

            <section className="painel">
              <h2 className="titulo-secao">Como cada um joga nos {serie.era}</h2>
              <div className="tabela-rolavel">
                <table className="estilos">
                  <thead>
                    <tr>
                      <th scope="col">
                        <span className="visualmente-oculto">Estatística</span>
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
          <h2 className="titulo-secao">Quem carregou a série</h2>
          <div className="lideres-serie">
            {[
              ["a", a],
              ["b", b],
            ].map(([l, time]) => (
              <table key={l}>
                <caption className={`faixa-${l}`}>
                  {time.sigla} {time.temporada}, médias por jogo
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Jogador</th>
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
            Jogar de novo
          </button>
          <button className="botao" onClick={aoOutraEra}>
            Jogar em outra era
          </button>
          <button className="botao" onClick={aoTrocarTimes}>
            Trocar times
          </button>
        </div>
      </main>
      <Rodape>Chances calculadas em 10 mil séries simuladas com os mesmos times, era e mando.</Rodape>
    </div>
  );
}

function Zebrometro({ chances, lado, vencedor }) {
  const chance = lado === "a" ? chances.chance_a : chances.chance_b;
  const zebra = chance < 0.5;
  return (
    <section className={`zebrometro ${zebra ? "zebra" : "logica"}`}>
      <p className="zebrometro-veredito">{zebra ? "Zebra!" : "Deu a lógica"}</p>
      <p>
        {zebra
          ? `Antes da série, o ${vencedor.nome} tinha só ${porcento(chance)} de chance.`
          : `O ${vencedor.nome} era favorito, com ${porcento(chance)} de chance.`}
      </p>
      <div
        className="medidor"
        role="img"
        aria-label={`Chance de cada time: ${porcento(chances.chance_a)} contra ${porcento(chances.chance_b)}`}
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
      <h2 className="titulo-secao">Como a série costuma terminar</h2>
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
        <span className="ponto lado-a" /> {a.sigla} vence <span className="ponto lado-b" /> {b.sigla} vence{" "}
        <span className="legenda-aconteceu">contorno: o que aconteceu</span>
      </p>
    </section>
  );
}
