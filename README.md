# Videoteca de tutoriales

Plataforma sencilla para publicar videos tutoriales y que los estudiantes los vean desde el navegador.

## Funciones

**Para estudiantes** (`/`)
- Catálogo de tutoriales en tarjetas con miniatura.
- Buscador por título, descripción o categoría.
- Filtro por categorías.
- Reproductor con opción de adelantar/retroceder, y que recuerda en qué minuto se quedó cada estudiante.
- Lista de otros tutoriales de la misma categoría.

**Para administradores** (`/admin.html`)
- Acceso con contraseña.
- Subida de videos (MP4, WebM, OGG, MOV) con barra de progreso y miniatura opcional.
- Editar título, categoría y descripción.
- Eliminar tutoriales.

## Instalación

Requiere [Node.js](https://nodejs.org) 18 o superior.

```bash
npm install
ADMIN_PASSWORD="tu-contraseña-segura" npm start
```

Abre http://localhost:3000 para ver la videoteca y http://localhost:3000/admin.html para subir videos.

En Windows (PowerShell):

```powershell
npm install
$env:ADMIN_PASSWORD="tu-contraseña-segura"; npm start
```

## Configuración

| Variable         | Descripción                                   | Valor por defecto |
|------------------|-----------------------------------------------|-------------------|
| `ADMIN_PASSWORD` | Contraseña del panel de administración        | `admin123` (¡cámbiala!) |
| `PORT`           | Puerto del servidor                           | `3000`            |
| `MAX_VIDEO_MB`   | Tamaño máximo por video, en MB                | `2048`            |

## Dónde se guardan los datos

- `uploads/`: los archivos de video y miniaturas.
- `data/videos.json`: título, descripción y categoría de cada video.

Haz copias de seguridad de ambas carpetas. Ninguna se sube a Git.

## Recomendaciones

- Usa **MP4 (H.264)**: es el formato que funciona en todos los navegadores y celulares.
- Para publicarlo en internet, despliega en un servidor con disco persistente (VPS, Render con disco, Railway, etc.) y usa HTTPS.
