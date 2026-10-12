// Videoteca de tutoriales: servidor Express que guarda los videos en disco
// y su información (título, descripción, categoría) en data/videos.json.

const express = require('express');
const multer = require('multer');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';
const MAX_MB = Number(process.env.MAX_VIDEO_MB || 2048);

const DATA_FILE = path.join(__dirname, 'data', 'videos.json');
const UPLOAD_DIR = path.join(__dirname, 'uploads');
fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
fs.mkdirSync(UPLOAD_DIR, { recursive: true });

if (!process.env.ADMIN_PASSWORD) {
  console.warn('AVISO: usando la contraseña por defecto "admin123". Define ADMIN_PASSWORD para cambiarla.');
}

// ---------- Almacenamiento de datos ----------

function leerVideos() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } catch {
    return [];
  }
}

function guardarVideos(videos) {
  const tmp = DATA_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(videos, null, 2));
  fs.renameSync(tmp, DATA_FILE);
}

function borrarArchivo(nombre) {
  if (!nombre) return;
  fs.unlink(path.join(UPLOAD_DIR, path.basename(nombre)), () => {});
}

// ---------- Sesión de administrador ----------

const sesiones = new Set();

function leerCookie(req, nombre) {
  const cookies = req.headers.cookie || '';
  for (const parte of cookies.split(';')) {
    const [k, ...v] = parte.trim().split('=');
    if (k === nombre) return decodeURIComponent(v.join('='));
  }
  return null;
}

function esAdmin(req) {
  const token = leerCookie(req, 'vt_admin');
  return token && sesiones.has(token);
}

function soloAdmin(req, res, next) {
  if (!esAdmin(req)) return res.status(401).json({ error: 'Debes iniciar sesión como administrador.' });
  next();
}

function compararSeguro(a, b) {
  const ha = crypto.createHash('sha256').update(String(a)).digest();
  const hb = crypto.createHash('sha256').update(String(b)).digest();
  return crypto.timingSafeEqual(ha, hb);
}

// ---------- Subida de archivos ----------

const TIPOS_VIDEO = ['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'];
const TIPOS_IMAGEN = ['image/jpeg', 'image/png', 'image/webp'];

const upload = multer({
  storage: multer.diskStorage({
    destination: UPLOAD_DIR,
    filename: (req, file, cb) => {
      const ext = path.extname(file.originalname).toLowerCase().replace(/[^.a-z0-9]/g, '');
      cb(null, crypto.randomUUID() + ext);
    },
  }),
  limits: { fileSize: MAX_MB * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    const permitidos = file.fieldname === 'video' ? TIPOS_VIDEO : TIPOS_IMAGEN;
    if (permitidos.includes(file.mimetype)) return cb(null, true);
    cb(new Error(`Formato no permitido para ${file.fieldname}: ${file.mimetype}`));
  },
});

const camposSubida = upload.fields([
  { name: 'video', maxCount: 1 },
  { name: 'miniatura', maxCount: 1 },
]);

function limpiarTexto(valor, max) {
  return String(valor || '').trim().slice(0, max);
}

// ---------- Aplicación ----------

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));
// express.static admite peticiones por rangos, lo que permite adelantar el video.
app.use('/media', express.static(UPLOAD_DIR, { maxAge: '7d' }));

app.post('/api/login', (req, res) => {
  if (!compararSeguro(req.body?.password || '', ADMIN_PASSWORD)) {
    return res.status(401).json({ error: 'Contraseña incorrecta.' });
  }
  const token = crypto.randomBytes(32).toString('hex');
  sesiones.add(token);
  res.setHeader('Set-Cookie', `vt_admin=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${60 * 60 * 8}`);
  res.json({ ok: true });
});

app.post('/api/logout', (req, res) => {
  sesiones.delete(leerCookie(req, 'vt_admin'));
  res.setHeader('Set-Cookie', 'vt_admin=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0');
  res.json({ ok: true });
});

