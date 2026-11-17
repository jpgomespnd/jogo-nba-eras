// Proteção contra o tradutor automático do navegador (Chrome, Edge).
// O tradutor troca os nós de texto da página por <font> com o texto traduzido. Quando o React depois tenta
// remover ou usar como referência um desses nós antigos, o navegador lança NotFoundError e a página fica em
// branco (https://github.com/facebook/react/issues/11538). Aqui o nó que não está mais no lugar é ignorado
// na remoção e, na inserção, o novo nó vai para o fim do pai em vez de derrubar o site.
export function protegerDoTradutor() {
  if (typeof Node !== "function" || Node.prototype.__protegidoDoTradutor) return;
  Node.prototype.__protegidoDoTradutor = true;

  const removeChild = Node.prototype.removeChild;
  Node.prototype.removeChild = function (filho) {
    if (filho.parentNode !== this) return filho;
    return removeChild.call(this, filho);
  };

  const insertBefore = Node.prototype.insertBefore;
  Node.prototype.insertBefore = function (novo, referencia) {
    if (referencia && referencia.parentNode !== this) return insertBefore.call(this, novo, null);
    return insertBefore.call(this, novo, referencia);
  };
}
