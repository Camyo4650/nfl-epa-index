FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NFLREADPY_VERBOSE=false
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY engine.py service.py store.py playoffs.py playoff_probability.py playoff_standings.py ./
RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["python", "service.py"]
