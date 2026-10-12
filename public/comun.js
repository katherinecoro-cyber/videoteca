// Funciones compartidas por las páginas de la videoteca.

function escaparHTML(texto) {
  const div = document.createElement('div');
  div.textContent = texto ?? '';
  return div.innerHTML;
}

function htmlMiniatura(video) {
  if (video.miniatura) {
    return `<div class="miniatura"><img src="/media/${encodeURIComponent(video.miniatura)}" alt="" loading="lazy"></div>`;
  }
  // Sin miniatura: el navegador muestra un fotograma del propio video.
  return `<div class="miniatura"><video src="/media/${encodeURIComponent(video.archivo)}#t=1" preload="metadata" muted></video></div>`;
}

function formatearFecha(iso) {
  return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'long', year: 'numeric' });
}

function formatearTamano(bytes) {
  if (bytes > 1024 ** 3) return (bytes / 1024 ** 3).toFixed(1) + ' GB';
  return (bytes / 1024 ** 2).toFixed(1) + ' MB';
}

async function pedirJSON(url, opciones = {}) {
  const res = await fetch(url, opciones);
  const datos = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(datos.error || 'Error de conexión.');
  return datos;
}
