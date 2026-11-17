import { createContext, useContext, useMemo } from "react";
import { coresDoConfronto } from "./cores.js";

// Visual da interface: "claro" e "escuro" são a identidade What If Hoops; "era" veste a era escolhida.
export const VISUAIS = [
  ["claro", "Light"],
  ["escuro", "Dark"],
  ["era", "Era style"],
];

const PADRAO = "claro";

const CHAVE = "jogo-nba-eras:visual";

export function visualSalvo() {
  try {
    const salvo = localStorage.getItem(CHAVE);
    return VISUAIS.some(([v]) => v === salvo) ? salvo : PADRAO;
  } catch {
    return PADRAO;
  }
}

export function salvarVisual(visual) {
  try {
    localStorage.setItem(CHAVE, visual);
  } catch {
    // Sem armazenamento (aba anônima, por exemplo): a escolha vale só nesta visita.
  }
}

export const ContextoVisual = createContext({ visual: PADRAO, tema: PADRAO, setVisual: () => {} });

// Variáveis CSS com as cores dos dois times (--cor-a, --camisa-a...) para o visual em uso.
// a e b precisam de { id, temporada }; enquanto um time carrega, ele fica na cor do texto.
export function useCoresDosTimes(a, b) {
  const { tema } = useContext(ContextoVisual);
  const idA = a?.id;
  const idB = b?.id;
  const tA = a?.temporada;
  const tB = b?.temporada;
  return useMemo(
    () => coresDoConfronto(idA && { id: idA, temporada: tA }, idB && { id: idB, temporada: tB }, tema),
    [idA, tA, idB, tB, tema],
  );
}
