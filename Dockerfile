# Imagen de la Videoteca de Tutoriales (Streamlit).
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# data/ (lista de tutoriales y estadísticas) y uploads/ (videos subidos) deben montarse
# como volúmenes para que no se pierdan al actualizar o recrear el contenedor.
VOLUME ["/app/data", "/app/uploads"]

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
