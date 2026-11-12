import { useEffect, useState } from "react";
import { temaDaEra } from "./formato.js";
import Escolha from "./telas/Escolha.jsx";
import Revelacao from "./telas/Revelacao.jsx";
import Serie from "./telas/Serie.jsx";
import { ContextoVisual, salvarVisual, visualSalvo } from "./visual.js";

const ESCOLHA_INICIAL = {
  a: { temporada: "2009-10", id: 1610612747 },
  b: { temporada: "2016-17", id: 1610612744 },
  era: "anos 90",
  mando: "a",
};

export default function App() {
  const [tela, setTela] = useState("escolha");
  const [escolha, setEscolha] = useState(ESCOLHA_INICIAL);
  const [semente, setSemente] = useState(0);
  const [serie, setSerie] = useState(null);
  const [focarEra, setFocarEra] = useState(false);
  const [visual, setVisual] = useState(visualSalvo);

  // A interface veste a era escolhida, já na tela de escolha, a não ser que o visual seja escuro ou claro.
  useEffect(() => {
    document.documentElement.dataset.era = visual === "era" ? temaDaEra(escolha.era) : visual;
    salvarVisual(visual);
  }, [visual, escolha.era]);

  function irPara(proxima, era = false) {
    setFocarEra(era);
    setTela(proxima);
    window.scrollTo(0, 0);
  }

  function novaSerie() {
    setSemente((s) => s + 1);
    irPara("serie");
  }

  const confronto = {
    temporada_a: escolha.a.temporada,
    time_a: escolha.a.id,
    temporada_b: escolha.b.temporada,
    time_b: escolha.b.id,
    era: escolha.era,
    mando: escolha.mando,
  };

  let pagina;
  if (tela === "serie") {
    pagina = (
      <Serie
        key={semente}
        pedido={{ ...confronto, semente }}
        aoTerminar={(s) => {
          setSerie(s);
          irPara("revelacao");
        }}
        aoNovaSerie={novaSerie}
        aoTrocarTimes={() => irPara("escolha")}
      />
    );
  } else if (tela === "revelacao") {
    pagina = (
      <Revelacao
        confronto={confronto}
        serie={serie}
        aoNovaSerie={novaSerie}
        aoOutraEra={() => irPara("escolha", true)}
        aoTrocarTimes={() => irPara("escolha")}
      />
    );
  } else {
    pagina = <Escolha escolha={escolha} setEscolha={setEscolha} focarEra={focarEra} aoComecar={() => irPara("serie")} />;
  }

  return <ContextoVisual value={{ visual, setVisual }}>{pagina}</ContextoVisual>;
}
