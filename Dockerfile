FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir "."

COPY . .

EXPOSE 8001

CMD ["python", "-m", "smithery.server"]