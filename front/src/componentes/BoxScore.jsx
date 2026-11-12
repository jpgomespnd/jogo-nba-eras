import { useEffect, useRef } from "react";

const COLUNAS = ["MIN", "PTS", "REB", "AST", "ROB", "TOC", "ERR", "FAL", "ARR", "3P", "LL"];
// As chaves vêm da API em português; na tela aparecem as siglas e os nomes em inglês.
const SIGLAS = { ROB: "STL", TOC: "BLK", ERR: "TOV", FAL: "PF", ARR: "FG", "3P": "3PT", LL: "FT" };
const NOMES_DAS_COLUNAS = {
  MIN: "Minutes",
  PTS: "Points",
  REB: "Rebounds",
  AST: "Assists",
  ROB: "Steals",
  TOC: "Blocks",
  ERR: "Turnovers",
  FAL: "Personal fouls",
  ARR: "Field goals",
  "3P": "3-pointers",
  LL: "Free throws",
};

function Tabela({ time, linhas, lado }) {
  return (
    <div className="box-tabela">
      <table>
        <caption className={`faixa-${lado}`}>
          {time.nome} {time.temporada}
        </caption>
        <thead>
          <tr>
            <th scope="col">Player</th>
            {COLUNAS.map((c) => (
              <th key={c} scope="col" title={NOMES_DAS_COLUNAS[c]}>
                {SIGLAS[c] ?? c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => (
            <tr key={l.Jogador}>
              <th scope="row">
                {l.Jogador}
                {l.eliminado && <span className="etiqueta-falta">Fouled out</span>}
              </th>
              {COLUNAS.map((c) => (
                <td key={c}>{l[c]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Pop-up do box score: <dialog> nativo prende o foco, fecha com Esc e devolve o foco ao botão que o abriu.
export default function BoxScore({ jogo, serie, aoFechar }) {
  const caixa = useRef(null);

  // Sem close() na limpeza: ele dispararia onClose e fecharia o pop-up na remontagem do StrictMode.
  useEffect(() => {
    if (!caixa.current.open) caixa.current.showModal();
  }, []);

  const { time_a: a, time_b: b } = serie;
  return (
    <dialog
      ref={caixa}
      className="dialogo dialogo-box"
      aria-labelledby="titulo-box"
      onClose={aoFechar}
      onClick={(e) => e.target === caixa.current && aoFechar()}
    >
      <div className="dialogo-cabeca">
        <h2 id="titulo-box">
          Game {jogo.numero}: {a.sigla} {jogo.pts_a}–{jogo.pts_b} {b.sigla}
        </h2>
        <button className="botao botao-discreto" onClick={aoFechar} autoFocus>
          Close
        </button>
      </div>
      <Tabela time={a} linhas={jogo.box_a} lado="a" />
      <Tabela time={b} linhas={jogo.box_b} lado="b" />
    </dialog>
  );
}