app.get('/api/sesion', (req, res) => {
  res.json({ admin: Boolean(esAdmin(req)) });
});

app.get('/api/categorias', (req, res) => {
  const categorias = [...new Set(leerVideos().map((v) => v.categoria))].sort((a, b) => a.localeCompare(b, 'es'));
  res.json(categorias);
});

app.get('/api/videos', (req, res) => {
  const q = limpiarTexto(req.query.q, 100).toLowerCase();
  const categoria = limpiarTexto(req.query.categoria, 80);
  let videos = leerVideos();
  if (categoria) videos = videos.filter((v) => v.categoria === categoria);
  if (q) {
    videos = videos.filter((v) =>
      [v.titulo, v.descripcion, v.categoria].some((t) => t.toLowerCase().includes(q))
    );
  }
  videos.sort((a, b) => b.fecha.localeCompare(a.fecha));
  res.json(videos);
});

app.get('/api/videos/:id', (req, res) => {
  const video = leerVideos().find((v) => v.id === req.params.id);
  if (!video) return res.status(404).json({ error: 'Video no encontrado.' });
  res.json(video);
});

app.post('/api/videos', soloAdmin, camposSubida, (req, res) => {
  const archivoVideo = req.files?.video?.[0];
  const archivoMiniatura = req.files?.miniatura?.[0];
  const titulo = limpiarTexto(req.body.titulo, 150);

  if (!archivoVideo || !titulo) {
    borrarArchivo(archivoVideo?.filename);
    borrarArchivo(archivoMiniatura?.filename);
    return res.status(400).json({ error: 'El título y el archivo de video son obligatorios.' });
  }

  const video = {
    id: crypto.randomUUID(),
    titulo,
    descripcion: limpiarTexto(req.body.descripcion, 5000),
    categoria: limpiarTexto(req.body.categoria, 80) || 'General',
    archivo: archivoVideo.filename,
    tipo: archivoVideo.mimetype,
    miniatura: archivoMiniatura?.filename || null,
    tamano: archivoVideo.size,
    fecha: new Date().toISOString(),
  };

  const videos = leerVideos();
  videos.push(video);
  guardarVideos(videos);
  res.status(201).json(video);
});

app.put('/api/videos/:id', soloAdmin, (req, res) => {
  const videos = leerVideos();
  const video = videos.find((v) => v.id === req.params.id);
  if (!video) return res.status(404).json({ error: 'Video no encontrado.' });

  const titulo = limpiarTexto(req.body.titulo, 150);
  if (!titulo) return res.status(400).json({ error: 'El título es obligatorio.' });

  video.titulo = titulo;
  video.descripcion = limpiarTexto(req.body.descripcion, 5000);
  video.categoria = limpiarTexto(req.body.categoria, 80) || 'General';
  guardarVideos(videos);
  res.json(video);
});

app.delete('/api/videos/:id', soloAdmin, (req, res) => {
  const videos = leerVideos();
  const indice = videos.findIndex((v) => v.id === req.params.id);
  if (indice === -1) return res.status(404).json({ error: 'Video no encontrado.' });

  const [video] = videos.splice(indice, 1);
  guardarVideos(videos);
  borrarArchivo(video.archivo);
  borrarArchivo(video.miniatura);
  res.json({ ok: true });
});

// Errores de subida (tamaño, formato) en formato JSON.
app.use((err, req, res, next) => {
  for (const lista of Object.values(req.files || {})) {
    for (const f of lista) borrarArchivo(f.filename);
  }
  if (err.code === 'LIMIT_FILE_SIZE') {
    return res.status(413).json({ error: `El archivo supera el límite de ${MAX_MB} MB.` });
  }
  res.status(400).json({ error: err.message || 'Error al procesar la solicitud.' });
});

app.listen(PORT, () => {
  console.log(`Videoteca disponible en http://localhost:${PORT}`);
  console.log(`Panel de administración: http://localhost:${PORT}/admin.html`);
});
