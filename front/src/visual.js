import { createContext } from "react";

// Visual da interface: "era" veste a era escolhida; "escuro" e "claro" deixam tudo neutro.
export const VISUAIS = [
  ["era", "Era style"],
  ["escuro", "Dark"],
  ["claro", "Light"],
];

const CHAVE = "jogo-nba-eras:visual";

export function visualSalvo() {
  try {
    const salvo = localStorage.getItem(CHAVE);
    return VISUAIS.some(([v]) => v === salvo) ? salvo : "era";
  } catch {
    return "era";
  }
}

export function salvarVisual(visual) {
  try {
    localStorage.setItem(CHAVE, visual);
  } catch {
    // Sem armazenamento (aba anônima, por exemplo): a escolha vale só nesta visita.
  }
}

export const ContextoVisual = createContext({ visual: "era", setVisual: () => {} });
