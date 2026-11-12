// Os 7 jogos possíveis. Os que ainda não foram mostrados ficam vazios: não dá para saber quantos haverá.
export default function MiniCartoes({ serie, revelados, atual, aoVivo, aoEscolher }) {
  const { time_a: a, time_b: b } = serie;
  return (
    <ol className="mini-cartoes" aria-label="Series games">
      {Array.from({ length: 7 }, (_, i) => {
        const jogo = serie.jogos[i];
        if (i === aoVivo) {
          return (
            <li key={i}>
              <div className="mini mini-ao-vivo" aria-current="true">
                <span className="mini-numero">Game {i + 1}</span>
                <span className="mini-placar">Live finish</span>
              </div>
            </li>
          );
        }
        if (!jogo || i >= revelados) {
          const sobrou = revelados === serie.jogos.length && !jogo;
          return (
            <li key={i}>
              <div className="mini mini-vazio">
                <span className="mini-numero">Game {i + 1}</span>
                <span className="mini-placar">{sobrou ? "Not needed" : i >= 4 ? "If necessary" : ""}</span>
              </div>
            </li>
          );
        }
        const venceuA = jogo.pts_a > jogo.pts_b;
        return (
          <li key={i}>
            <button
              className={`mini venceu-${venceuA ? "a" : "b"}`}
              aria-current={i === atual ? "true" : undefined}
              onClick={() => aoEscolher(i)}
            >
              <span className="mini-numero">
                Game {i + 1}
                {jogo.decisivo && <span className="mini-decisivo"> · elimination</span>}
              </span>
              <span className="mini-placar placar-numero">
                {venceuA ? a.sigla : b.sigla} {Math.max(jogo.pts_a, jogo.pts_b)}-{Math.min(jogo.pts_a, jogo.pts_b)}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
