FROM python:3.11-slim

WORKDIR /app

# 安装 Python 依赖（pymysql 是纯 Python 驱动，无需系统库）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 云托管通过 PORT 环境变量注入端口，默认 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
