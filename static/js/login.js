const form = document.getElementById('login-form');
const mensagem = document.getElementById('mensagem-usuario');
const loading = document.getElementById('loading');

loading.style.display = 'none';

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  mensagem.style.display = 'none';
  mensagem.textContent = '';
  mensagem.className = '';
  loading.style.display = 'block';

  const formData = new URLSearchParams();
  formData.append('username', form.username.value.trim());
  formData.append('password', form.password.value);

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // timeout de 15s

    const response = await fetch('/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
      signal: controller.signal
    });

    clearTimeout(timeoutId);
    loading.style.display = 'none';

    if (!response.ok) {
      let errorMsg = 'Erro desconhecido';
      try {
        const errorJson = await response.json();
        errorMsg = errorJson.detail || errorMsg;
      } catch {}
      mensagem.textContent = errorMsg;
      mensagem.className = 'erro';
      mensagem.style.display = 'block';
      return;
    }

    // Sucesso: sempre direciona para /choose
    window.location.href = '/choose';

  } catch (err) {
    loading.style.display = 'none';
    if (err.name === 'AbortError') {
      mensagem.textContent = 'Tempo de conexão esgotado. Tente novamente.';
    } else {
      mensagem.textContent = 'Erro ao conectar com o servidor.';
    }
    mensagem.className = 'erro';
    mensagem.style.display = 'block';
  }
});

async function logout() {
  try {
    await fetch('/logout', { method: 'POST' });
  } catch {}
  window.location.href = '/';
}
