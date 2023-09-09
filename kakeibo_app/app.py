from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def top():  # トップ画面を表示
    return render_template("index.html")


@app.route("/service_detail")
def show_registered_services():  # 登録したサービスの一覧を表示
    L = [{"service_name": "service_1", "upper_limit": 12000}]
    return render_template("service_detail.html", service_settings=L)


app.run()
