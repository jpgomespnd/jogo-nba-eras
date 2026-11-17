// Cores dos times por franquia (id da NBA) e por época: cada entrada vale a partir da temporada que começa
// naquele ano, até a próxima entrada. [ano, principal, secundária]. São aproximações das cores de cada fase,
// não as cores oficiais licenciadas.
const CORES = {
  1610612737: [[1990, "#e03a3e", "#fdb927"], [2007, "#c8102e", "#002b5c"], [2015, "#e03a3e", "#c1d32f"]], // Hawks
  1610612738: [[1990, "#007a33", "#ba9653"]], // Celtics
  1610612739: [[1990, "#e35205", "#002d72"], [1994, "#0072ce", "#e35205"], [2003, "#860038", "#fdbb30"]], // Cavaliers
  1610612740: [[2002, "#00778b", "#5b2b82"], [2008, "#002b5c", "#c4a36a"], [2013, "#0c2340", "#c8102e"]], // Hornets/Pelicans
  1610612741: [[1990, "#ce1141", "#000000"]], // Bulls
  1610612742: [[1990, "#0b6eb8", "#00a651"], [2001, "#00538c", "#b8c4ca"]], // Mavericks
  1610612743: [[1990, "#0e2240", "#fec524"], [1993, "#00285e", "#8b2131"], [2003, "#4d90cd", "#fdb927"], [2018, "#0e2240", "#fec524"]], // Nuggets
  1610612744: [[1990, "#0068b3", "#fdb927"], [1997, "#041e42", "#ff8200"], [2010, "#1d428a", "#ffc72c"]], // Warriors
  1610612745: [[1990, "#ce1141", "#fdb927"], [1995, "#002d62", "#ba0c2f"], [2003, "#ce1141", "#c4ced4"]], // Rockets
  1610612746: [[1990, "#c8102e", "#1d428a"]], // Clippers
  1610612747: [[1990, "#552583", "#fdb927"]], // Lakers
  1610612748: [[1990, "#98002e", "#f9a01b"]], // Heat
  1610612749: [[1990, "#00471b", "#ac1a2f"], [1993, "#4b2e83", "#00843d"], [2006, "#00471b", "#ac1a2f"], [2015, "#00471b", "#eee1c6"]], // Bucks
  1610612750: [[1990, "#005083", "#00a94f"], [2017, "#0c2340", "#78be20"]], // Timberwolves
  1610612751: [[1990, "#002a60", "#cd1041"], [2012, "#000000", "#ffffff"]], // Nets
  1610612752: [[1990, "#006bb6", "#f58426"]], // Knicks
  1610612753: [[1990, "#0077c0", "#000000"]], // Magic
  1610612754: [[1990, "#002d62", "#fdbb30"]], // Pacers
  1610612755: [[1990, "#006bb6", "#ed174c"], [1997, "#ba0c2f", "#000000"], [2009, "#006bb6", "#ed174c"]], // 76ers
  1610612756: [[1990, "#1d1160", "#e56020"]], // Suns
  1610612757: [[1990, "#e03a3e", "#000000"]], // Trail Blazers
  1610612758: [[1990, "#0055a4", "#e03a3e"], [1994, "#5a2d81", "#63727a"]], // Kings
  1610612759: [[1990, "#000000", "#c4ced4"]], // Spurs
  1610612760: [[1990, "#00653a", "#ffc200"], [2008, "#007ac1", "#ef3b24"]], // SuperSonics/Thunder
  1610612761: [[1995, "#753bbd", "#ba0c2f"], [2006, "#ce1141", "#000000"]], // Raptors
  1610612762: [[1990, "#5f259f", "#f9a01b"], [1996, "#3e2680", "#6cace4"], [2004, "#002b5c", "#f9a01b"]], // Jazz
  1610612763: [[1995, "#00b2a9", "#bc7844"], [2001, "#5d76a9", "#12173f"]], // Grizzlies
  1610612764: [[1990, "#002b5c", "#e31837"], [1997, "#002566", "#8c8279"], [2011, "#002b5c", "#e31837"]], // Bullets/Wizards
  1610612765: [[1990, "#c8102e", "#1d42ba"], [1996, "#007873", "#8c1d40"], [2001, "#c8102e", "#1d42ba"]], // Pistons
  1610612766: [[1990, "#00788c", "#1d1160"], [2004, "#f26532", "#0f586c"], [2014, "#1d1160", "#00788c"]], // Hornets/Bobcats
};

