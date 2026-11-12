import { useContext } from "react";
import { ContextoVisual, VISUAIS } from "../visual.js";
import Logo from "./Logo.jsx";

// Topo, rodapé e avisos que se repetem nas três telas.

function SeletorVisual() {
  const { visual, setVisual } = useContext(ContextoVisual);
  return (
    <div className="seletor-visual" role="radiogroup" aria-label="Appearance">
      {VISUAIS.map(([valor, texto]) => (
        <button key={valor} role="radio" aria-checked={visual === valor} onClick={() => setVisual(valor)}>
          {texto}
        </button>
      ))}
    </div>
  );
}

export function Topo({ children }) {
  return (
    <header className="topo">
      <div className="marca">
        <Logo />
        <span className="ao-vivo">LIVE</span>
      </div>
      {children}
      <SeletorVisual />
    </header>
  );
}

export function Rodape({ children }) {
  return (
    <footer className="rodape">
      <p>{children}</p>
      <p className="rodape-marca">
        <span className="rodape-slogan">Any team. Any era. Best of 7.</span> What If Hoops is an unofficial project, not
        affiliated with the NBA.
      </p>
    </footer>
  );
}

export function Aviso({ erro, aoTentar, children }) {
  if (erro) {
    return (
      <div className="aviso" role="alert">
        <p>
          The API didn't respond ({erro}). Make sure it is running with{" "}
          <code>.venv\Scripts\uvicorn --app-dir scripts api:app --reload</code> and try again.
        </p>
        {aoTentar && (
          <button className="botao" onClick={aoTentar}>
            Try again
          </button>
        )}
      </div>
    );
  }
  return (
    <div className="aviso carregando" role="status">
      {children}
    </div>
  );
}
