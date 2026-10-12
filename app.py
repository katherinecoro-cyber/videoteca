"""Videoteca de tutoriales hecha con Streamlit.

Los estudiantes buscan y ven tutoriales; el administrador sube videos
(archivo, o enlace de YouTube o Google Drive) desde la sección "Administrar".
"""

import hmac
import re
import uuid
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

import almacen
from almacen import ErrorAlmacen

FORMATOS_VIDEO = ["mp4", "webm", "ogg", "mov"]
FORMATOS_IMAGEN = ["jpg", "jpeg", "png", "webp"]

st.set_page_config(page_title="Videoteca de Tutoriales", page_icon="🎬", layout="wide")


# ---------- Utilidades ----------

def id_youtube(url):
    m = re.search(r"(?:youtu\.be/|[?&]v=|/shorts/|/embed/|/live/)([\w-]{11})", url or "")
    return m.group(1) if m else None


def id_drive(url):
    if "drive.google.com" not in (url or ""):
        return None
    m = re.search(r"/d/([\w-]{20,})|[?&]id=([\w-]{20,})", url)
    return (m.group(1) or m.group(2)) if m else None


def mostrar_video(video):
    if video.get("url") and id_drive(video["url"]):
        components.iframe(f"https://drive.google.com/file/d/{id_drive(video['url'])}/preview", height=480)
    elif video.get("url"):
        st.video(video["url"])
    else:
        st.video(almacen.ruta_archivo(video["archivo"]))


def mostrar_miniatura(video):
    url = video.get("url")
    if video.get("miniatura"):
        st.image(almacen.ruta_archivo(video["miniatura"]), use_container_width=True)
    elif id_youtube(url):
        st.image(f"https://img.youtube.com/vi/{id_youtube(url)}/hqdefault.jpg", use_container_width=True)
    elif id_drive(url):
        st.image(f"https://drive.google.com/thumbnail?id={id_drive(url)}&sz=w640", use_container_width=True)
    else:
        mostrar_video(video)


def categorias(videos):
    return sorted({v["categoria"] for v in videos}, key=str.lower)


def fecha_legible(iso):
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y")


def cargar_videos():
    try:
        return sorted(almacen.leer_videos(), key=lambda v: v["fecha"], reverse=True)
    except (ErrorAlmacen, OSError) as e:
        st.error(f"No se pudo cargar la lista de tutoriales. {e}")
        st.stop()


def contrasena_admin():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except (KeyError, FileNotFoundError):
        return "admin123"


# ---------- Vista de estudiantes ----------

def tarjeta(video, columna):
    with columna.container(border=True):
        mostrar_miniatura(video)
        st.caption(video["categoria"].upper())
        st.markdown(f"**{video['titulo']}**")
        if video["descripcion"]:
            resumen = video["descripcion"]
            st.write(resumen[:120] + ("…" if len(resumen) > 120 else ""))
        if st.button("▶ Ver tutorial", key=f"ver-{video['id']}", use_container_width=True):
            st.query_params["video"] = video["id"]
            st.rerun()


def pagina_reproductor(video, videos):
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

    st.title("🎬 Tutoriales")
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
    st.subheader("Subir nuevo tutorial")
    origen = st.radio("Origen del video", ["Enlace de YouTube o Google Drive", "Subir archivo"], horizontal=True)
    if origen == "Subir archivo" and almacen.USA_SUPABASE:
        st.caption(f"Máximo {almacen.LIMITE_SUPABASE_MB} MB por archivo. "
                   "Para videos más pesados usa un enlace de YouTube o Google Drive.")

    with st.form("subir", clear_on_submit=True):
        titulo = st.text_input("Título *", max_chars=150)
        categoria = st.selectbox("Categoría", categorias(videos), index=None, accept_new_options=True,
                                 placeholder="Elige una o escribe una nueva")
        descripcion = st.text_area("Descripción", max_chars=5000)
        if origen == "Subir archivo":
            archivo = st.file_uploader("Archivo de video * (MP4 recomendado)", type=FORMATOS_VIDEO)
            url = None
        else:
            url = st.text_input("Enlace del video *",
                                placeholder="https://www.youtube.com/watch?v=...  o  https://drive.google.com/file/d/...")
            st.caption("En Google Drive, comparte el video como «Cualquier persona con el enlace».")
            archivo = None
        miniatura = st.file_uploader("Miniatura (opcional)", type=FORMATOS_IMAGEN)

        if not st.form_submit_button("Publicar tutorial", type="primary"):
            return
        url = (url or "").strip()
        if not titulo.strip():
            st.error("El título es obligatorio.")
            return
        if origen == "Subir archivo" and not archivo:
            st.error("Selecciona un archivo de video.")
            return
        if origen != "Subir archivo" and not url.startswith("http"):
            st.error("Escribe un enlace válido.")
            return

        try:
            with st.spinner("Guardando el tutorial..."):
                almacen.agregar_video({
                    "id": str(uuid.uuid4()),
                    "titulo": titulo.strip(),
                    "descripcion": descripcion.strip(),
                    "categoria": (categoria or "").strip() or "General",
                    "archivo": almacen.guardar_archivo(archivo) if archivo else None,
                    "url": url or None,
                    "miniatura": almacen.guardar_archivo(miniatura) if miniatura else None,
                    "fecha": datetime.now().isoformat(timespec="seconds"),
                })
        except (ErrorAlmacen, OSError) as e:
            st.error(f"No se pudo guardar. {e}")
            return
        # Recargar para que el nuevo tutorial aparezca en la lista de abajo.
        st.session_state.aviso = "✔ Tutorial publicado correctamente."
        st.rerun()


def lista_publicados(videos):
    st.subheader(f"Tutoriales publicados ({len(videos)})")
    if not videos:
        st.caption("Aún no has subido tutoriales.")
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
                        try:
                            almacen.actualizar_video(video["id"], {
                                "titulo": titulo.strip(),
                                "categoria": categoria.strip() or "General",
                                "descripcion": descripcion.strip(),
                            })
                            st.rerun()
                        except ErrorAlmacen as e:
                            st.error(f"No se pudo guardar. {e}")

            confirmar = st.checkbox("Confirmo que quiero eliminar este tutorial", key=f"conf-{video['id']}")
            if st.button("🗑 Eliminar", key=f"del-{video['id']}", disabled=not confirmar):
                try:
                    almacen.eliminar_video(video)
                    st.rerun()
                except ErrorAlmacen as e:
                    st.error(f"No se pudo eliminar. {e}")


def pagina_admin():
    if not st.session_state.get("admin"):
        formulario_login()
        return

    st.title("⚙️ Administrar videoteca")
    if st.button("Cerrar sesión"):
        st.session_state.admin = False
        st.rerun()

    if almacen.USA_SUPABASE:
        st.success("💾 Almacenamiento permanente activo (Supabase).")
    else:
        st.warning("⚠️ Supabase no está configurado: los tutoriales se guardan de forma temporal "
                   "y se borrarán cuando la app se reinicie. Revisa el README para activarlo.")

    if "aviso" in st.session_state:
        st.success(st.session_state.pop("aviso"))

    videos = cargar_videos()
    formulario_subida(videos)
    st.divider()
    lista_publicados(videos)


# ---------- Navegación ----------

pagina = st.navigation([
    st.Page(pagina_catalogo, title="Videoteca", icon="🎬", default=True),
    st.Page(pagina_admin, title="Administrar", icon="⚙️", url_path="admin"),
])
pagina.run()
