※ Djangoコンテナ内で、と書いてある操作は原則manage.pyのあるディレクトリで実行すること

# 始め方
## docker, docker-composeをインストール
https://www.docker.com/products/docker-desktop

`docker-compose` は頻出するので.bashrcなどでaliasを作成しておくと楽
例: `alias dc='docker-compose'`

## dockerのイメージをビルド
ルートで`docker-compose build`

## コンテナ一括新規作成 & 一括起動
ルートで`docker-compose up`  
DB、Django、minio(S3互換のファイルストレージ)、Nginxが立ち上がる  
DjangoによるDBマイグレーション、adminユーザーの作成などの初期化が行われる  

### Djangoのadminサイトに入る
- email: admin@example.com
- password: prescription  
ログイン未実装のため、adminサイト(http://127.0.0.1/project-admin/)に入ることで、ログインする

### DjangoのWebサービスにアクセス
ブラウザでhttp://127.0.0.1 を開く


# 開発時

## dockerコンテナに入る

- backend(Django)コンテナに入りたい時 
=> `docker-compose exec back bash`

- db(postgres)コンテナに入りたい時 
=> `docker-compose exec db bash`

- nginxコンテナに入りたい時 (あまりないと思うが)
=> `docker-compose exec nginx bash`


## Djangoで書いたコードを反映
- Pythonコード
Djangoのコンテナの中で`pkill gunicorn -HUP`  
pkill gunicorn でgunicornのプロセスをkillしつつ -HUP オプションで再起動  
(Djangoの開発時のmanage.py runserverでは書き換えごとに再起動を起こすが、本projectではjanome tokenizer等の読み込みが都度行われるのを避けるために、毎回反映させるためにkillする)

- staticファイル
Djangoのコンテナの中で`python manage.py collectstatic`  
このコマンドで、prescription_api内のstaticディレクトリのファイルがストレージ(ローカルならminio, 本番ならS3にアップロードされ、配信の準備が整う)

## DjangoのORM(DB操作)を通じて、DBを扱う
Djangoのコンテナの中で`python manage.py shell`  
ここでモジュールやモデルをインポートして、DBを操作できる(反映もされるので注意)  
例: 
```python
import prescription.models import Prescription
prescription = Prescription.objects.last() # 最新のprescriptionを取得
print(prescription.pharmacy.name) # そのprescriptionの紐づく薬局の名前を表示
```
参考: https://qiita.com/okoppe8/items/66a8747cf179a538355b

## minioへのアクセス
ブラウザでhttp://127.0.0.1:9000/ を開く
- minio_ACCESS_KEY=1234
- minio_SECRET_KEY=12345678  
この中身は、dockerのホストマシンのdocker/storage/data/と共有されている

## コンテナのログを見たい時
`docker-compose logs -f`

## コンテナ一括停止
`docker-compose down`

## コンテナ一括起動
`docker-compose start`


# リリース時

## コード変更時

### EC2マシンにpull
このレポジトリをgit pull(初回はclone)

### Staticファイルの変更時
Djangoのコンテナの中で`python manage.py collectstatic`

### Pythonコードの変更時
Djangoのコンテナの中で`pkill gunicorn -HUP`して既存のプロセスをkillかつ再起動


## 初回もしくは再起動時

### dockerのイメージをビルド
プロジェクトルートで`docker-compose -f docker-compose.production.yml build`  
DBはRDS、minioはS3が代替するので、起動しないようになっている

### .envファイルの置き換え
Djangoプロジェクトのenvファイルは開発用のものなので、本番用のものに置き換える  
ただし、本番用のものはAWSのシークレットキーなどを含むため、**Git管理下にはおかず、直接アップロードすること**

### docker-compose up
プロジェクトルートで`docker-compose -f docker-compose.production.yml up`

### gunicorn起動
Djangoのコンテナの中で`gunicorn config.wsgi:application --timeout 120 --bind 0.0.0.0:8083`

