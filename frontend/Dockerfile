FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
ARG TARGETARCH
RUN npm ci && \
    if [ "$TARGETARCH" = "arm64" ]; then npm install --no-save @rollup/rollup-linux-arm64-musl; \
    elif [ "$TARGETARCH" = "amd64" ]; then npm install --no-save @rollup/rollup-linux-x64-musl; fi
COPY . .
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
