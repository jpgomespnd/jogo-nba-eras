// Símbolo da marca: um ponto de interrogação cujo ponto é a bola.
// O traço usa a cor do texto (currentColor); a bola é sempre laranja.
export function Simbolo({ className }) {
  return (
    <svg className={className} viewBox="0 0 64 104" aria-hidden="true" focusable="false">
      <path
        d="M9 32 A23 23 0 1 1 41 53 C35 56 32 60 32 67 V72"
        fill="none"
        stroke="currentColor"
        strokeWidth="12"
        strokeLinecap="butt"
      />
      <g transform="translate(32 89)">
        <circle r="14" fill="#ff5a1f" />
        <path
          d="M-14 0 H14 M0 -14 V14 M-9 -10.5 Q-3 0 -9 10.5 M9 -10.5 Q3 0 9 10.5"
          fill="none"
          stroke="#0b0b0b"
          strokeWidth="2"
        />
      </g>
    </svg>
  );
}

export default function Logo() {
  return (
    <span className="logo" role="img" aria-label="What If Hoops">
      <Simbolo className="logo-simbolo" />
      <span className="logo-palavras" aria-hidden="true">
        <span>What if</span>
        <span className="logo-hoops">Hoops</span>
      </span>
    </span>
  );
}
