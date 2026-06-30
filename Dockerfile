# ===== Stage 1: 构建数据库 =====
FROM python:3.12-alpine AS builder
WORKDIR /app
COPY data/ ./data/
COPY import_data.py .
RUN python import_data.py && rm -rf data/ import_data.py

# ===== Stage 2: 最小运行时 =====
FROM python:3.12-alpine
WORKDIR /app

COPY --from=builder /app/regions.db .
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements.txt \
    && rm -rf /root/.cache

COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/

EXPOSE 5000
CMD ["python", "app.py"]
