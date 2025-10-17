document.addEventListener('DOMContentLoaded', () => {
  // ----------------- Elementos -----------------
  const form = document.getElementById('form');
  const inputProduto = document.getElementById('id_produto');
  const autocompleteList = document.getElementById('autocomplete-list');
  const mensagemEl = document.getElementById('mensagem-usuario');
  const loadingEl = document.getElementById('loading');
  const inputFile = document.getElementById('file');
  const fileNameEl = document.getElementById('file-name');
  const fileRemoveBtn = document.getElementById('file-remove');

  if (!form || !inputProduto || !autocompleteList || !mensagemEl || !loadingEl || !inputFile || !fileNameEl) {
    console.error("Algum elemento obrigatório não foi encontrado no DOM");
    return;
  }

  // ----------------- Variáveis -----------------
  let produtos = [];
  let selectedId = null;
  let currentFocus = -1;

  // ----------------- Carregar produtos -----------------
  async function carregarProdutos() {
    try {
      const res = await fetch('/api/produtos');
      const data = await res.json();
      if (Array.isArray(data)) {
        produtos = data; // cada item: {id, text}
      } else {
        console.error("Resposta inesperada do backend:", data);
      }
    } catch (err) {
      console.error("Erro ao carregar produtos:", err);
    }
  }
  carregarProdutos();

  // ----------------- Input de arquivo -----------------
  inputFile.addEventListener('change', () => {
    if (inputFile.files.length > 0) {
      fileNameEl.textContent = inputFile.files[0].name;
    } else {
      fileNameEl.textContent = "Nenhum arquivo escolhido";
    }
  });

  // ----------------- Autocomplete -----------------
  function mostrarLista(filtrados) {
    autocompleteList.innerHTML = '';
    filtrados.forEach((p) => {
      const li = document.createElement('li');
      li.textContent = p.text;
      li.dataset.id = p.id;
      li.addEventListener('click', () => {
        inputProduto.value = p.text;
        selectedId = p.id;
        autocompleteList.innerHTML = '';
      });
      autocompleteList.appendChild(li);
    });
    currentFocus = -1;
  }

  inputProduto.addEventListener('input', () => {
    const valor = inputProduto.value.toLowerCase();
    if (!valor) {
      mostrarLista(produtos);
      return;
    }
    const filtrados = produtos.filter(p =>
      p.text.toLowerCase().includes(valor) || p.id.toString().includes(valor)
    );
    mostrarLista(filtrados);
  });

  inputProduto.addEventListener('focus', () => {
    mostrarLista(produtos);
  });

  inputProduto.addEventListener('keydown', (e) => {
    const items = autocompleteList.getElementsByTagName('li');
    if (!items) return;

    if (e.key === 'ArrowDown') {
      currentFocus++;
      adicionarClasse(items);
    } else if (e.key === 'ArrowUp') {
      currentFocus--;
      adicionarClasse(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (currentFocus > -1) {
        items[currentFocus].click();
      }
    }
  });

  function adicionarClasse(items) {
    if (!items) return false;
    Array.from(items).forEach(item => item.classList.remove('autocomplete-active'));
    if (currentFocus >= items.length) currentFocus = 0;
    if (currentFocus < 0) currentFocus = items.length - 1;
    items[currentFocus].classList.add('autocomplete-active');
  }

  document.addEventListener('click', (e) => {
    if (e.target !== inputProduto) {
      autocompleteList.innerHTML = '';
    }
  });

  // ----------------- Submit -----------------
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    fd.set('id_produto', selectedId);

    mensagemEl.style.display = 'none';
    loadingEl.style.display = 'block';

    try {
      const res = await fetch('/patrimonio/upload', { method: 'POST', body: fd });
      const data = await res.json();
      loadingEl.style.display = 'none';

      if (data.status === "erro" || (data.processados && data.processados.some(r => !r.sucesso))) {
        const erro = data.detalhes ? data.detalhes[0].mensagem : "Ocorreu um erro no upload";
        mensagemEl.className = 'erro';
        mensagemEl.style.display = 'block';
        mensagemEl.textContent = `❌ Erro: ${erro}`;
      } else {
        mensagemEl.className = 'sucesso';
        mensagemEl.style.display = 'block';
        mensagemEl.textContent = "✅ Upload concluído com sucesso!";
      }
    } catch (err) {
      loadingEl.style.display = 'none';
      mensagemEl.className = 'erro';
      mensagemEl.style.display = 'block';
      mensagemEl.textContent = "❌ Erro na comunicação com o servidor";
    }
  });

  inputFile.addEventListener('change', () => {
  if (inputFile.files.length > 0) {
    fileNameEl.textContent = inputFile.files[0].name;
    fileRemoveBtn.style.display = 'inline-block'; // mostra botão remover
  } else {
    fileNameEl.textContent = "Nenhum arquivo escolhido";
    fileRemoveBtn.style.display = 'none';
  }
});

fileRemoveBtn.addEventListener('click', () => {
  inputFile.value = "";                  // limpa o input
  fileNameEl.textContent = "Nenhum arquivo escolhido"; // reseta texto
  fileRemoveBtn.style.display = 'none';  // esconde botão
});
});
