import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./temas.css";
import "./index.css";
import App from "./App.jsx";
import { protegerDoTradutor } from "./tradutor.js";

protegerDoTradutor();

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
