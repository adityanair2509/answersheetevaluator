FROM node:18-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
# Create the base directory expected by Vite's base config
RUN mkdir -p /usr/share/nginx/html/answersheetevaluator

# Copy the built assets into the base directory
COPY --from=builder /app/dist /usr/share/nginx/html/answersheetevaluator

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
