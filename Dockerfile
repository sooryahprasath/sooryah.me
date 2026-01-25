# Stage 1: Build
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:stable-alpine
# Remove default static files
RUN rm -rf /usr/share/nginx/html/*
# Copy fresh build from previous stage
COPY --from=build /app/dist /usr/share/nginx/html
# Copy your custom config
COPY default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]