# Stage 1: Builder Stage
FROM python:3.11-slim AS builder

ARG APP_HOME=/app
# ARG BUILD_ENVIRONMENT="production"

WORKDIR ${APP_HOME}

# ENV BUILD_ENVIRONMENT=$BUILD_ENVIRONMENT

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runner Stage
FROM python:3.11-slim AS runner

WORKDIR /server

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# Copy executables from builder (important for streamlit command)
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/Dashboard.py"]
