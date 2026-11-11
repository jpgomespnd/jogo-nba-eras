import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import CartaTime from "../componentes/CartaTime.jsx";
import { Aviso, Rodape, Topo } from "../componentes/Moldura.jsx";
import { numero, porcento } from "../formato.js";

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
            Buscando temporadas e eras…
          </Aviso>
        </main>
      </div>
    );
  }

  const cartas = [
    ["a", "Time A", timeA],
    ["b", "Time B", timeB],
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
    ["a", timeA ? `${timeA.sigla} ${escolha.a.temporada}` : "Time A"],
    ["b", timeB ? `${timeB.sigla} ${escolha.b.temporada}` : "Time B"],
    ["neutro", "Quadra neutra"],
  ];

  return (
    <div className="tela">
      <Topo>
        <span className="topo-info">Série melhor de 7 entre épocas</span>
      </Topo>
      <main className="conteudo escolha">
        <div className="duelo">
          {cartas[0]}
          <div className="versus" aria-hidden="true">
            x
          </div>
          {cartas[1]}
        </div>

        <section className="eras" ref={secaoEras}>
          <h2 className="titulo-secao">Em que era a série é jogada</h2>
          <div className="eras-grade" role="radiogroup" aria-label="Era">
            {eras.map((era) => (
              <button
                key={era.nome}
                role="radio"
                aria-checked={escolha.era === era.nome}
                className="era"
                onClick={() => setEscolha((e) => ({ ...e, era: era.nome }))}
              >
                <span className="era-nome">{era.nome}</span>
                <span className="era-numeros">
                  <span>
                    <b className="placar-numero">{numero(era.ritmo, 1)}</b> posses por jogo
                  </span>
                  <span>
                    <b className="placar-numero">{porcento(era.volume_de_3)}</b> dos arremessos de 3
                  </span>
                </span>
                <span className="era-descricao">{era.descricao}</span>
              </button>
            ))}
          </div>
        </section>

        <div className="rodape-escolha">
          <fieldset className="mando">
            <legend className="titulo-secao">Mando de quadra</legend>
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
              Sortear times
            </button>
            <button className="botao botao-principal" onClick={aoComecar} disabled={!timeA || !timeB}>
              Começar a série
            </button>
          </div>
        </div>
      </main>
      <Rodape>As chances de cada time só aparecem quando a série termina.</Rodape>
    </div>
  );
}
