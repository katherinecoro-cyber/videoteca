"""Videoteca de tutoriales hecha con Streamlit.

Los estudiantes buscan y ven tutoriales; el administrador publica videos
(enlaces de YouTube o Google Drive) desde la sección "Administrar".
"""

import base64
import hmac
import html
import os
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

import almacen
from almacen import ErrorAlmacen

BASE = Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"
ASSETS = BASE / "assets"
UPLOAD_DIR.mkdir(exist_ok=True)

FORMATOS_VIDEO = ["mp4", "webm", "ogg", "mov"]
FORMATOS_IMAGEN = ["jpg", "jpeg", "png", "webp"]

# Colores institucionales de Digital Business School.
AZUL_OSCURO = "#1E3460"
AZUL = "#1D70B7"
BLANCO = "#FFFFFF"

st.set_page_config(page_title="Videoteca de Tutoriales · Digital Business School",
                   page_icon=str(ASSETS / "icono_dbs.png"), layout="wide")


# ---------- Encabezado institucional ----------

def imagen_base64(nombre):
    return base64.b64encode((ASSETS / nombre).read_bytes()).decode()


def encabezado():
    st.html(f"""
    <style>
      .vt-banner {{
        display: flex; align-items: center; justify-content: space-between; gap: 24px;
        background: {BLANCO}; border: 1px solid #D6DEEA; border-radius: 14px;
        padding: 16px 24px 20px; position: relative; overflow: hidden;
      }}
      .vt-banner::after {{
        content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 6px;
        background: linear-gradient(90deg, {AZUL_OSCURO} 0 50%, {AZUL} 50% 100%);
      }}
      .vt-banner img {{ width: auto; flex-shrink: 0; }}
      .vt-banner .vt-logo-v {{ height: 110px; }}
      .vt-banner .vt-logo-h {{ height: 64px; }}
      .vt-banner .vt-texto {{ flex: 1; text-align: center; }}
      .vt-banner h1 {{ color: {AZUL_OSCURO}; margin: 0; font-size: 1.9rem; line-height: 1.2; padding: 0; }}
      .vt-banner p {{ margin: 4px 0 0; color: {AZUL}; font-size: 0.95rem; font-weight: 600; }}
      @media (max-width: 640px) {{
        .vt-banner {{ flex-wrap: wrap; justify-content: center; gap: 12px 20px; padding: 12px 12px 18px; }}
        .vt-banner .vt-logo-v {{ height: 64px; }}
        .vt-banner .vt-logo-h {{ height: 36px; }}
        .vt-banner .vt-texto {{ order: 3; flex-basis: 100%; }}
        .vt-banner h1 {{ font-size: 1.3rem; }}
        .vt-banner p {{ font-size: 0.8rem; }}
      }}
    </style>
    <div class="vt-banner">
      <img class="vt-logo-v" src="data:image/png;base64,{imagen_base64('logo_dbs_vertical.png')}"
           alt="Logo de Digital Business School">
      <div class="vt-texto">
        <h1>Videoteca de Tutoriales</h1>
        <p>Digital Business School</p>
      </div>
      <img class="vt-logo-h" src="data:image/png;base64,{imagen_base64('logo_dbs_horizontal.png')}"
           alt="Logo de Digital Business School">
    </div>
    """)
    # Estilos generales: títulos en azul oscuro, botones con borde azul.
    st.html(f"""
    <style>
      .stMainBlockContainer h1, .stMainBlockContainer h2, .stMainBlockContainer h3 {{ color: {AZUL_OSCURO}; }}
      .stMainBlockContainer .stButton button[kind="secondary"] {{
        border-color: {AZUL}; color: {AZUL}; font-weight: 600;
      }}
      .stMainBlockContainer .stButton button[kind="secondary"]:hover {{
        background: {AZUL}; border-color: {AZUL}; color: {BLANCO};
      }}
      .vt-categoria {{
        color: {AZUL}; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
    </style>
    """)


# ---------- Datos ----------

