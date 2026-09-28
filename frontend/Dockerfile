# ============================================
# 前端：多阶段构建 → Nginx 静态站 + 反代 API/WS
# ============================================
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
# 若有 lock 文件可取消下行注释以锁定版本
# COPY package-lock.json ./
RUN npm install

COPY . .
# 同源部署：WS 走当前域名，由 Nginx 反代到后端
ENV VITE_WS_BASE_URL=
RUN npm run build || npx vite build

# ---- 运行镜像 ----
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://127.0.0.1/ || exit 1
