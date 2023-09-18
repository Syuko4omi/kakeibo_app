# ☕︎ MOCA (Monthly Otakatsu Cash Administrator)
* 月々の出費を管理するWebアプリ
* 普段利用するサービスに対し、一ヶ月いくらまで使っても良いかを自分で設定し、今月の使用金額がそれを上回っていないかどうかを確認できる

## アプリの起動
app.pyがあるディレクトリで以下を実行すると、http://127.0.0.1:5000 でアプリが起動する。
```
poetry run python3 app.py
```

## 機能
### a. トップ画面
* 登録したサービスの上限金額と、現在の使用金額をプログレスバーで確認できる。また、サービス全体でも確認可能。
    * 使用金額が上限金額の80%ならプログレスバーの色は緑色になる。80%以上100%未満なら黄色、100%以上だと赤色になる。
![image](https://github.com/Syuko4omi/kakeibo_app/assets/50670279/37f56e8c-d23d-4005-aea1-a131af0db761)

### b. サービス
* 画面上部の「登録済みサービス一覧」から、今月分の出費を記録したいサービスの登録・確認・上限金額変更・削除が可能。
![image](https://github.com/Syuko4omi/kakeibo_app/assets/50670279/162fa22a-eabf-4ab8-b7d2-3c4d84215060)
![image](https://github.com/Syuko4omi/kakeibo_app/assets/50670279/8db93517-d789-4926-8826-172b22d42253)
* また、トップ画面の各サービスのエリアにある「詳細を見る」ボタンを押せば、各月の購入履歴や使用金額が見られる。
![image](https://github.com/Syuko4omi/kakeibo_app/assets/50670279/f7388c97-867f-47de-bdfa-c4e06c655850)

### c. 商品
* 画面上部の「商品登録」から、商品の登録が可能。注意として、商品を購入したサービスは登録済みのサービスからしか選べないので、先にサービス名と上限金額を 画面上部の「登録済みサービス一覧」から登録したのち、商品を登録しなければならない。
![image](https://github.com/Syuko4omi/kakeibo_app/assets/50670279/637aeafd-6b94-4355-94e3-2cda842c17e6)
* 登録した商品の情報を変更・削除する場合、トップ画面の各サービスのエリアにある「詳細を見る」ボタンを押し、画面下部の商品テーブルの右側にあるリンクから行える。
![image](https://github.com/Syuko4omi/kakeibo_app/assets/50670279/f04d6910-b2ef-4637-85a0-35dbdc98d932)


### d. 履歴
* 使用金額の合計と、上限金額の合計を表示する。これまでにいくら節約できたのか、また浪費したのかを可視化する。
![image](https://github.com/Syuko4omi/kakeibo_app/assets/50670279/a9b65b6e-548a-46b8-87cc-34f85fa6fbfe)
* 「節約したお金を使う」ボタンを押せば、節約したお金を他の用途に使用した場合、それを登録することができる。内容の閲覧・変更・削除も可能。
![image](https://github.com/Syuko4omi/kakeibo_app/assets/50670279/12cb2b27-a3a5-4e85-8a73-f62bebd8ef15)


## 構成
* 言語：Python
* アプリケーションフレームワーク：Flask
* CSSフレームワーク：BootStrap
    * テンプレートエンジン：Jinja
* データベース：SQlite


## 改良案
* ORマッパー（SQLAlchemy）を用いて、SQL文をソースコードに書かないようにする
* app.pyの可読性が低いので、Flask Blueprintを使ってモジュール分割を行う
* アカウントに関連する諸機能を追加する
    * アカウント登録
    * ログイン
    * アカウント変更・削除
