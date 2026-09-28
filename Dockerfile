# ============================================
# 后端镜像：FastAPI + Playwright + FFmpeg
# ============================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TZ=Asia/Shanghai

WORKDIR /app

# 系统依赖：ffmpeg（视频合成）、CJK 字体、Playwright 运行库
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        fonts-noto-cjk \
        fonts-wqy-zenhei \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
        libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
        libasound2 libxshmfence1 libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Chromium（PPT 视频 HTML 渲染）
RUN playwright install --with-deps chromium || playwright install chromium

# 应用代码
COPY main.py .
COPY app/ ./app/
COPY prompts/ ./prompts/
COPY scripts/ ./scripts/

# 数据与日志目录（compose 挂载 volume）
RUN mkdir -p /app/data/chroma /app/logs /app/backups

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
