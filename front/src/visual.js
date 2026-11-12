import { createContext } from "react";

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

export const ContextoVisual = createContext({ visual: PADRAO, setVisual: () => {} });
