import { useEffect, useRef, useState } from "react";

const VELOCIDADES = [1, 2, 4];
const QUARTO = 720;
const PRORROGACAO = 300;

// Relógio de jogo a partir do segundo corrido: quanto falta no período e qual é ele.
function relogio(segundo) {
  const regulamentar = 4 * QUARTO;
  let fim, periodo;
  if (segundo <= regulamentar) {
    const quarto = Math.max(1, Math.ceil(segundo / QUARTO));
    fim = quarto * QUARTO;
    periodo = `Q${quarto}`;
  } else {
    const extra = Math.ceil((segundo - regulamentar) / PRORROGACAO);
    fim = regulamentar + extra * PRORROGACAO;
    periodo = extra === 1 ? "OT" : `${extra}OT`;
  }
  const resto = Math.max(0, Math.floor(fim - segundo));
  return { periodo, tempo: `${Math.floor(resto / 60)}:${String(resto % 60).padStart(2, "0")}` };
}

function placarAntesDoFinal(jogo) {
  const lance = jogo.lances[jogo.inicio_do_final - 1] ?? { pts_a: 0, pts_b: 0, segundo: 0 };
  return { ...lance, ...relogio(lance.segundo) };
}

export function EscolhaDoFinal({ jogo, serie, aoAcompanhar, aoSimular }) {
  const caixa = useRef(null);
  const antes = placarAntesDoFinal(jogo);

  useEffect(() => {
    const dialogo = caixa.current;
    dialogo.showModal();
    return () => dialogo.close();
  }, []);

  return (
    <dialog ref={caixa} className="dialogo" aria-labelledby="titulo-final" onCancel={(e) => e.preventDefault()}>
      <h2 id="titulo-final">Game {jogo.numero} is coming down to the wire</h2>
      <p className="dialogo-placar placar-numero">
        {serie.time_a.sigla} {antes.pts_a}–{antes.pts_b} {serie.time_b.sigla}
      </p>
      <p>
        {antes.tempo} left in {antes.periodo}. How do you want to see the finish?
      </p>
      <div className="acoes">
        <button className="botao botao-principal" onClick={aoAcompanhar} autoFocus>
          Watch play by play
        </button>
        <button className="botao" onClick={aoSimular}>
          Simulate to the end
        </button>
      </div>
    </dialog>
  );
}

export default function FinalNarrado({ jogo, serie, aoTerminar }) {
  const lances = jogo.lances.slice(jogo.inicio_do_final);
  const ultimo = lances.at(-1).segundo;
  const [segundo, setSegundo] = useState(() => placarAntesDoFinal(jogo).segundo);
  const [velocidade, setVelocidade] = useState(1);

  // Um segundo de jogo a cada 1000/velocidade ms; trocar a velocidade não perde o ponto da narração.
  useEffect(() => {
    if (segundo > ultimo) {
      const fim = setTimeout(aoTerminar, 1800 / velocidade);
      return () => clearTimeout(fim);
    }
    const passo = setTimeout(() => setSegundo((s) => s + 1), 1000 / velocidade);
    return () => clearTimeout(passo);
  }, [segundo, velocidade, ultimo, aoTerminar]);

  const vistos = lances.filter((l) => l.segundo <= segundo);
  const placar = vistos.at(-1) ?? placarAntesDoFinal(jogo);
  const { periodo, tempo } = relogio(Math.min(segundo, ultimo));
  const acabou = segundo > ultimo;

  return (
    <article className="cartao-jogo final-narrado" aria-label={`Finish of game ${jogo.numero}`}>
      <div className="cartao-topo">
        <span>Game {jogo.numero} · live finish</span>
        {jogo.decisivo && <span className="selo-decisivo">Elimination game</span>}
      </div>

      <div className="placar">
        <div className="placar-lado lado-a">
          <span className="placar-sigla">{serie.time_a.sigla}</span>
          <span className="placar-numero placar-grande">{placar.pts_a}</span>
        </div>
        <span className="relogio">
          <span className="placar-numero">{acabou ? "Final" : tempo}</span>
          <span>{periodo}</span>
        </span>
        <div className="placar-lado lado-b">
          <span className="placar-numero placar-grande">{placar.pts_b}</span>
          <span className="placar-sigla">{serie.time_b.sigla}</span>
        </div>
      </div>

      <div className="narracao-controles">
        <div className="velocidades" role="radiogroup" aria-label="Speed">
          {VELOCIDADES.map((v) => (
            <button key={v} role="radio" aria-checked={velocidade === v} onClick={() => setVelocidade(v)}>
              {v}x
            </button>
          ))}
        </div>
        <button className="botao" onClick={aoTerminar}>
          Skip to the end of the game
        </button>
      </div>

      <ol className="lances" aria-live="polite">
        {vistos
          .map((l, i) => (
            <li key={i} className={l.time === serie.time_a.sigla ? "lance-a" : "lance-b"}>
              <span className="lance-relogio placar-numero">{l.relogio}</span>
              <span className="lance-time">{l.time}</span>
              <span>{l.texto}</span>
              {l.pontos > 0 && (
                <span className="lance-placar placar-numero">
                  {l.pts_a}-{l.pts_b}
                </span>
              )}
            </li>
          ))
          .reverse()}
      </ol>
    </article>
  );
}
