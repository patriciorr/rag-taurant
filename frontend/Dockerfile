FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:alpine

# Railway overrides PORT and BACKEND_URL; the DNS resolver is read from /etc/resolv.conf.
ENV PORT=8080 \
    BACKEND_URL=http://backend:8000 \
    NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    NGINX_ENVSUBST_FILTER='^(PORT|BACKEND_URL|NGINX_LOCAL_RESOLVERS)$'

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
EXPOSE 8080
