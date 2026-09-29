FROM python:3.10-slim

WORKDIR /app

# Sao chép file requirements và cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn dashboard
COPY . .

# Expose port mặc định của Streamlit
EXPOSE 8501

# Chạy ứng dụng Streamlit
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
