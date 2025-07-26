# 使用官方的 Python 基礎映像
FROM python:3.9-slim-buster

# 設定工作目錄
WORKDIR /app

# 複製依賴文件並安裝
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式程式碼
COPY . .

# 設定環境變數 (在 Cloud Run 中部署時，這些會被覆蓋)
ENV PORT=8080

# 暴露應用程式將監聽的埠
EXPOSE 8080

# 啟動應用程式
# main:app 指的是 main.py 檔案中的 FastAPI 應用實例 'app'
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]