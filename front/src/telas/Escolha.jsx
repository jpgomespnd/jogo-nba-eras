import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import CartaTime from "../componentes/CartaTime.jsx";
import { Aviso, Rodape, Topo } from "../componentes/Moldura.jsx";
import { numero, porcento, rotuloDaEra } from "../formato.js";

// Os times de cada temporada são pedidos uma vez só.
const timesPorTemporada = new Map();
function buscarTimes(temporada) {
  if (!timesPorTemporada.has(temporada)) {
    const pedido = api.times(temporada);
    pedido.catch(() => timesPorTemporada.delete(temporada));
    timesPorTemporada.set(temporada, pedido);
  }
  return timesPorTemporada.get(temporada);
}

const sortear = (lista) => lista[Math.floor(Math.random() * lista.length)];

export default function Escolha({ escolha, setEscolha, aoComecar, focarEra }) {
  const [temporadas, setTemporadas] = useState([]);
  const [eras, setEras] = useState([]);
  const [times, setTimes] = useState({});
  const [erro, setErro] = useState(null);
  const [tentativa, setTentativa] = useState(0);
  const secaoEras = useRef(null);

  useEffect(() => {
    Promise.all([api.temporadas(), api.eras()])
      .then(([t, e]) => {
        setTemporadas(t);
        setEras(e);
      })
      .catch((e) => setErro(e.message));
  }, [tentativa]);

  useEffect(() => {
    for (const temporada of [escolha.a.temporada, escolha.b.temporada]) {
      buscarTimes(temporada)
        .then((lista) => setTimes((atual) => ({ ...atual, [temporada]: lista })))
        .catch((e) => setErro(e.message));
    }
  }, [escolha.a.temporada, escolha.b.temporada, tentativa]);

  useEffect(() => {
    if (focarEra && eras.length) secaoEras.current?.scrollIntoView({ block: "center" });
  }, [focarEra, eras.length]);

  const timeDe = (lado) => times[escolha[lado].temporada]?.find((t) => t.id === escolha[lado].id);
  const timeA = timeDe("a");
  const timeB = timeDe("b");

  function trocarTemporada(lado, temporada) {
    buscarTimes(temporada).then((lista) => {
      const mesmo = lista.find((t) => t.id === escolha[lado].id);
      setEscolha((e) => ({ ...e, [lado]: { temporada, id: (mesmo ?? lista[0]).id } }));
    });
  }

  async function sortearTimes() {
    const sorteio = {};
    for (const lado of ["a", "b"]) {
      const temporada = sortear(temporadas);
      sorteio[lado] = { temporada, id: sortear(await buscarTimes(temporada)).id };
    }
    setEscolha((e) => ({ ...e, ...sorteio }));
  }

  if (erro || !temporadas.length) {
    return (
      <div className="tela">
        <Topo />
        <main className="conteudo">
          <Aviso erro={erro} aoTentar={() => {
            setErro(null);
            setTentativa((n) => n + 1);
          }}>
            Loading seasons and eras…
          </Aviso>
        </main>
      </div>
    );
  }

  const cartas = [
    ["a", "Team A", timeA],
    ["b", "Team B", timeB],
  ].map(([lado, rotulo, time]) => (
    <CartaTime
      key={lado}
      lado={lado}
      rotulo={rotulo}
      temporadas={temporadas}
      temporada={escolha[lado].temporada}
      times={times[escolha[lado].temporada]}
      time={time}
      aoTrocarTemporada={(t) => trocarTemporada(lado, t)}
      aoTrocarTime={(id) => setEscolha((e) => ({ ...e, [lado]: { ...e[lado], id } }))}
    />
  ));

  const opcoesDeMando = [
    ["a", timeA ? `${timeA.sigla} ${escolha.a.temporada}` : "Team A"],
    ["b", timeB ? `${timeB.sigla} ${escolha.b.temporada}` : "Team B"],
    ["neutro", "Neutral court"],
  ];

  return (
    <div className="tela">
      <Topo>
        <span className="topo-info">Best-of-7 series across eras</span>
      </Topo>
      <main className="conteudo escolha">
        <div className="duelo">
          {cartas[0]}
          <div className="versus" aria-hidden="true">
            vs
          </div>
          {cartas[1]}
        </div>

        <section className="eras" ref={secaoEras}>
          <h2 className="titulo-secao">Which era the series is played in</h2>
          <div className="eras-grade" role="radiogroup" aria-label="Era">
            {eras.map((era) => (
              <button
                key={era.nome}
                role="radio"
                aria-checked={escolha.era === era.nome}
                className="era"
                onClick={() => setEscolha((e) => ({ ...e, era: era.nome }))}
              >
                <span className="era-nome era-rotulo">{era.rotulo ?? rotuloDaEra(era.nome)}</span>
                <span className="era-numeros">
                  <span>
                    <b className="placar-numero">{numero(era.ritmo, 1)}</b> possessions per game
                  </span>
                  <span>
                    <b className="placar-numero">{porcento(era.volume_de_3)}</b> of shots are 3s
                  </span>
                </span>
                <span className="era-descricao">{era.descricao}</span>
              </button>
            ))}
          </div>
        </section>

        <div className="rodape-escolha">
          <fieldset className="mando">
            <legend className="titulo-secao">Home court</legend>
            <div className="mando-opcoes">
              {opcoesDeMando.map(([valor, texto]) => (
                <label key={valor} className="mando-opcao">
                  <input
                    type="radio"
                    name="mando"
                    value={valor}
                    checked={escolha.mando === valor}
                    onChange={() => setEscolha((e) => ({ ...e, mando: valor }))}
                  />
                  {texto}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="acoes">
            <button className="botao" onClick={sortearTimes}>
              Random teams
            </button>
            <button className="botao botao-principal" onClick={aoComecar} disabled={!timeA || !timeB}>
              Start the series
            </button>
          </div>
        </div>
      </main>
      <Rodape>Each team's odds are revealed only when the series ends.</Rodape>
    </div>
  );
}
