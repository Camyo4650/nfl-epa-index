FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json tsconfig.json ./
RUN npm ci
COPY src ./src
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html movement.html history.html playoffs.html styles.css /usr/share/nginx/html/
COPY --from=build /app/dist /usr/share/nginx/html/dist
EXPOSE 80
