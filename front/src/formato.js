export const numero = (valor, casas = 0) =>
  valor.toLocaleString("en-US", { minimumFractionDigits: casas, maximumFractionDigits: casas });

export const porcento = (valor, casas = 0) => `${numero(100 * valor, casas)}%`;

export const comSinal = (valor, casas = 1) => `${valor > 0 ? "+" : ""}${numero(valor, casas)}`;

// "anos 90" -> "90": o valor de data-era que escolhe o tema.
export const temaDaEra = (era) => era.replace("anos ", "");

// Rótulo em inglês para exibir a era; o nome em português segue sendo o identificador da API.
const ROTULOS_DAS_ERAS = { "anos 90": "1990s", "anos 2000": "2000s", "anos 2010": "2010s", "anos 2020": "2020s" };
export const rotuloDaEra = (era) => ROTULOS_DAS_ERAS[era] ?? era;

export const campanha = (time) => `${time.vitorias}-${time.derrotas}`;