def guardar_archivo(archivo):
    """Guarda un archivo subido con un nombre único y devuelve ese nombre."""
    extension = Path(archivo.name).suffix.lower()
    nombre = f"{uuid.uuid4()}{extension}"
    (UPLOAD_DIR / nombre).write_bytes(archivo.getbuffer())
    return nombre


def borrar_archivo(nombre):
    if nombre:
        (UPLOAD_DIR / Path(nombre).name).unlink(missing_ok=True)


def id_youtube(url):
    m = re.search(r"(?:youtu\.be/|[?&]v=|/shorts/|/embed/|/live/)([\w-]{11})", url or "")
    return m.group(1) if m else None


def id_drive(url):
    if "drive.google.com" not in (url or ""):
        return None
    m = re.search(r"/d/([\w-]{20,})|[?&]id=([\w-]{20,})", url)
    return (m.group(1) or m.group(2)) if m else None


def mostrar_video(video):
    url = video.get("url")
    if id_drive(url):
        components.iframe(f"https://drive.google.com/file/d/{id_drive(url)}/preview", height=480)
    elif url:
        st.video(url)
    elif (UPLOAD_DIR / video["archivo"]).exists():
        st.video(str(UPLOAD_DIR / video["archivo"]))
    else:
        st.warning("El archivo de este video ya no está disponible.")


def mostrar_miniatura(video):
    url = video.get("url")
    if video.get("miniatura") and (UPLOAD_DIR / video["miniatura"]).exists():
        st.image(str(UPLOAD_DIR / video["miniatura"]), use_container_width=True)
    elif id_youtube(url):
        st.image(f"https://img.youtube.com/vi/{id_youtube(url)}/hqdefault.jpg", use_container_width=True)
    elif id_drive(url):
        st.image(f"https://drive.google.com/thumbnail?id={id_drive(url)}&sz=w640", use_container_width=True)
    else:
        mostrar_video(video)


def cargar_videos():
    try:
        return sorted(almacen.leer_videos(), key=lambda v: v["fecha"], reverse=True)
    except (ErrorAlmacen, requests.RequestException) as e:
        st.error(f"No se pudo cargar la lista de tutoriales. {e}")
        st.stop()


def guardar(cambio, mensaje):
    """Guarda un cambio en la lista; devuelve True si salió bien."""
    try:
        with st.spinner("Guardando..."):
            almacen.modificar_videos(cambio, mensaje)
        return True
    except (ErrorAlmacen, requests.RequestException) as e:
        st.error(f"No se pudo guardar. {e}")
        return False


def categorias(videos):
    return sorted({v["categoria"] for v in videos}, key=str.lower)


def fecha_legible(iso):
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y")


def contrasena_admin():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("ADMIN_PASSWORD", "admin123")


# ---------- Conteo de visitas ----------
# Cada navegador recibe una cookie con un código al azar (sin datos personales),
# así se cuenta a cada persona una vez por día aunque recargue la página.

def es_organizadora():
    return st.session_state.get("admin") or bool(st.context.cookies.get("vt_organizador"))


def contar_visita():
    if "visitante" in st.session_state:
        return
    cookies = st.context.cookies
    st.session_state.visitante = cookies.get("vt_visitante") or str(uuid.uuid4())
    dia = almacen.hoy()
    if es_organizadora() or cookies.get("vt_ultimo_dia") == dia:
        return
    almacen.registrar_visita(nueva_persona="vt_visitante" not in cookies)
    st.session_state.setdefault("cookies_pendientes", {}).update(
        vt_visitante=st.session_state.visitante, vt_ultimo_dia=dia)


def guardar_cookies():
    """Escribe en el navegador las cookies pendientes de esta sesión."""
    pendientes = st.session_state.get("cookies_pendientes")
    if pendientes:
        js = "".join(f"window.parent.document.cookie='{k}={v}; path=/; max-age=31536000; SameSite=Lax';"
                     for k, v in pendientes.items())
        st.html("<style>.stElementContainer:has(iframe[height='0']) {display: none;}</style>")
        components.html(f"<script>{js}</script>", height=0)