// Fundo de cada visual (data-era no <html>), para saber se a cor do time aparece sobre ele.
export const FUNDOS = {
  claro: "#f1ede4",
  escuro: "#0b0b0b",
  90: "#0a0f2c",
  2000: "#0e1330",
  2010: "#15181d",
  2020: "#101216",
};

const TINTA = "#0b0b0b";
const OSSO = "#f1ede4";
const LARANJA = "#ff5a1f";

function rgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function luminancia(hex) {
  const [r, g, b] = rgb(hex).map((c) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contraste(x, y) {
  const [claro, escuro] = [luminancia(x), luminancia(y)].sort((p, q) => q - p);
  return (claro + 0.05) / (escuro + 0.05);
}

function hsl(hex) {
  const [r, g, b] = rgb(hex).map((c) => c / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}

// Duas cores "iguais" para quem olha a tela: mesmo matiz, ou duas cores sem cor (preto, cinza) parecidas.
function parecidas(x, y) {
  const [h1, s1, l1] = hsl(x);
  const [h2, s2, l2] = hsl(y);
  if (Math.abs(l1 - l2) > 0.3) return false;
  // Quase branco, quase preto ou pouco saturado conta como cor neutra.
  const neutra = (sat, luz) => sat < 0.2 || luz > 0.88 || luz < 0.12;
  if (neutra(s1, l1) || neutra(s2, l2)) return neutra(s1, l1) && neutra(s2, l2);
  const dh = Math.min(Math.abs(h1 - h2), 360 - Math.abs(h1 - h2));
  return dh < 30;
}

export function coresDoTime(id, temporada) {
  const ano = Number(String(temporada).slice(0, 4));
  const fases = CORES[id];
  if (!fases) return null;
  let fase = fases[0];
  for (const f of fases) if (f[0] <= ano) fase = f;
  return { principal: fase[1], secundaria: fase[2] };
}

const sobre = (cor) => (contraste(cor, TINTA) >= contraste(cor, "#ffffff") ? TINTA : "#ffffff");

// Cor que representa cada time na tela (led, faixas, barras): a principal, a secundária se a principal
// sumir no fundo, e o time B troca de cor se ficar parecido com o A: tenta a outra cor dele, depois a cor
// do texto e, por último, o laranja da marca.
export function coresDoConfronto(a, b, tema) {
  const fundo = FUNDOS[tema] ?? FUNDOS.claro;
  const texto = contraste(fundo, TINTA) > contraste(fundo, OSSO) ? TINTA : OSSO;
  const visivel = (cor) => contraste(cor, fundo) >= 2.2;
  const opcoes = (cores) => (cores ? [cores.principal, cores.secundaria].filter(visivel) : []);

  const ca = a ? coresDoTime(a.id, a.temporada) : null;
  const cb = b ? coresDoTime(b.id, b.temporada) : null;
  const corA = opcoes(ca)[0] ?? texto;
  const corB = [...opcoes(cb), texto, LARANJA].find((c) => !parecidas(c, corA)) ?? texto;

  const estilo = {};
  for (const [lado, cor, cores] of [
    ["a", corA, ca],
    ["b", corB, cb],
  ]) {
    estilo[`--cor-${lado}`] = cor;
    estilo[`--sobre-${lado}`] = sobre(cor);
    // "Camisa": o quadrado da sigla, com a principal no fundo e a secundária nas letras.
    const camisa = cores?.principal ?? cor;
    const letras = cores && contraste(cores.secundaria, camisa) >= 2.5 ? cores.secundaria : sobre(camisa);
    estilo[`--camisa-${lado}`] = camisa;
    estilo[`--camisa-texto-${lado}`] = letras;
  }
  return estilo;
}
