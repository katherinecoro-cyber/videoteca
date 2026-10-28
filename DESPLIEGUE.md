# Guía de instalación en un servidor propio

Guía para el equipo de sistemas. La aplicación es una app de **Python + Streamlit**: no necesita base
de datos y guarda sus datos en archivos JSON.

## Resumen técnico

| | |
|---|---|
| Lenguaje | Python 3.10 o superior |
| Dependencias | `requirements.txt` (streamlit, requests, tzdata) |
| Comando | `streamlit run app.py` |
| Puerto | 8501 (configurable) |
| Base de datos | No usa. Los datos están en `data/` (JSON) y `uploads/` (videos subidos) |
| Configuración | `.streamlit/config.toml` (tema, tamaño máximo de subida) y `.streamlit/secrets.toml` (contraseña) |
| Comprobación de salud | `GET /_stcore/health` responde `ok` |
| Requisito del proxy | Debe permitir **WebSockets** (Streamlit los usa en `/_stcore/stream`) |

## 1. Obtener el código

```bash
git clone https://github.com/katherinecoro-cyber/videoteca.git
cd videoteca
```

## 2. Configurar la contraseña y el modo de guardado

Crear `.streamlit/secrets.toml` (no se sube a Git):

```toml
ADMIN_PASSWORD = "contraseña-segura-de-la-organizadora"
```

**Modo de guardado.** En un servidor propio el disco es permanente, así que lo más simple es **no**
definir `VIDEOTECA_GITHUB_TOKEN`:

- **Sin token (recomendado en servidor propio):** la lista de tutoriales y las estadísticas se guardan
  en `data/*.json` y los videos subidos en `uploads/`. Permite subir archivos de video además de
  enlaces de YouTube/Drive. **Hay que incluir `data/` y `uploads/` en las copias de seguridad.**
- **Con token:** la lista y las estadísticas se guardan en la rama `datos-videoteca` del repositorio
  de GitHub (ver README). Solo se permiten enlaces de YouTube/Drive.

Para migrar los tutoriales ya publicados en Streamlit Cloud al modo sin token, copiar
`data/videos.json` y `data/estadisticas.json` de la rama `datos-videoteca` a la carpeta `data/` del servidor.

Opcional: `VIDEOTECA_ZONA_HORARIA` (por defecto `America/La_Paz`) define a qué día pertenece cada visita.

## 3a. Instalación directa (Linux con systemd)

```bash
sudo useradd --system --home /opt/videoteca videoteca
sudo git clone https://github.com/katherinecoro-cyber/videoteca.git /opt/videoteca
cd /opt/videoteca
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt
sudo nano .streamlit/secrets.toml          # ver paso 2
sudo chown -R videoteca:videoteca /opt/videoteca
```

`/etc/systemd/system/videoteca.service`:

```ini
[Unit]
Description=Videoteca de Tutoriales (Streamlit)
After=network.target

[Service]
User=videoteca
WorkingDirectory=/opt/videoteca
ExecStart=/opt/videoteca/venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now videoteca
curl http://127.0.0.1:8501/_stcore/health     # debe responder: ok
```

## 3b. Instalación con Docker

El repositorio incluye un `Dockerfile`. `data/` y `uploads/` deben ser volúmenes para que no se pierdan
al actualizar el contenedor:

```bash
docker build -t videoteca .
docker run -d --name videoteca --restart unless-stopped -p 127.0.0.1:8501:8501 \
  -v /srv/videoteca/data:/app/data \
  -v /srv/videoteca/uploads:/app/uploads \
  -v /srv/videoteca/secrets.toml:/app/.streamlit/secrets.toml:ro \
  videoteca
```

## 4. Proxy inverso con HTTPS (nginx)

Streamlit necesita WebSockets; sin las cabeceras `Upgrade`/`Connection` la página queda cargando.
`client_max_body_size` debe coincidir con `maxUploadSize` de `.streamlit/config.toml` (1024 MB).

```nginx
server {
    listen 443 ssl;
    server_name videoteca.ejemplo.com;
    # ssl_certificate ...;  ssl_certificate_key ...;   (por ejemplo con certbot)

    client_max_body_size 1024m;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

**Si se publica en una subruta** (por ejemplo `https://dbs.ejemplo.com/videoteca/`), agregar
`--server.baseUrlPath videoteca` al comando de inicio y usar `location /videoteca/` con
`proxy_pass http://127.0.0.1:8501/videoteca/;`.

## 5. Actualizar a una versión nueva

```bash
cd /opt/videoteca
sudo -u videoteca git pull
sudo -u videoteca ./venv/bin/pip install -r requirements.txt
sudo systemctl restart videoteca
```

`git pull` no toca `data/`, `uploads/` ni `.streamlit/secrets.toml` (están en `.gitignore`).

## Notas

- **Copias de seguridad:** `data/` y `uploads/` (modo sin token) y `.streamlit/secrets.toml`.
- **Espacio en disco:** los videos subidos se guardan en `uploads/`; conviene vigilar el espacio o
  publicar los videos pesados como enlaces de YouTube/Drive.
- **Estadísticas:** se cuentan con cookies anónimas (`vt_visitante`, `vt_ultimo_dia`, `vt_organizador`),
  sin datos personales. Se guardan en `data/estadisticas.json`.
- **Un solo proceso:** la app está pensada para ejecutarse en una sola instancia. Con varias réplicas
  detrás de un balanceador, los archivos de `data/` no se compartirían entre ellas.
