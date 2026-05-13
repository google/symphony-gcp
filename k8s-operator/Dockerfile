# Dockerfile
FROM python:3.13-alpine3.23 AS builder

WORKDIR /app

# Copy pyproject.toml and poetry.lock
COPY pyproject.toml README.md .
COPY src ./src
COPY build_scripts ./build_scripts

# Accept VERSION build argument and update __init__.py
ARG VERSION
ENV VERSION=$VERSION
RUN if [ -n "$VERSION" ]; then \
        sed -i  "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" src/gcp_symphony_operator/__init__.py; \
    fi

# Install uv and build the wheel
RUN pip install --no-cache-dir uv && \
    uv build --wheel --out-dir=dist .

# Create a new stage for the final image
FROM python:3.13-alpine3.23

LABEL org.opencontainers.image.source=https://github.com/google/symphony-gcp
LABEL org.opencontainers.image.description="A kubernetes operator for Google GKE and IBM Spectrum Symphony host factory"
LABEL org.opencontainers.image.licenses="Apache 2.0"
LABEL org.opencontainers.image.authors="Accenture, LLC"

WORKDIR /app

# Copy the wheel file from the builder stage
COPY --from=builder /app/dist/*.whl /app/

# Install the package from the wheel file
RUN pip install --no-cache-dir /app/*.whl && \
    rm /app/*.whl

# Copy the entrypoint
# COPY run.py .
COPY gcp_symphony_operator.run .

ENV PATH="/app:${PATH}"

ENTRYPOINT ["python", "gcp_symphony_operator.run"]
CMD []