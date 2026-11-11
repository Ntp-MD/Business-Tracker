FROM mcr.microsoft.com/playwright/python:v1.64.1-jammy

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=10000

COPY backend ./backend
COPY legacy ./legacy

EXPOSE 10000
CMD ["python", "backend/server.py"]