# ---------- Vista de estudiantes ----------

def tarjeta(video, columna):
    with columna.container(border=True):
        mostrar_miniatura(video)
        st.markdown(f'<span class="vt-categoria">{html.escape(video["categoria"])}</span>',
                    unsafe_allow_html=True)
        st.markdown(f"**{video['titulo']}**")
        if video["descripcion"]:
            resumen = video["descripcion"]
            st.write(resumen[:120] + ("…" if len(resumen) > 120 else ""))
        if st.button("▶ Ver tutorial", key=f"ver-{video['id']}", use_container_width=True):
            st.query_params["video"] = video["id"]
            st.rerun()


def pagina_reproductor(video, videos):
    vistos = st.session_state.setdefault("vistos", set())
    if video["id"] not in vistos and not es_organizadora():
        vistos.add(video["id"])
        almacen.registrar_vista(video["id"], st.session_state.get("visitante"))

    if st.button("← Volver a todos los tutoriales"):
        del st.query_params["video"]
        st.rerun()

    principal, lateral = st.columns([3, 1], gap="large")
    with principal:
        mostrar_video(video)
        st.title(video["titulo"])
        st.caption(f"{video['categoria']} · {fecha_legible(video['fecha'])}")
        if video["descripcion"]:
            st.write(video["descripcion"])

    with lateral:
        st.subheader("Más de esta categoría")
        otros = [v for v in videos if v["categoria"] == video["categoria"] and v["id"] != video["id"]]
        if not otros:
            st.caption("No hay más tutoriales en esta categoría.")
        for v in otros:
            if st.button(v["titulo"], key=f"rel-{v['id']}", use_container_width=True):
                st.query_params["video"] = v["id"]
                st.rerun()


def pagina_catalogo():
    videos = cargar_videos()

    seleccionado = st.query_params.get("video")
    if seleccionado:
        video = next((v for v in videos if v["id"] == seleccionado), None)
        if video:
            pagina_reproductor(video, videos)
            return
        st.warning("Ese tutorial ya no está disponible.")

    st.header("🎬 Tutoriales")
    st.write("Busca un tema o elige una categoría y pulsa **Ver tutorial**.")

    busqueda = st.text_input("Buscar", placeholder="🔍 Buscar tutoriales...", label_visibility="collapsed")
    categoria = st.pills("Categoría", ["Todas"] + categorias(videos), default="Todas",
                         label_visibility="collapsed")

    if categoria and categoria != "Todas":
        videos = [v for v in videos if v["categoria"] == categoria]
    if busqueda:
        q = busqueda.lower()
        videos = [v for v in videos if any(q in v[c].lower() for c in ("titulo", "descripcion", "categoria"))]

    if not videos:
        st.info("No se encontraron tutoriales." if busqueda or categoria != "Todas"
                else "Todavía no hay tutoriales publicados.")
        return

    columnas = st.columns(3)
    for i, video in enumerate(videos):
        tarjeta(video, columnas[i % 3])


# ---------- Vista de administración ----------

def formulario_login():
    st.title("🔒 Acceso de administrador")
    with st.form("login"):
        clave = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            if hmac.compare_digest(clave, contrasena_admin()):
                st.session_state.admin = True
                st.rerun()
            st.error("Contraseña incorrecta.")


