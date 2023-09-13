from flask import Flask, render_template, request, redirect, g
import datetime
import sqlite3

DATABASE = "kakeibo.db"
app = Flask(__name__)


def connect_db():  # データベースとの接続を確立する部分
    rv = sqlite3.connect(DATABASE)  # rvに接続を格納する
    # row_factoryにsqlite3.Rowを設定することで、SELECTを使って返るものがタプルではなくsqlite3.Rowオブジェクト（辞書のようなもの）になる
    # そのため、ret.idやret.title、ret.bodyといった形でメモの中身にアクセスすることができるようになる
    # https://stackoverflow.com/questions/44009452/what-is-the-purpose-of-the-row-factory-method-of-an-sqlite3-connection-object
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    # gオブジェクトはグローバル変数で、DBのデータを保存するために使われる
    # gオブジェクトは、1回のリクエスト（ユーザーがWebページからFlaskアプリへ要求すること）ごとに個別なものになる
    # gオブジェクトは、リクエストの（処理）期間中は複数の関数によってアクセスされるようなデータを格納するために使われる
    # DBとの接続はgオブジェクトに格納されて、もしも同じリクエストの中でget_dbが2回呼び出された場合、新しい接続を作成する代わりに、再利用される
    if not hasattr(g, "sqlite_db"):  # もしgが"sqlite_db"属性でない＝まだDBに接続していないようなら、データベースと接続する
        g.sqlite_db = connect_db()
    return g.sqlite_db  # これで一時的にDBとの接続を保存する。これに対してSQL文を投げる


@app.route("/")
def top():  # トップ画面を表示
    # 年と月を取得
    tokyo_tz = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.now(tokyo_tz)
    year = str(dt.year)
    month = "{:02}".format(dt.month)
    yyyymm = year + "-" + month

    db = get_db()  # 接続を確立
    service_detail_list = db.execute(
        "select * from service where year_month = ?", [yyyymm]
    ).fetchall()  # これがsqlite3.Rowオブジェクトが入ったリストになっている

    if service_detail_list != []:  # テーブルにサービスが登録されていた場合の処理
        item_detail_list = db.execute(
            "select * from item where purchase_date like ?", [yyyymm + "%"]
        ).fetchall()  # 該当の月に買った商品
        expense_for_each_service = {}
        for service_detail in service_detail_list:
            expense_for_each_service[service_detail["service_name"]] = 0
        for item in item_detail_list:
            expense_for_each_service[item["service_name"]] += item["item_price"]
        service_detail_list_with_each_data = []
        for service_detail in service_detail_list:
            service_name = service_detail["service_name"]
            upper_limit = service_detail["upper_limit"]
            current_usage = expense_for_each_service[service_name]
            usage_ratio = round((current_usage * 100 / upper_limit), 1)
            text_style_usage_ratio = f"width:{usage_ratio}%"
            usage_ratio_with_percent = f"{usage_ratio}%"

            service_detail_list_with_each_data.append(
                {
                    "service_name": service_name,
                    "current_usage": current_usage,
                    "upper_limit": upper_limit,
                    "text_style_usage_ratio": text_style_usage_ratio,
                    "usage_ratio_with_percent": usage_ratio_with_percent,
                }
            )

        total_current_usage = sum(
            [expense for expense in expense_for_each_service.values()]
        )
        total_upper_limit = sum(
            [service_detail["upper_limit"] for service_detail in service_detail_list]
        )
        total_usage_ratio = round((total_current_usage * 100 / total_upper_limit), 1)
        text_style_total_usage_ratio = f"width:{total_usage_ratio}%"
        total_usage_ratio_with_percent = f"{total_usage_ratio}%"

        return render_template(
            "index.html",
            year=dt.year,
            month=dt.month,
            total_upper_limit=total_upper_limit,
            total_current_usage=total_current_usage,
            text_style_total_usage_ratio=text_style_total_usage_ratio,
            total_usage_ratio_with_percent=total_usage_ratio_with_percent,
            # service_detail_list=service_detail_list,
            service_detail_list=service_detail_list_with_each_data,
        )
    else:  # 今月分のサービスが登録されていなかった場合
        is_service_exist = db.execute("select * from service").fetchone()
        if is_service_exist != []:  # 以前にサービスが登録されていた場合
            newest_service = db.execute(
                "select * from service where service_id = (select max(service_id) from service)"
            ).fetchone()
            most_recent_day_recorded = newest_service["year_month"]
            service_detail_list = db.execute(  # 直近の月で使っていたサービスを選ぶ
                "select * from service where year_month = ?", [most_recent_day_recorded]
            )
            service_detail_list_with_each_data = []
            for service_detail in service_detail_list:  # 上限は前の時と据え置き
                service_name = service_detail["service_name"]
                upper_limit = service_detail["upper_limit"]
                current_usage = 0
                usage_ratio = round((current_usage * 100 / upper_limit), 1)
                text_style_usage_ratio = f"width:{usage_ratio}%"
                usage_ratio_with_percent = f"{usage_ratio}%"

                service_detail_list_with_each_data.append(
                    {
                        "service_name": service_name,
                        "current_usage": current_usage,
                        "upper_limit": upper_limit,
                        "text_style_usage_ratio": text_style_usage_ratio,
                        "usage_ratio_with_percent": usage_ratio_with_percent,
                    }
                )

                db.execute(  # dbにデータを登録
                    "insert into service (year_month, service_name, upper_limit) values (?, ?, ?)",
                    [yyyymm, service_name, upper_limit],
                )
                db.commit()

            total_current_usage = 0
            total_upper_limit = sum(
                [
                    service_detail["upper_limit"]
                    for service_detail in service_detail_list_with_each_data
                ]
            )
            total_usage_ratio = round(
                (total_current_usage * 100 / total_upper_limit), 1
            )
            text_style_total_usage_ratio = f"width:{total_usage_ratio}%"
            total_usage_ratio_with_percent = f"{total_usage_ratio}%"

            return render_template(
                "index.html",
                year=dt.year,
                month=dt.month,
                total_upper_limit=total_upper_limit,
                total_current_usage=total_current_usage,
                text_style_total_usage_ratio=text_style_total_usage_ratio,
                total_usage_ratio_with_percent=total_usage_ratio_with_percent,
                service_detail_list=service_detail_list_with_each_data,
            )
        else:  # 初めてサービスを使う場合
            return render_template(
                "index.html",
                year=dt.year,
                month=dt.month,
                total_current_usage=0,
                total_upper_limit=0,
                text_style_total_usage_ratio="width:0%",
                total_usage_ratio_with_percent="-",
                service_detail_list=service_detail_list,
            )


