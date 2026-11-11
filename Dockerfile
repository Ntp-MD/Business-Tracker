FROM mcr.microsoft.com/playwright/python:v1.64.1-jammy

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=10000

COPY server.py db.py pw_login.py ./
COPY index.html ./
COPY live ./live
COPY app ./app
COPY assets ./assets

EXPOSE 10000
CMD ["python", "server.py"]
