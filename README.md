# Videoteca de tutoriales (Streamlit)

Aplicación sencilla para publicar videos tutoriales y que los estudiantes los vean desde el navegador.

## Funciones

**Videoteca** (para estudiantes)
- Catálogo de tutoriales en tarjetas.
- Buscador por título, descripción o categoría y filtro por categorías.
- Página de reproducción con descripción y otros tutoriales de la misma categoría.

**Administrar** (con contraseña)
- Agregar tutoriales con un enlace de **YouTube** o **Google Drive**, o subiendo el archivo.
- Miniatura opcional (en YouTube y Drive se toma automáticamente).
- Editar título, categoría y descripción; eliminar tutoriales.

## Ejecutar en tu computadora

Requiere Python 3.11 o superior.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abrirá http://localhost:8501. La sección **Administrar** está en el menú lateral.
Copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y completa los valores.
Si no defines `ADMIN_PASSWORD`, la contraseña es `admin123`.

## Almacenamiento permanente con Supabase (para que no se borre nada)

Streamlit Community Cloud borra los archivos locales cada vez que la app se reinicia.
Por eso la lista de tutoriales y los archivos subidos se guardan en [Supabase](https://supabase.com) (gratis).

1. Crea una cuenta en https://supabase.com y pulsa **New project**. Elige un nombre, una contraseña
   para la base de datos y la región más cercana.
2. Cuando el proyecto esté listo, abre **SQL Editor → New query**, pega el contenido de
   [`supabase.sql`](supabase.sql) y pulsa **Run**. Esto crea la tabla `videos` y la carpeta `videoteca`.
3. Ve a **Project Settings → API Keys** y copia:
   - la **Project URL** (`https://xxxxxxxx.supabase.co`, también aparece en **Project Settings → Data API**);
   - una **secret key** (`sb_secret_...`) o, en la pestaña de claves antiguas, la clave **service_role**.
   Esta clave es secreta: no la compartas ni la pongas en GitHub.
4. En Streamlit Cloud abre tu app → **⋮ → Settings → Secrets** y escribe:
   ```toml
   ADMIN_PASSWORD = "tu-contraseña-segura"
   SUPABASE_URL = "https://xxxxxxxx.supabase.co"
   SUPABASE_KEY = "tu-clave-secreta"
   ```
5. Guarda. La app se reinicia y en **Administrar** verás «💾 Almacenamiento permanente activo».

### Límites del plan gratuito

- Supabase permite archivos de hasta **50 MB** y **1 GB** en total. Para videos más pesados
  usa un enlace de **YouTube** (puede ser «no listado») o de **Google Drive**
  (compartido como «Cualquier persona con el enlace»); esos no ocupan espacio en Supabase.
- Supabase pausa los proyectos gratuitos que no tienen actividad durante una semana.
  Los datos **no se borran**: entra en supabase.com y pulsa **Restore project**.

## Publicar en Streamlit Community Cloud

1. Entra en https://share.streamlit.io e inicia sesión con tu cuenta de GitHub.
2. Pulsa **Create app → Deploy a public app from GitHub**.
3. Elige el repositorio `videoteca`, la rama y el archivo `app.py`.
4. En **Advanced settings → Secrets** pega los valores del paso 4 de arriba.
5. Pulsa **Deploy** y comparte el enlace con tus estudiantes.

## Archivos

- `app.py`: la aplicación.
- `almacen.py`: guarda y lee los tutoriales (Supabase, o carpeta local si no está configurado).
- `supabase.sql`: crea la tabla y la carpeta en Supabase.
- `.streamlit/config.toml`: `maxUploadSize` define el tamaño máximo de subida.
