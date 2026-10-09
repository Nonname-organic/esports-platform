# ベースイメージは AWS ECR Public の公式ミラーから取得する。
# Docker Hub は未認証だとIP単位で絞られ、GitHub のランナーはIPを共有するため
# 429 や auth.docker.io の 504 でビルドが落ちることが繰り返し起きた。
# ECR Public は同じ公式イメージを認証不要・レート制限なしで配る。
FROM public.ecr.aws/docker/library/python:3.12-slim

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
