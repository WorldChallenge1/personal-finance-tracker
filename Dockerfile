FROM astral/uv:python3.13-bookworm-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Create non-root user with specific UID/GID
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd -g ${USER_GID} appuser && \
    useradd -m -u ${USER_UID} -g ${USER_GID} -s /bin/bash appuser

WORKDIR /app

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Copy dependency files
COPY --chown=appuser:appuser pyproject.toml uv.lock* ./

# Install dependencies as root (system-wide)
RUN uv pip install --system -r pyproject.toml

# Copy project files with correct ownership
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]