FROM python:3.12-alpine@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4 AS build

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip==26.2.1 \
    && /opt/venv/bin/pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
    && /opt/venv/bin/python -m pip uninstall --yes pip

FROM python:3.12-alpine@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4 AS runtime

WORKDIR /app
# Package installation is completed in the build stage. Do not ship pip's
# bundled dependencies or ensurepip's installer wheel in the runtime image.
RUN apk --no-cache upgrade \
    && apk add --no-cache libstdc++ \
    && python -m pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python3.12/ensurepip
ENV PATH="/opt/venv/bin:$PATH" \
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1
COPY --from=build /opt/venv /opt/venv

COPY app ./app
COPY auth ./auth
COPY models ./models
COPY schemas ./schemas
COPY scripts ./scripts
COPY tests ./tests
COPY pytest.ini ./pytest.ini
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

RUN addgroup -S appgroup && adduser -S -G appgroup appuser \
	&& mkdir -p /app/storage \
	&& chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3).read()"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
