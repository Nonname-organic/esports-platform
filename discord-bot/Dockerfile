FROM python:3.12-slim

WORKDIR /app

# 依存インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリコピー
COPY . .

# 非rootユーザー
RUN useradd -m -u 1001 botuser
USER botuser

CMD ["python", "bot.py"]