def formulario_subida(videos):
    st.subheader("Publicar nuevo tutorial")
    if almacen.USA_GITHUB:
        # Los archivos subidos se borrarían al reiniciar la app; solo se aceptan enlaces.
        origen = "Enlace"
    else:
        origen = st.radio("Origen del video", ["Enlace", "Subir archivo"], horizontal=True,
                          format_func=lambda o: "Enlace de YouTube o Google Drive" if o == "Enlace" else o)

    with st.form("subir", clear_on_submit=True):
        titulo = st.text_input("Título *", max_chars=150)
        categoria = st.selectbox("Categoría", categorias(videos), index=None, accept_new_options=True,
                                 placeholder="Elige una o escribe una nueva")
        descripcion = st.text_area("Descripción", max_chars=5000)
        archivo = miniatura = None
        url = ""
        if origen == "Subir archivo":
            archivo = st.file_uploader("Archivo de video * (MP4 recomendado)", type=FORMATOS_VIDEO)
            miniatura = st.file_uploader("Miniatura (opcional)", type=FORMATOS_IMAGEN)
        else:
            url = st.text_input("Enlace del video *",
                                placeholder="https://www.youtube.com/watch?v=...  o  https://drive.google.com/file/d/...")
            st.caption("En YouTube puedes subirlo como «No listado». En Google Drive, compártelo como "
                       "«Cualquier persona con el enlace». La miniatura se toma automáticamente.")

        if not st.form_submit_button("Publicar tutorial", type="primary"):
            return
        url = url.strip()
        if not titulo.strip():
            st.error("El título es obligatorio.")
            return
        if origen == "Subir archivo" and not archivo:
            st.error("Selecciona un archivo de video.")
            return
        if origen == "Enlace" and not (id_youtube(url) or id_drive(url)):
            st.error("Escribe un enlace válido de YouTube o de Google Drive.")
            return

        nuevo = {
            "id": str(uuid.uuid4()),
            "titulo": titulo.strip(),
            "descripcion": descripcion.strip(),
            "categoria": (categoria or "").strip() or "General",
            "archivo": guardar_archivo(archivo) if archivo else None,
            "url": url or None,
            "miniatura": guardar_archivo(miniatura) if miniatura else None,
            "fecha": datetime.now().isoformat(timespec="seconds"),
        }
        if guardar(lambda vs: vs + [nuevo], f"Publicar tutorial: {nuevo['titulo']}"):
            # Recargar para que el nuevo tutorial aparezca en la lista de abajo.
            st.session_state.aviso = "✔ Tutorial publicado correctamente."
            st.rerun()


def lista_publicados(videos):
    st.subheader(f"Tutoriales publicados ({len(videos)})")
    if not videos:
        st.caption("Aún no has publicado tutoriales.")
        return

    for video in videos:
        with st.expander(f"{video['titulo']}  ·  {video['categoria']}"):
            with st.form(f"editar-{video['id']}"):
                titulo = st.text_input("Título", video["titulo"], max_chars=150)
                categoria = st.text_input("Categoría", video["categoria"], max_chars=80)
                descripcion = st.text_area("Descripción", video["descripcion"], max_chars=5000)
                if st.form_submit_button("Guardar cambios"):
                    if not titulo.strip():
                        st.error("El título es obligatorio.")
                    else:
                        cambios = {"titulo": titulo.strip(), "categoria": categoria.strip() or "General",
                                   "descripcion": descripcion.strip()}
                        if guardar(lambda vs: [{**v, **cambios} if v["id"] == video["id"] else v for v in vs],
                                   f"Editar tutorial: {cambios['titulo']}"):
                            st.rerun()

            confirmar = st.checkbox("Confirmo que quiero eliminar este tutorial", key=f"conf-{video['id']}")
            if st.button("🗑 Eliminar", key=f"del-{video['id']}", disabled=not confirmar):
                if guardar(lambda vs: [v for v in vs if v["id"] != video["id"]],
                           f"Eliminar tutorial: {video['titulo']}"):
                    borrar_archivo(video.get("archivo"))
                    borrar_archivo(video.get("miniatura"))
                    st.rerun()


def pagina_admin():
    if not st.session_state.get("admin"):
        formulario_login()
        return

    # Marca este navegador como de la organizadora para no contar sus visitas.
    if not st.context.cookies.get("vt_organizador"):
        st.session_state.setdefault("cookies_pendientes", {})["vt_organizador"] = "1"

    st.title("⚙️ Administrar videoteca")
    if st.button("Cerrar sesión"):
        st.session_state.admin = False
        st.rerun()

    if almacen.USA_GITHUB:
        st.success("💾 Guardado permanente activo: la lista de tutoriales se guarda en GitHub.")
    else:
        st.warning("⚠️ Guardado temporal: los tutoriales se borrarán cuando la app se reinicie. "
                   "Agrega VIDEOTECA_GITHUB_TOKEN en los Secrets para guardarlos de forma permanente.")
    if "aviso" in st.session_state:
        st.success(st.session_state.pop("aviso"))

    videos = cargar_videos()
    pestana_tutoriales, pestana_estadisticas = st.tabs(["🎬 Tutoriales", "📊 Estadísticas"])
    with pestana_tutoriales:
        formulario_subida(videos)
        st.divider()
        lista_publicados(videos)
    with pestana_estadisticas:
        panel_estadisticas(videos)