# ここからサービス画面
@app.route("/service_detail")
def show_registered_services():  # 登録したサービスの一覧を表示
    db = get_db()  # 接続を確立
    service_detail_list = db.execute(
        "select * from service"
    ).fetchall()  # これがsqlite3.Rowオブジェクトが入ったリストになっている
    return render_template(
        "service_detail.html", service_detail_list=service_detail_list
    )


@app.route("/service_register", methods=["GET", "POST"])
def register_new_service():  # 新しいサービスを登録する
    if request.method == "POST":  # 登録ボタンが押された場合の処理
        # request.form.getで得られるのは全部str型
        service_name = request.form.get("service_name")  # 画面から送られてきたサービス名
        upper_limit = request.form.get("upper_limit")  # 画面から送られてきたサービスの使用上限金額
        tokyo_tz = datetime.timezone(datetime.timedelta(hours=9))
        dt = datetime.datetime.now(tokyo_tz)
        year = str(dt.year)
        month = "{:02}".format(dt.month)
        yyyymm = year + "-" + month
        db = get_db()
        is_existed_service = db.execute(  # 既に同じ名前のサービスが登録されているかどうかを確認
            "select service_name from service where service_name = ? and year_month = ?",
            [service_name, yyyymm],
        ).fetchall()

        # 同名のサービスがある場合・入力が空欄の場合のエラーキャッチ
        if is_existed_service:
            return render_template(
                "service_register.html", error_message="同じ名前のサービスが既に存在しています"
            )
        if service_name == "" or upper_limit == "":
            return render_template(
                "service_register.html", error_message="サービス名もしくは使用上限金額が空欄です"
            )

        # ここからDBに登録する処理
        register_body = {
            "service_name": service_name,
            "current_usage": 0,
            "upper_limit": upper_limit,
            "usage_ratio": 0.0,
            "text_style_usage_ratio": "width:0.0%",
            "usage_ratio_with_percent": "0.0%",
        }
        statement = "".join(
            [
                "insert into service (",
                ", ".join("`" + key + "`" for key in register_body.keys()),
                ") values (",
                ", ".join(["?"] * len(register_body)),
                ")",
            ]
        )  # db.execute("insert into memo (title, body) values (?,?)", [service_name, body])みたいな形式
        db.execute(statement, [value for value in register_body.values()])
        db.commit()  # BEGINは暗黙的に行われるので、変更はcommitするだけで良い
        return redirect("/service_detail")  # DBに新たなサービスを入れたら、TOP画面に戻る
    return render_template("service_register.html", error_message="")


