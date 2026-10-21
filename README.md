# Videoteca de tutoriales (Streamlit)

Digital Business School (DBS).

Aplicación sencilla para publicar videos tutoriales y que los estudiantes los vean desde el navegador.

## Funciones

**Videoteca** (para estudiantes)
- Catálogo de tutoriales en tarjetas.
- Buscador por título, descripción o categoría y filtro por categorías.
- Página de reproducción con descripción y otros tutoriales de la misma categoría.

**Administrar** (con contraseña)
- Subir videos (MP4, WebM, OGG, MOV) o agregar un enlace de YouTube.
- Miniatura opcional.
- Editar título, categoría y descripción; eliminar tutoriales.

## Ejecutar en tu computadora

Requiere Python 3.9 o superior.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abrirá http://localhost:8501. La sección **Administrar** está en el menú lateral.

Contraseña de administrador: copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml`
y cambia el valor de `ADMIN_PASSWORD`. Si no la defines, la contraseña es `admin123`.

## Publicar en Streamlit Community Cloud

1. Entra en https://share.streamlit.io e inicia sesión con tu cuenta de GitHub.
2. Pulsa **Create app → Deploy a public app from GitHub**.
3. Elige el repositorio `videoteca`, la rama `main` y el archivo `app.py`.
4. En **Advanced settings → Secrets** escribe:
   ```toml
   ADMIN_PASSWORD = "tu-contraseña-segura"
   ```
5. Pulsa **Deploy** y comparte el enlace con tus estudiantes.

### ⚠️ Importante sobre el almacenamiento

Streamlit Community Cloud **no guarda archivos de forma permanente**: cuando la app se reinicia
(por inactividad o por una actualización), se borran los videos subidos y la lista `data/videos.json`.

Mientras tanto, la opción más segura es publicar los tutoriales como **enlaces de YouTube**
(pueden ser videos "no listados") en lugar de subir el archivo. Para guardar los datos de forma
permanente hace falta conectar un almacenamiento externo (por ejemplo, Supabase o Google Drive).

## Configuración

- `.streamlit/config.toml`: colores institucionales (azul oscuro `#1E3460`, azul `#1D70B7`, blanco `#FFFFFF`) y `maxUploadSize` define el tamaño máximo de subida (1024 MB).
- `assets/`: logos de Digital Business School (horizontal, vertical e ícono).
- `uploads/`: archivos de video y miniaturas.
- `data/videos.json`: datos de cada tutorial.
