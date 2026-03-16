# 基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY rag_service.py .

# 创建必要目录
RUN mkdir -p ./uploaded_docs ./chroma_db

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "rag_service:app", "--host", "0.0.0.0", "--port", "8000"]