FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG DATABASE_URL
RUN if [ -n "$DATABASE_URL" ]; then \
        echo "Validating Alembic migrations are in sync with models..." && \
        alembic -x sqlalchemy.url="$DATABASE_URL" check || (echo "ERROR: Migrations out of sync. Run 'alembic revision --autogenerate' and upgrade before building." && exit 1); \
    else \
        echo "No DATABASE_URL provided, skipping migration check at build time"; \
    fi

ENV PYTHONPATH=/app

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]