import { campanha, comSinal, numero } from "../formato.js";

export default function CartaTime({ lado, rotulo, temporadas, temporada, times, time, aoTrocarTemporada, aoTrocarTime }) {
  return (
    <section className={`carta-time lado-${lado}`} aria-label={rotulo}>
      <div className="carta-controles">
        <label>
          Season
          <select value={temporada} onChange={(e) => aoTrocarTemporada(e.target.value)}>
            {temporadas.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        <label>
          Team
          <select translate="no" value={time?.id ?? ""} onChange={(e) => aoTrocarTime(Number(e.target.value))} disabled={!times}>
            {(times ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.campeao ? `${t.nome} 🏆` : t.nome}
              </option>
            ))}
          </select>
        </label>
      </div>

      {time ? (
        <>
          <div className="carta-cabeca">
            <div className="sigla" aria-hidden="true" translate="no">
              {time.sigla}
            </div>
            <div>
              <h2 className="carta-nome" translate="no">
                <span className="led aceso">{time.nome}</span>
              </h2>
              <p className="carta-campanha">
                <span className="placar-numero">{campanha(time)}</span> in {temporada}, {comSinal(time.saldo)} point
                differential
              </p>
              {time.campeao && <p className="selo-campeao">{temporada} Champions</p>}
            </div>
          </div>
          <ul className="selos" aria-label="Playing style">
            {time.selos.length ? (
              time.selos.map((s) => <li key={s}>{s}</li>)
            ) : (
              <li className="selo-vazio">No standout traits</li>
            )}
          </ul>
          <p className="rotulo">Top scorers, points per game</p>
          <ol className="cestinhas">
            {time.destaques.map((d) => (
              <li key={d.jogador}>
                <span translate="no">{d.jogador}</span>
                <span className="placar-numero">{numero(d.pontos_por_jogo, 1)}</span>
              </li>
            ))}
          </ol>
        </>
      ) : (
        <div className="carta-vazia">Loading {temporada} teams…</div>
      )}
    </section>
  );
}
