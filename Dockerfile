FROM python:3.8

# 作業ディレクトリを/appに設定
WORKDIR /app

# 現在のディレクトリの内容をコンテナ内の/appにコピー
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# ポートの公開
EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]

# コンテナ起動時にapp.pyを実行
CMD ["python", "app.py"]