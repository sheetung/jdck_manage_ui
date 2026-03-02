# 使用官方Python镜像作为基础镜像
FROM python:3.9-slim

# 安装系统依赖，包括ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件到工作目录
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露应用端口
EXPOSE 8080

# 运行应用
CMD ["python", "app.py"]