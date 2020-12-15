# prescription

#　アクセスするページ
http://3.131.61.197:5000/
```
ozone
52.15.67.215:5000
yarai
18.222.116.212:5000
yamazaki
3.136.236.117:5000
demo（これまで使っていたファイル）
3.133.155.103:5000

s3からのダウンロード
aws s3 sync s3://medistorage/yarai_server/2020-12-04 .
```
## EC2上にmasterブランチを反映/runさせるためのコマンド群

```
ターミナル上からEC2にssh接続する
[新IP from 2020.11.11]
ssh -i <秘密鍵のパス> <user_name>@3.131.61.197

[旧IP]
ssh -i <秘密鍵のパス> <user_name>@18.221.19.223

EC2上にてユーザを変更する ... sudo権限を付与してもらっていないとこれ出来ないことに注意.
sudo su - ec2-user
pass: mediLab0319

該当ディレクトリに移動し、pullを行う
cd prescription (prescription-testではない)
git pull origin master   (河野のgithubの公開鍵をawsに持たせているので僕のgithubから引用されます。)

app.runのホストが0.0.0.0に指定されていることを確認する.なっていなかったら手動で直す.
vim main.py
>> if __name__ == '__main__':
>>   app.run(debug=True, host='0.0.0.0')

appをrunさせる ... nohupをしないと, ターミナルを落とした際にEC2上のappも落ちる.
nohup python3 main.py（pythonではなくpython3）
※ デバグ時等リアルタイムでターミナル上でシステムの挙動を見たいときは python3 main.py がオススメ
```

#### 上記で"address is already in use"と出た場合 -> 過去走らせたpython3 main.py コマンドが動いていることが多い
```
# 以下の2つのコマンドを用いて, 過去にpython3 main.pyを叩いているIDを特定
# ... pyenv~~ みたいなコマンドを直近で叩いているIDを見つける
ps r
ps aux

# IDをkillする
kill <ID>

#再度実行
nohup python3 main.py （うまくいかなかったらほかのIDをKILLする）
```

#### 実行確認
```
http://18.221.19.223:5000 へアクセス
```


#### ログを取りながら実行したいとき

```
python3 main.py > log.txt(任意のテキストファイル)
```
※ そのうち、デフォルトでログを取れるようにコードを改変するつもり。


## ローカルでの環境構築

以下の手順を実行する
※松田が2020/5/2にOS,pythonをクリーンインストールした際の手順。<br>
おそらく十分性が高いもの。

```
##環境:
#host os: windows10
#virtual soft: Virtual Box 6.1
#guest os: ubuntu 18.04 LTS ... メモリ8GB, ストレージ60GB(固定)

##pythonのバージョン確認
python3 --version
>>Python 3.6.9

##python3のpip等環境構築
git clone https://github.com/taichiobara/prescription
sudo apt install python3-pip
sudo pip3 install --upgrade pip
sudo apt install python3-venv

##2020/5/2時点でgithubに置いてあるrequirements.txtをインストール.その際mecabは下準備が必要。
##参照: https://mojitoba.com/2019/01/29/solve-error-installation-mecab-python3/
sudo apt install mecab
sudo apt install libmecab-dev
sudo apt install mecab-ipadic-utf8
sudo apt autoremove
pip3 install -r requirements.txt

##小原がreadme.mdにて指摘していた追加パッケージinstall
pip3 install opencv-python
pip3 install git+https://github.com/miurahr/pykakasi
pip3 install nltk

##import cv2にてエラーが出る場合、以下のコマンドを実行
##参照 https://anton0825.hatenablog.com/entry/2017/01/09/000000
sudo yum install -y mesa-libGL.x86_64

##追加で必要と言われたsymspellpy, バージョン古すぎと言われたxlrdをinstall
pip3 install symspellpy
pip3 install xlrd

##5/8に追加したパッケージをインストール
pip3 install python-Levenshtein

##β版サービス最終化に際して、追加したパッケージをインストール
pip3 install janome

##動作確認
python3 main.py
```

