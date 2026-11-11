// Topo, rodapé e avisos que se repetem nas três telas.

export function Topo({ children }) {
  return (
    <header className="topo">
      <div className="marca">
        <span className="ao-vivo">AO VIVO</span>
        <span>jogo-nba-eras</span>
      </div>
      {children}
    </header>
  );
}

export function Rodape({ children }) {
  return (
    <footer className="rodape">
      {children} Projeto não oficial, sem vínculo com a NBA.
    </footer>
  );
}

export function Aviso({ erro, aoTentar, children }) {
  if (erro) {
    return (
      <div className="aviso" role="alert">
        <p>
          A API não respondeu ({erro}). Confira se ela está ligada com{" "}
          <code>.venv\Scripts\uvicorn --app-dir scripts api:app --reload</code> e tente de novo.
        </p>
        {aoTentar && (
          <button className="botao" onClick={aoTentar}>
            Tentar de novo
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
