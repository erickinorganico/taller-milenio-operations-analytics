FROM python:3.12-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 milenio \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin milenio
COPY requirements-web.txt ./
RUN pip install --no-cache-dir --only-binary=:all: -r requirements-web.txt && pip check
COPY manage.py ./
COPY milenio_web milenio_web
COPY workshop workshop
COPY commercial commercial
COPY scripts scripts
COPY infra/nube/import_windows.py infra/nube/import_windows.py
ARG MILENIO_BUILD_REVISION=local-test
LABEL org.opencontainers.image.revision=$MILENIO_BUILD_REVISION
USER 10001:10001
CMD ["python", "scripts/cloud_app.py", "serve"]
