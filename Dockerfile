FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib \
    URBANOMY_HOST=0.0.0.0
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY urbanomy_agent ./urbanomy_agent
COPY urbanomy_mcp ./urbanomy_mcp
RUN pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 urbanomy && mkdir -p /app/outputs \
    && chown -R urbanomy:urbanomy /app/outputs
USER urbanomy
EXPOSE 8080
CMD ["python", "-m", "urbanomy_agent"]
