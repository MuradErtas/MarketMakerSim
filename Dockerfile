# One Railway service: static UI (nginx) + FastAPI on loopback (same as docker-compose networking, collapsed to one VM).
FROM node:20-alpine AS frontend-build
WORKDIR /f
COPY frontend/package.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app

COPY --from=frontend-build /f/dist /usr/share/nginx/html
COPY deploy/nginx.railway.conf /deploy/nginx.railway.conf
COPY deploy/start.sh /deploy/start.sh
RUN chmod +x /deploy/start.sh

EXPOSE 8080
CMD ["/deploy/start.sh"]
