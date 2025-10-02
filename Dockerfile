# 1. ベースイメージの指定
# 安定した環境のために、Python 3.10 のスリム版を使用します。
FROM python:3.10-slim

# 2. MeCabのシステム依存関係をインストール
# mecab, libmecab-dev, mecab-ipadic-utf8 は、MeCab本体と日本語辞書をシステムに導入します。
RUN apt-get update && apt-get install -y \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    && rm -rf /var/lib/apt/lists/*

# 3. ワーキングディレクトリを設定
# コンテナ内の作業ディレクトリを /app に設定します。
WORKDIR /app

# 4. Python依存関係のインストール
# requirements.txt を先にコピーし、インストールします。
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. アプリファイルをコピー
# app.py やその他のファイルをコンテナにコピーします。
COPY . .

# 6. アプリケーションの起動コマンドを設定
# アプリケーションのエントリーポイントを定義します。
CMD ["python", "app.py"]