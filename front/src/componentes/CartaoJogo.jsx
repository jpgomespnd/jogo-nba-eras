const ESTATISTICAS = [
  ["PTS", "points"],
  ["REB", "rebounds"],
  ["AST", "assists"],
];

function localDoJogo(jogo, serie) {
  if (serie.mando === "neutro") return "Neutral court";
  return `At ${jogo.a_em_casa ? serie.time_a.sigla : serie.time_b.sigla}`;
}

export default function CartaoJogo({ jogo, serie, aoAbrirBox }) {
  const { time_a: a, time_b: b } = serie;
  const venceuA = jogo.pts_a > jogo.pts_b;
  const prorrogacao = jogo.prorrogacoes
    ? jogo.prorrogacoes === 1
      ? "OT"
      : `${jogo.prorrogacoes}OT`
    : null;

  return (
    <article className="cartao-jogo" aria-label={`Game ${jogo.numero}`}>
      <div className="cartao-topo">
        <span>
          Game {jogo.numero} · {localDoJogo(jogo, serie)}
        </span>
        {jogo.decisivo && <span className="selo-decisivo">Elimination game</span>}
      </div>

      <div className="placar">
        <div className={`placar-lado lado-a ${venceuA ? "vencedor" : ""}`}>
          <span className="placar-sigla">{a.sigla}</span>
          <span className="placar-numero placar-grande">{jogo.pts_a}</span>
        </div>
        <span className="placar-final">{prorrogacao ? `Final/${prorrogacao}` : "Final"}</span>
        <div className={`placar-lado lado-b ${venceuA ? "" : "vencedor"}`}>
          <span className="placar-numero placar-grande">{jogo.pts_b}</span>
          <span className="placar-sigla">{b.sigla}</span>
        </div>
      </div>

      <h2 className="manchete">{jogo.manchete}</h2>

      <table className="lideres">
        <caption className="rotulo">Game leaders</caption>
        <tbody>
          {ESTATISTICAS.map(([chave, nome]) => {
            const [la, lb] = jogo.lideres.map((l) => l[chave]);
            return (
              <tr key={chave}>
                <td className="lider-a">
                  {la.jogador} <b className="placar-numero">{la.valor}</b>
                </td>
                <th scope="row" title={nome}>
                  {chave}
                </th>
                <td className="lider-b">
                  <b className="placar-numero">{lb.valor}</b> {lb.jogador}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {jogo.destaques.length > 0 && (
        <ul className="destaques" aria-label="Standout performances">
          {jogo.destaques.map((d) => (
            <li key={d.texto}>
              <span aria-hidden="true">★</span> {d.texto}
            </li>
          ))}
        </ul>
      )}

      <button className="botao abrir-box" onClick={aoAbrirBox}>
        Full box score
      </button>
    </article>
  );
}