def panel_estadisticas(videos):
    try:
        datos = almacen.leer_estadisticas()
    except (ErrorAlmacen, requests.RequestException) as e:
        st.error(f"No se pudieron cargar las estadísticas. {e}")
        return

    visitas = datos.get("visitas_por_dia", {})
    vistas_video = datos.get("vistas_por_video", {})
    hoy = date.fromisoformat(almacen.hoy())
    ultimos_7 = sum(visitas.get((hoy - timedelta(days=i)).isoformat(), 0) for i in range(7))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Personas hoy", visitas.get(hoy.isoformat(), 0))
    c2.metric("Ingresos en 7 días", ultimos_7)
    c3.metric("Personas distintas en total", sum(datos.get("personas_nuevas_por_dia", {}).values()))
    c4.metric("Tutoriales vistos en total", sum(vistas_video.values()))

    st.subheader("Personas que entraron por día · últimos 30 días")
    dias = [hoy - timedelta(days=i) for i in range(29, -1, -1)]
    serie = pd.DataFrame({"Día": pd.to_datetime(dias),
                          "Personas": [visitas.get(d.isoformat(), 0) for d in dias]})
    grafico = alt.Chart(serie).mark_bar(color=AZUL, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("yearmonthdate(Día):O", title=None,
                axis=alt.Axis(format="%d/%m", labelAngle=-45, labelOverlap=True)),
        y=alt.Y("Personas:Q", title=None, axis=alt.Axis(tickMinStep=1, format="d")),
        tooltip=[alt.Tooltip("Día:T", title="Día", format="%d/%m/%Y"), alt.Tooltip("Personas:Q")],
    ).properties(height=260)
    st.altair_chart(grafico, use_container_width=True)

    st.subheader("Vistas por tutorial")
    if not videos:
        st.caption("Aún no hay tutoriales publicados.")
    else:
        tabla = pd.DataFrame([{"Tutorial": v["titulo"], "Categoría": v["categoria"],
                               "Vistas": vistas_video.get(v["id"], 0)} for v in videos])
        tabla = tabla.sort_values("Vistas", ascending=False, kind="stable")
        st.dataframe(tabla, hide_index=True, use_container_width=True, column_config={
            "Vistas": st.column_config.ProgressColumn(
                "Vistas", format="%d", min_value=0, max_value=max(int(tabla["Vistas"].max()), 1)),
        })

    st.caption("Cada navegador cuenta como una persona: se cuenta una vez por día aunque recargue la página. "
               "Si alguien usa otro navegador, otro dispositivo o una ventana de incógnito, cuenta como otra "
               "persona. **Ingresos en 7 días** suma las personas de cada día (quien entra 3 días cuenta 3 "
               "veces). **Vistas:** cada vez que alguien abre la página de un tutorial, una vez por día. "
               "Tus propias visitas como organizadora no se cuentan. Los datos se guardan cada 2 minutos.")


# ---------- Navegación ----------

pagina = st.navigation([
    st.Page(pagina_catalogo, title="Videoteca", icon="🎬", default=True),
    st.Page(pagina_admin, title="Administrar", icon="⚙️", url_path="admin"),
])
encabezado()
# La visita se cuenta solo en la videoteca (no en Administrar), y las cookies se escriben
# antes de mostrar la página para que queden guardadas aunque la persona recargue rápido.
if pagina.title == "Videoteca":
    contar_visita()
guardar_cookies()
pagina.run()
