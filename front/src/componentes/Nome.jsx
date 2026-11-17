import { createContext, useContext, useMemo } from "react";

// Nomes de times e jogadores ficam fora do tradutor automático do navegador (o Heat não vira "Calor").
export function Nome({ children }) {
  return <span translate="no">{children}</span>;
}

const ContextoNomes = createContext(null);

const escapar = (texto) => texto.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

// Junta os nomes da série (times, siglas e jogadores dos box scores) para achá-los nos textos da API.
export function NomesDaSerie({ serie, children }) {
  const padrao = useMemo(() => {
    const nomes = new Set();
    for (const time of [serie.time_a, serie.time_b]) nomes.add(time.nome).add(time.sigla);
    for (const jogo of serie.jogos) for (const linha of [...jogo.box_a, ...jogo.box_b]) nomes.add(linha.Jogador);
    const lista = [...nomes].filter(Boolean).sort((x, y) => y.length - x.length);
    return new RegExp(`(${lista.map(escapar).join("|")})`, "g");
  }, [serie]);
  return <ContextoNomes value={padrao}>{children}</ContextoNomes>;
}

// Texto livre da API (manchete, destaque, narração): traduz a frase, mas não os nomes dentro dela.
export function Texto({ children }) {
  const padrao = useContext(ContextoNomes);
  if (!padrao || typeof children !== "string") return children;
  return children.split(padrao).map((parte, i) => (i % 2 ? <Nome key={i}>{parte}</Nome> : parte));
}
