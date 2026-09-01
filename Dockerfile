FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir $(python3 -c "import tomllib; t = tomllib.load(open('pyproject.toml', 'rb')); print(' '.join(t['project']['dependencies']))")

COPY . .
RUN pip install --no-cache-dir --no-deps .

ENTRYPOINT ["python3", "scripts/entrypoint.py"]
CMD ["duckbot"]
