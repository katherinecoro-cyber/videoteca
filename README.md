# Videoteca de tutoriales (Streamlit)

Digital Business School (DBS).

Aplicación sencilla para publicar videos tutoriales y que los estudiantes los vean desde el navegador.

## Funciones

**Videoteca** (para estudiantes)
- Catálogo de tutoriales en tarjetas.
- Buscador por título, descripción o categoría y filtro por categorías.
- Página de reproducción con descripción y otros tutoriales de la misma categoría.

**Administrar** (con contraseña)
- Publicar tutoriales con un enlace de **YouTube** o **Google Drive** (la miniatura se toma automáticamente).
- Editar título, categoría y descripción; eliminar tutoriales.
- **Estadísticas** (solo visibles para la organizadora): personas que entran por día, personas
  distintas en total y cuántas veces se abrió cada tutorial.

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

## Guardado permanente en GitHub (para que no se borre nada)

Streamlit Community Cloud borra los archivos locales cada vez que la app se reinicia.
Por eso la lista de tutoriales se guarda en este mismo repositorio de GitHub, en el archivo
`data/videos.json` de la rama **`datos-videoteca`** (la app la crea sola). Los videos se publican
como enlaces de YouTube o Google Drive, que tampoco se borran.

1. Crea un token en https://github.com/settings/personal-access-tokens/new
   - **Token name:** `videoteca`
   - **Expiration:** la fecha más lejana que permita (anótala: cuando venza hay que crear otro).
   - **Repository access:** *Only select repositories* → `videoteca`.
   - **Permissions → Repository permissions → Contents:** *Read and write*.
   - Pulsa **Generate token** y copia el token (empieza con `github_pat_`). Solo se muestra una vez.
2. En Streamlit Cloud abre tu app → **⋮ → Settings → Secrets** y agrega:
   ```toml
   VIDEOTECA_GITHUB_TOKEN = "github_pat_..."
   ```
3. Guarda. En **Administrar** verás «💾 Guardado permanente activo».

Las estadísticas de uso se guardan en el mismo lugar, en `data/estadisticas.json`. Para no hacer un
cambio en GitHub por cada visita, se acumulan en memoria y se guardan juntas cada 2 minutos (o cada 25
visitas); si la app se reinicia justo antes, se pueden perder los conteos de esos últimos minutos.

### Cómo se cuentan las visitas

Cada navegador recibe una cookie con un código al azar (sin datos personales). Así cada persona cuenta
una vez por día aunque recargue la página, y cada tutorial cuenta una vez por persona y día. Otro
navegador, otro dispositivo o una ventana de incógnito cuentan como otra persona. El navegador de la
organizadora queda marcado al iniciar sesión en Administrar y sus visitas no se cuentan.

Sin el token, la app funciona igual pero los tutoriales se borran al reiniciarse.
Opcionales: `VIDEOTECA_GITHUB_REPO` (por defecto `katherinecoro-cyber/videoteca`),
`VIDEOTECA_RAMA_DATOS` (por defecto `datos-videoteca`) y `VIDEOTECA_ZONA_HORARIA`
(por defecto `America/La_Paz`, para decidir a qué día pertenece cada visita).

## Configuración

- `.streamlit/config.toml`: colores institucionales (azul oscuro `#1E3460`, azul `#1D70B7`, blanco `#FFFFFF`) y `maxUploadSize` define el tamaño máximo de subida (1024 MB).
- `assets/`: logos de Digital Business School (horizontal, vertical e ícono).
- `almacen.py`: guarda y lee la lista de tutoriales y las estadísticas (GitHub, o carpeta local si no hay token).
- `data/videos.json`: lista de tutoriales cuando se usa el modo local.
