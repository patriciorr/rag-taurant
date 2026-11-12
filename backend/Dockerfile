FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade 'pip>=26.2' 'setuptools>=84.1.0' \
    && pip install -r requirements.txt

COPY . .

RUN useradd --system --no-create-home app && chown -R app /app
USER app

EXPOSE 8000


# Railway injects PORT and needs HOST=:: because its private network is IPv6.
ENV HOST=0.0.0.0

CMD ["sh", "-c", "exec uvicorn main:app --host ${HOST} --port ${PORT:-8000}"]
