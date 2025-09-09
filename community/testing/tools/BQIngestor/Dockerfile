# Dockerfile
FROM python:3.13-slim AS builder

WORKDIR /app

# Copy pyproject.toml and poetry.lock
COPY pyproject.toml .
COPY README.md .
COPY src ./src

# Install uv and build the wheel
RUN pip install uv && \
    uv build --wheel --out-dir=dist .

# Create a new stage for the final image
FROM python:3.13-slim

WORKDIR /app

# Copy the wheel file from the builder stage
COPY --from=builder /app/dist/*.whl /app/

# Install the package from the wheel file
RUN pip install --no-cache-dir /app/*.whl

COPY app.run .

# Copy the entrypoint
# COPY run.py .
ENV PATH="/app:${PATH}"

ENTRYPOINT ["python", "app.run"]
CMD []
