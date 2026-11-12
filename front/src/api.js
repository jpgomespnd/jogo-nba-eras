// Endereço da API; em produção vem da variável VITE_API_URL.
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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
