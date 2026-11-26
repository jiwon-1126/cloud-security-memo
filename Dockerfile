FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --gid 10001 memo && useradd --uid 10001 --gid 10001 --no-create-home memo
COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY --chown=10001:10001 app.py wsgi.py init_db.py start.sh ./
COPY --chown=10001:10001 templates/ templates/
COPY --chown=10001:10001 static/ static/
COPY --chown=10001:10001 scripts/container-entrypoint.sh /app/entrypoint.sh
USER 10001:10001
EXPOSE 5000
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