@app.route("/<service_name>/service_edit", methods=["GET", "POST"])
def edit_service(service_name):  # サービスの上限金額を編集する
    if request.method == "POST":
        service_name = request.form.get("service_name")  # 画面から送られてきたサービス名
        upper_limit = request.form.get("upper_limit")  # 画面から送られてきたサービスの使用上限金額

        # 入力が空欄の場合のエラーキャッチ
        if upper_limit == "":
            db = get_db()
            post = db.execute(
                "select service_name, upper_limit from service where service_name = ?",
                [
                    service_name,
                ],
            ).fetchone()
            return render_template(
                "service_edit.html", error_message="使用上限金額が空欄です", post=post
            )

        # DBに上書き登録する処理
        db = get_db()
        db.execute(
            "update service set upper_limit = ? where service_name = ?",
            [upper_limit, service_name],
        )
        db.commit()
        return redirect("/service_detail")  # DBの情報を編集したら、TOP画面に戻る
    db = get_db()
    post = db.execute(
        "select service_name, upper_limit from service where service_name = ?",
        [
            service_name,
        ],
    ).fetchone()
    return render_template("service_edit.html", error_message="", post=post)


@app.route("/<service_name>/service_delete", methods=["GET", "POST"])
def delete_service(service_name):  # 登録されているサービスを削除する
    if request.method == "POST":
        service_name = request.form.get("service_name")  # 画面から送られてきたメモのタイトル

        # DBからサービスを削除する
        db = get_db()
        db.execute(
            "delete from service where service_name = ?",
            [
                service_name,
            ],
        )
        db.commit()  # BEGINは暗黙的に行われるので、変更はcommitするだけで良い
        return redirect("/service_detail")  # DBからサービスを削除したら、TOP画面に戻る
    db = get_db()
    post = db.execute(
        "select service_name, upper_limit from service where service_name = ?",
        [
            service_name,
        ],
    ).fetchone()
    return render_template("service_delete.html", post=post)


# ここから商品画面
@app.route("/<service_name>/item_detail")
def show_registered_items(service_name):  # 登録した商品の一覧を表示
    tokyo_tz = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.now(tokyo_tz)
    year = str(dt.year)
    month = "{:02}".format(dt.month)
    query_ym = year + "-" + month + "%"
    db = get_db()  # 接続を確立
    item_detail_list = db.execute(  # ここでサービスを一意に特定する
        "select * from item where purchase_date like ? and service_name = ?",
        [
            query_ym,
            service_name,
        ],
    ).fetchall()  # これがsqlite3.Rowオブジェクトが入ったリストになっている"""
    return render_template("item_detail.html", item_detail_list=item_detail_list)


@app.route("/item_register", methods=["GET", "POST"])
def register_new_item():  # 新しいサービスを登録する
    if request.method == "POST":  # 登録ボタンが押された場合の処理
        # request.form.getで得られるのは全部str型
        purchase_date = request.form.get("purchase_date")  # 画面から送られてきた購入日 2023-09-01とか
        service_name = request.form.get("service_name")  # 画面から送られてきたサービス名
        item_name = request.form.get("item_name")  # 画面から送られてきた商品名
        item_price = request.form.get("item_price")  # 画面から送られてきた商品の金額
        item_attribute = request.form.get("item_attribute")  # 画面から送られてきた商品の属性
        db = get_db()
        is_existed_item = db.execute(  # 既に同じ名前の商品が同じサービスで購入されているかどうかを確認
            "select service_name, item_name from item where service_name = ? and item_name = ?",
            [
                service_name,
                item_name,
            ],
        ).fetchall()
        service_detail_list = db.execute(  # ここでサービスを一意に特定する
            "select * from service"
        ).fetchall()

        # 同じ商品が同じサービスで購入されている場合・入力が空欄の場合のエラーキャッチ
        if is_existed_item:
            return render_template(
                "item_register.html",
                error_message="同じ名前の商品がこのサービスで既に購入されています",
                service_detail_list=service_detail_list,
            )
        blank_input = [
            entry == ""
            for entry in [
                purchase_date,
                service_name,
                item_name,
                item_price,
                item_attribute,
            ]
        ]
        if True in blank_input:
            return render_template(
                "item_register.html",
                error_message="全て入力してください",
                service_detail_list=service_detail_list,
            )

        # ここからDBに登録する処理
        register_body = {
            "purchase_date": purchase_date,
            "service_name": service_name,
            "item_name": item_name,
            "item_price": item_price,
            "item_attribute": item_attribute,
        }
        statement = "".join(
            [
                "insert into item (",
                ", ".join("`" + key + "`" for key in register_body.keys()),
                ") values (",
                ", ".join(["?"] * len(register_body)),
                ")",
            ]
        )  # db.execute("insert into memo (title, body) values (?,?)", [service_name, body])みたいな形式
        db.execute(statement, [value for value in register_body.values()])
        db.commit()  # BEGINは暗黙的に行われるので、変更はcommitするだけで良い
        return redirect(f"/{service_name}/item_detail")  # DBに新たなサービスを入れたら、商品登録画面に戻る

    db = get_db()  # 接続を確立
    service_detail_list = db.execute(  # ここでサービスを一意に特定する
        "select * from service"
    ).fetchall()
    return render_template(
        "item_register.html", error_message="", service_detail_list=service_detail_list
    )


app.run()