FYI:<br>
現状(2020/4/30)のawsの環境。
[aws_requirements.txt](https://github.com/taichiobara/prescription/files/4551294/aws_requirements.txt)<br>

## ローカルでの実行方法

トップの階層において、

```
python main.py
```

でローカルサーバーが立ち上がる。

画像送信画面[http://127.0.0.1:5000/](http://127.0.0.1:5000/) <br>
→修正画面[http://127.0.0.1:5000/result](http://127.0.0.1:5000/result)<br>
→QRコード表示画面[http://127.0.0.1:5000/qrcode](http://127.0.0.1:5000/qrcode)<br>
→画像送信画面[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## .uploadsのS3バックアップ方法 via S3
```
（EC2-userでprescriptionに移動する）

aws s3 sync upload s3://medistorage/20201118(※1 日にちが最適か)

S３のコンソールに飛ぶ　https://s3.console.aws.amazon.com/s3/home?region=ap-northeast-1#

medistorage をクリック

アップロードしたファイル（この場合20201118）が存在することを確認

ファイルを一つ一つ開き、オブジェクトアクションからダウンロードする　
（最適化の余地あり。ディレクトリごとダウンロードする方法：https://hacknote.jp/archives/57148/）

(※２　ダウンロードしたファイルはEC2から削除する。)

```

## コードの全体構造
### .py files
|ファイル名|概要|
|-------|----------|
|main.py |サーバ上でrunさせておく, main処理|
|preprocessing_and_OCR.py |フロントより受け取った画像情報を前処理した上で、visionAPIにてOCRする処理|
|recieve_info.py |フロントより情報を受け取り、それをpython上で扱えるnp.arrayの形に変換する処理. preprocessing_and_OCR.py内にて使用|
|ocr_request.py |visionAPIへのリクエストを行うための諸処理. preprocessing_and_OCR.py内にて使用|
|basic_info.py |OCR結果の生文字列群より、患者基本情報をパースする処理|
|med_info.py |OCR結果の生文字列群より、医薬品情報をパースする処理|
|med_info_def_res.py |医薬品用法用量を取得するための正規表現を定義する処理. med_info.py内にて使用|
|make_qr.py |OCR->文字列パースによって取得された処方箋の情報を受け, JAHIS規格に成形・QRコード化する処理|
|create_msg.py |フロントに読取結果を表示するために必要な情報を作成するための処理|
※python file内の各関数の詳細は、関数直下のコメントを参照してください

<br>

# 以下、OLD CONTENTS

### 現状うまく動くことが確認されている処方箋画像

[PHCサンプル](https://user-images.githubusercontent.com/42126369/80725875-9e66ec80-8b3e-11ea-8a3f-580305a73014.png)

### ファイルの構造説明

main.pyが一番大事なファイルで、全体の流れが書いてあります。<br>main.pyの中でvision1.pyの中の関数を取ってきながら処理を進めている感じ。<br>
main.pyの中に「〜〜というURLでアクセスされたら〜〜という処理をする」ということが書かれています。

|ファイル名|役割|
|-------|----------|
| .ipynb_checkpoints | 無関係 |
| __pycache__ |自然に生成されるやつ|
| static |cssファイルやｊｓファイル置き場|
| templates| htmlファイル置き場|
| uploads |写真置き場|
| notebook_and_rawData |システムのDB,parameterチューニング手順書のipynb & その入力となるデータ置き場|
| .DS_Store |無関係|
|df_medicineInfo.pickle|一般名・品名の両方の医薬品名DB|
|df_medicineInfo_ippan.pickle|一般名のみの医薬品名DB|
|df_medicineInfo_specific.pickle|品名のみの医薬品名DB|
|dict_hospitalInfo.pickle|関東信越の病院名・コードDB|
|dict_hospitalInfo_sub.pickle|関東信越の病院のうち、2つのコードを持つやつのsubの方のコードDB|
|medicine4_10.pickle |symspellで使ってる薬品データ|
|hospital3_10.joblib |symspellで使ってる病院データ.joblibにて圧縮.|
|my_classifier.pickle|カナ氏名から性別判断するのに使う|
|requirements.txt |環境構築に必要なデータ（正しいかは確認必要）|
|main.py |これがメイン|
|test.html |無関係|
|vision1.py |関数置き場|


## vision1.pyの関数一覧（一番右に出力が見切れていることに注意）

|関数名|機能 &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;|引数|戻り値|
|--|--|--|--|
|yugami|輪郭を取り出して画像の歪みを補正|画像のpath|歪み補正後の画像|
|waku|処方箋画像から必要な領域のみを切り出す|画像のarray|保険者番号部分,記号・番号,基本情報部分,医薬品情報部分の左,医薬品情報部分の右,保険者番号部分をそのまま取ってきたもの|
|waku1|waku関数が失敗した処方せんからの切り出しを行う|同上|同上|
|recognize_image1|画像を文字起こし|画像のarray|text|
|recognize_image2|画像から縦線を消して文字起こし（保険者番号用）|画像のarray|text|
|text_processing_basic|基本情報の読み取り|text|リスト|
|extract_name|文字列から名前部分を抽出|text|text|
|kanji_name|氏名を抽出|text|text|
|kana_name|漢字をカタカナにする|漢字|カタカナ|
|symbol_num|記号番号をidとnumに分ける（複数通り提示）|text|id,num|
|symbol_num2|記号番号をidとnumに分ける（複数通り提示）|text|id,num|
|symspell|薬名に名寄せ|text,どこまで間違いを許容するか（最大4）|候補名のリスト,候補名それぞれのもとのtextからの距離|
|text_processing_med|薬品情報を抽出|text|薬1の辞書,薬2の辞書,薬3の辞書,薬4の辞書,薬5の辞書,薬6の辞書,薬7の辞書,薬8の辞書,薬9の辞書,薬10の辞書|
|list2str|用法、用量のリストを正規表現で使える形に変換する処理|リスト,数字,曜日|text|
|update_RPNum|txtの中の文字列に応じて、更新されたRP番号を返す処理（調剤数量の文字列がそこに存在するか否か, 用法の文字列がそこに存在するか否か、の2点で判定）|RP_num,RP_renbanNum,txt,l1=l_chozaiNum_units,l2=l_youhou|RP番号,RP番号内連番|
|func_101|101_剤形レコードに関連する情報(剤形区分・調剤数量)と思われる文字列を返す|txt,l=l_chozaiNum_units,df=df_medicineInfo|数量|
|func_101_2|101_剤形レコードに関連する情報(剤形区分・調剤数量)と思われる文字列を返す|med,df=df_medicineInfo|kubun_num|
|func_111|文字列ブロックを入力として、111_用法レコードに関連する情報(用法)と思われる文字列を返す|txt,l=l_youhou|（あれば）用法|
|func_201|201_薬品レコードの情報(医薬品コード種別・医薬品コード・用量・単位)を返す|txt,med,l=l_youryou_units,df=df_medicineInfo|med_codeType,med_code,youryou_num,unit|
|func_281|ジェネリック医薬品変更可否を表すboolを入力とし、変更不可な場合はそれを表すJAHIS用の2次元listを返す|bool|リスト|
|convert_days|XX年XX月XX日の形のstringを受取、genngouにて表された元号番号を添えてJAHIS規格で返す処理|text,元号|text|
|type_check|処方箋が一段組(A)or２段組(B)かを判定|画像のarray|AorB|
|jp2rome|日本語（カタカナ）をローマ字に|text|text|
|feature_extraction|後ろ3文字を取り出す関数|text|text|
|kata2gender|カタカナの氏名から性別を推定する関数|text|text（男or女）|

vision1.py以外のページで上の関数を使うには、「v1.関数名」で使える。（ページの最初でvision1をv1と定義しているから）


## Pull requestのやり方
[松田さんからのおすすめ記事](https://qiita.com/samurai_runner/items/7442521bce2d6ac9330b)<br>
[良いプルリクのやり方](https://gist.github.com/koudaiii/77ab8eb30512978d1122)
- なるべく細かくプルリクする
- 関係ないファイル入れないようにフォルダの中身には気を付ける
- 題名はわかりやすいものがよい（簡潔出なくて長くても全然OK）
- コメントも大歓迎
- コード中のコメントアウトはたくさんつけてもらえると嬉しい。
