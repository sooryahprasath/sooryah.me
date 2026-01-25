# Stage 1: Build
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
# Clean install to avoid version conflicts
RUN npm ci 
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:stable-alpine
# Clear any default Nginx content
RUN rm -rf /usr/share/nginx/html/*
# Copy fresh dist from build stage
COPY --from=build /app/dist /usr/share/nginx/html
# Copy your specific nginx config
COPY default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]