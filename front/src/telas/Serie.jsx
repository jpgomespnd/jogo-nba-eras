import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import BoxScore from "../componentes/BoxScore.jsx";
import CartaoJogo from "../componentes/CartaoJogo.jsx";
import FinalNarrado, { EscolhaDoFinal } from "../componentes/FinalNarrado.jsx";
import MiniCartoes from "../componentes/MiniCartoes.jsx";
import { Aviso, Rodape, Topo } from "../componentes/Moldura.jsx";

const PAUSA_DO_AUTOMATICO = 2200;

export default function Serie({ pedido, aoTerminar, aoNovaSerie, aoTrocarTimes }) {
  const [serie, setSerie] = useState(null);
  const [erro, setErro] = useState(null);
  const [tentativa, setTentativa] = useState(0);
  const [revelados, setRevelados] = useState(0);
  const [atual, setAtual] = useState(0);
  // Final em aberto: { indice, modo: "escolher" | "narrar" }.
  const [final, setFinal] = useState(null);
  const [automatico, setAutomatico] = useState(false);
  // Índice do jogo com o box score aberto no pop-up.
  const [box, setBox] = useState(null);

  // Uma série nova (outra semente) remonta a tela pelo key no App, então o estado já começa zerado.
  const chave = JSON.stringify(pedido);
  useEffect(() => {
    let valido = true;
    api
      .serie(JSON.parse(chave))
      .then((s) => valido && setSerie(s))
      .catch((e) => valido && setErro(e.message));
    return () => {
      valido = false;
    };
  }, [chave, tentativa]);

  const total = serie?.jogos.length ?? 0;
  const terminou = serie && revelados === total;
  const rodando = automatico && !terminou;

  const mostrar = useCallback((indice) => {
    setFinal(null);
    setRevelados(indice + 1);
    setAtual(indice);
  }, []);

  const avancar = useCallback(
    (direto) => {
      const jogo = serie.jogos[revelados];
      if (!direto && jogo.inicio_do_final !== null) setFinal({ indice: revelados, modo: "escolher" });
      else mostrar(revelados);
    },
    [serie, revelados, mostrar],
  );

  // No automático os finais apertados são simulados direto, sem pop-up.
  useEffect(() => {
    if (!rodando) return;
    const passo = setTimeout(() => avancar(true), revelados === 0 ? 0 : PAUSA_DO_AUTOMATICO);
    return () => clearTimeout(passo);
  }, [rodando, revelados, avancar]);

  const terminarFinal = useCallback(() => mostrar(final.indice), [final, mostrar]);

  if (!serie) {
    return (
      <div className="tela">
        <Topo />
        <main className="conteudo">
          <Aviso
            erro={erro}
            aoTentar={() => {
              setErro(null);
              setTentativa((n) => n + 1);
            }}
          >
            Montando a série nos {pedido.era}…
          </Aviso>
        </main>
      </div>
    );
  }

  const { time_a: a, time_b: b } = serie;
  const ultimo = serie.jogos[revelados - 1];
  const vitorias = { a: ultimo?.vitorias_a ?? 0, b: ultimo?.vitorias_b ?? 0 };
  const narrando = final?.modo === "narrar";
  let situacao = "Série empatada em 0-0";
  if (terminou) situacao = `${vitorias.a > vitorias.b ? a.sigla : b.sigla} vence a série por 4-${Math.min(vitorias.a, vitorias.b)}`;
  else if (vitorias.a !== vitorias.b)
    situacao = `${vitorias.a > vitorias.b ? a.sigla : b.sigla} lidera por ${Math.max(vitorias.a, vitorias.b)}-${Math.min(vitorias.a, vitorias.b)}`;
  else if (revelados) situacao = `Série empatada em ${vitorias.a}-${vitorias.b}`;

  let palco;
  if (narrando) palco = <FinalNarrado key={final.indice} jogo={serie.jogos[final.indice]} serie={serie} aoTerminar={terminarFinal} />;
  else if (revelados) palco = (
      <CartaoJogo key={atual} jogo={serie.jogos[atual]} serie={serie} aoAbrirBox={() => setBox(atual)} />
    );
  else
    palco = (
      <div className="cartao-jogo cartao-vazio">
        <p className="manchete">
          {a.nome} {a.temporada} x {b.nome} {b.temporada}
        </p>
        <p>
          Sete jogos no máximo, jogados no ambiente dos {serie.era}. A série só começa quando você mandar.
        </p>
      </div>
    );

  return (
    <div className="tela">
      <Topo>
        <span className="topo-info">
          {a.sigla} {a.temporada} x {b.sigla} {b.temporada} · {serie.era}
        </span>
        <button className="botao botao-discreto" onClick={aoTrocarTimes}>
          Trocar times
        </button>
      </Topo>

      <main className="conteudo serie">
        <div className="placar-serie" aria-live="polite">
          <span className="placar-serie-time lado-a">{a.sigla}</span>
          <span className="placar-numero placar-serie-numero">
            {vitorias.a}-{vitorias.b}
          </span>
          <span className="placar-serie-time lado-b">{b.sigla}</span>
          <span className="placar-serie-situacao">{situacao}</span>
        </div>

        <MiniCartoes
          serie={serie}
          revelados={revelados}
          atual={narrando ? -1 : atual}
          aoVivo={narrando ? final.indice : -1}
          aoEscolher={(i) => {
            setAtual(i);
            setBox(i);
          }}
        />

        <div className="serie-corpo">
          {palco}
          <aside className="controles" aria-label="Controles da série">
            {terminou ? (
              <button className="botao botao-principal" onClick={() => aoTerminar(serie)}>
                Revelar as chances
              </button>
            ) : (
              <>
                <button className="botao botao-principal" onClick={() => avancar(false)} disabled={automatico || !!final}>
                  {revelados ? "Próximo jogo" : "Começar a série"}
                </button>
                <button className="botao" onClick={() => setAutomatico((v) => !v)} disabled={!!final} aria-pressed={automatico}>
                  {automatico ? "Parar o automático" : "Avançar sozinho"}
                </button>
                <button className="botao" onClick={() => mostrar(total - 1)} disabled={narrando}>
                  Pular para o fim da série
                </button>
              </>
            )}
            <button className="botao" onClick={aoNovaSerie}>
              Jogar de novo
            </button>
          </aside>
        </div>
      </main>

      {box !== null && <BoxScore key={box} jogo={serie.jogos[box]} serie={serie} aoFechar={() => setBox(null)} />}

      {final?.modo === "escolher" && (
        <EscolhaDoFinal
          jogo={serie.jogos[final.indice]}
          serie={serie}
          aoAcompanhar={() => setFinal({ ...final, modo: "narrar" })}
          aoSimular={terminarFinal}
        />
      )}

      <Rodape>Uma das séries possíveis; outra semente traz outra série.</Rodape>
    </div>
  );
}
