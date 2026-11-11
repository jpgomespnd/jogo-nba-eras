export const numero = (valor, casas = 0) =>
  valor.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

export const porcento = (valor, casas = 0) => `${numero(100 * valor, casas)}%`;

export const comSinal = (valor, casas = 1) => `${valor > 0 ? "+" : ""}${numero(valor, casas)}`;

// "anos 90" -> "90": o valor de data-era que escolhe o tema.
export const temaDaEra = (era) => era.replace("anos ", "");

export const campanha = (time) => `${time.vitorias}-${time.derrotas}`;
