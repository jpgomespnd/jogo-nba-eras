import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import CartaTime from "../componentes/CartaTime.jsx";
import { Nome } from "../componentes/Nome.jsx";
import { Aviso, Rodape, Topo } from "../componentes/Moldura.jsx";
import { numero, porcento, rotuloDaEra } from "../formato.js";
import { useCoresDosTimes } from "../visual.js";

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
  const cores = useCoresDosTimes(timeA && { id: timeA.id, temporada: escolha.a.temporada }, timeB && { id: timeB.id, temporada: escolha.b.temporada });

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

  const indiceDaEra = eras.findIndex((e) => e.nome === escolha.era);
  const eraAtual = eras[indiceDaEra];
  const escolherEra = (nome) => setEscolha((e) => ({ ...e, era: nome }));

  // Setas trocam de era dentro do grupo, como em qualquer grupo de opções.
  function andarComSetas(evento) {
    const passo = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[evento.key];
    if (!passo) return;
    evento.preventDefault();
    const proxima = (indiceDaEra + passo + eras.length) % eras.length;
    escolherEra(eras[proxima].nome);
    evento.currentTarget.querySelectorAll("button")[proxima].focus();
  }

  const opcoesDeMando = [
    ["a", timeA ? <><Nome>{timeA.sigla}</Nome> {escolha.a.temporada}</> : "Team A"],
    ["b", timeB ? <><Nome>{timeB.sigla}</Nome> {escolha.b.temporada}</> : "Team B"],
    ["neutro", "Neutral court"],
  ];

  return (
    <div className="tela" style={cores}>
      <Topo>
        <span className="topo-info">Best-of-7 series across eras</span>
      </Topo>
      <main className="conteudo escolha">
        <section className="era-heroi" ref={secaoEras} aria-labelledby="titulo-era">
          <h1 className="chamada-titulo">The series that never happened.</h1>
          <p className="era-heroi-kicker" id="titulo-era">
            Pick the era the series is played in
          </p>
          <p className="era-heroi-nome era-rotulo" aria-live="polite">
            {rotuloDaEra(escolha.era)}
          </p>
          {eraAtual && (
            <>
              <p className="era-heroi-descricao">{eraAtual.descricao}</p>
              <ul className="era-heroi-chips">
                <li>
                  <b className="placar-numero">{numero(eraAtual.ritmo, 1)}</b> possessions per game
                </li>
                <li>
                  <b className="placar-numero">{porcento(eraAtual.volume_de_3)}</b> of shots are 3s
                </li>
              </ul>
            </>
          )}
          <div
            className="seletor-eras"
            role="radiogroup"
            aria-labelledby="titulo-era"
            style={{ "--indice": Math.max(0, indiceDaEra), "--quantas": eras.length }}
            onKeyDown={andarComSetas}
          >
            {eras.map((era) => (
              <button
                key={era.nome}
                role="radio"
                aria-checked={escolha.era === era.nome}
                tabIndex={escolha.era === era.nome ? 0 : -1}
                className="seletor-era era-rotulo"
                onClick={() => escolherEra(era.nome)}
              >
                {era.rotulo}
              </button>
            ))}
            <span className="seletor-led" aria-hidden="true" />
          </div>
        </section>

        <div className="duelo">
          {cartas[0]}
          <div className="versus" aria-hidden="true">
            <span>vs</span>
            <small>Best of 7</small>
          </div>
          {cartas[1]}
        </div>

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
