import { useEffect, useState } from "react";

// Endereço da API; em produção vem da variável VITE_API_URL. Sem ela, a API é procurada na porta 8000 da mesma
// máquina que serviu o site (localhost no computador, o IP do computador quando aberto no celular).
const BASE = import.meta.env.VITE_API_URL ?? `${location.protocol}//${location.hostname}:8000`;

async function pedir(caminho, opcoes) {
  const resposta = await fetch(`${BASE}${caminho}`, opcoes);
  const corpo = await resposta.json();
  if (!resposta.ok) {
    const detalhe = typeof corpo.detail === "string" ? corpo.detail : "Invalid request";
    throw new Error(detalhe);
  }
  return corpo;
}

function postar(caminho, dados) {
  return pedir(caminho, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
}

export const api = {
  temporadas: () => pedir("/temporadas"),
  times: (temporada) => pedir(`/times?temporada=${encodeURIComponent(temporada)}`),
  eras: () => pedir("/eras"),
  serie: (pedido) => postar("/serie", pedido),
  revelar: (pedido) => postar("/revelar", pedido),
};

// Faz um pedido à API e guarda a resposta ou o erro. chave é o pedido em JSON; tentarDeNovo refaz o pedido.
// A resposta de um pedido que ficou para trás (a tela mudou antes de ela chegar) é descartada.
export function usePedido(pedir, chave) {
  const [estado, setEstado] = useState({ dados: null, erro: null });
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let valido = true;
    pedir(JSON.parse(chave))
      .then((dados) => valido && setEstado({ dados, erro: null }))
      .catch((e) => valido && setEstado({ dados: null, erro: e.message }));
    return () => {
      valido = false;
    };
  }, [pedir, chave, tentativa]);

  function tentarDeNovo() {
    setEstado({ dados: null, erro: null });
    setTentativa((n) => n + 1);
  }

  return { ...estado, tentarDeNovo };
}
