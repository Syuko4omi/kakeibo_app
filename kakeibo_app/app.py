from flask import Flask, render_template, request, redirect, g
import sqlite3

from config import DATABASE, ITEM_ATTRIBUTE_LIST
from util import (
    get_current_yyyymm,
    is_there_empty_entry,
    get_total_usage_info,
    add_usage_info_to_service_detail,
)

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
    yyyymm = get_current_yyyymm()  # 年と月を取得
    db = get_db()  # 接続を確立
    service_detail_list = db.execute(  # 特定の年月のサービスを取得する
        "select * from service where year_month = ?", [yyyymm]
    ).fetchall()  # これがsqlite3.Rowオブジェクトが入ったリストになっている

    if service_detail_list != []:  # テーブルにサービスが登録されていた場合の処理
        item_detail_list = db.execute(
            "select * from item where purchase_date like ?", [yyyymm + "%"]
        ).fetchall()  # 該当の月に買った商品を全て抜き出す
        expense_for_each_service = {  # それぞれのサービスに対する出費が入る
            service_detail["service_name"]: 0 for service_detail in service_detail_list
        }
        for item in item_detail_list:  # 上限金額が設定されたサービスで買った商品のみ使用金額に加算する
            if item["service_name"] in expense_for_each_service:
                expense_for_each_service[item["service_name"]] += item["item_price"]

        service_detail_list_with_each_data = []
        # sqlite3.Rowオブジェクトをもとに、上限の何割使ったのかなどを計算した情報を格納した辞書型をリストに加える
        for service_detail in service_detail_list:
            service_detail_dict = add_usage_info_to_service_detail(
                service_detail, expense_for_each_service[service_detail["service_name"]]
            )
            service_detail_list_with_each_data.append(service_detail_dict)

        total_current_usage = sum(expense_for_each_service.values())
        total_upper_limit = sum(
            [service_detail["upper_limit"] for service_detail in service_detail_list]
        )
        total_usage_ratio = round((total_current_usage * 100 / total_upper_limit), 1)
        text_style_total_usage_ratio = f"width:{total_usage_ratio}%"
        total_usage_ratio_with_percent = f"{total_usage_ratio}%"

        return render_template(
            "index.html",
            year=yyyymm[:4],
            month=yyyymm[5:],
            total_upper_limit=total_upper_limit,
            total_current_usage=total_current_usage,
            text_style_total_usage_ratio=text_style_total_usage_ratio,
            total_usage_ratio_with_percent=total_usage_ratio_with_percent,
            service_detail_list=service_detail_list_with_each_data,
        )
    else:  # 今月分のサービスが登録されていなかった場合
        is_service_exist = db.execute("select * from service").fetchone()
        if is_service_exist != None:  # 以前にサービスが登録されていた場合
            newest_service = db.execute(
                "select * from service where service_id = (select max(service_id) from service)"
            ).fetchone()
            most_recent_day_recorded = newest_service["year_month"]
            service_detail_list = db.execute(  # 直近の月で使っていたサービスを選ぶ
                "select * from service where year_month = ?", [most_recent_day_recorded]
            )
            service_detail_list_with_each_data = []
            for service_detail in service_detail_list:  # 上限は前の時と据え置き
                service_detail_dict = add_usage_info_to_service_detail(
                    service_detail=service_detail, current_usage=0
                )
                service_detail_list_with_each_data.append(service_detail_dict)

                db.execute(  # dbにデータを登録
                    "insert into service (year_month, service_name, upper_limit) values (?, ?, ?)",
                    [
                        yyyymm,
                        service_detail_dict["service_name"],
                        service_detail_dict["upper_limit"],
                    ],
                )
                db.commit()
            total_upper_limit = sum(
                [
                    service_detail["upper_limit"]
                    for service_detail in service_detail_list_with_each_data
                ]
            )

            return render_template(
                "index.html",
                year=yyyymm[:4],
                month=yyyymm[5:],
                total_upper_limit=total_upper_limit,
                total_current_usage=0,
                text_style_total_usage_ratio=f"width:{0}%",
                total_usage_ratio_with_percent=f"{0}%",
                service_detail_list=service_detail_list_with_each_data,
            )
        else:  # 初めてサービスを使う場合
            return render_template(
                "index.html",
                year=yyyymm[:4],
                month=yyyymm[5:],
                total_current_usage=0,
                total_upper_limit=0,
                text_style_total_usage_ratio="width:0%",
                total_usage_ratio_with_percent="-",
                service_detail_list=service_detail_list,
            )


# ここからサービス画面
@app.route("/service_detail")
def show_registered_services():  # 登録したサービスの一覧を表示
    yyyymm = get_current_yyyymm()
    db = get_db()  # 接続を確立
    service_detail_list = db.execute(  # 登録したサービス一覧
        "select * from service where year_month = ?", [yyyymm]
    ).fetchall()
    return render_template(
        "service_detail.html", service_detail_list=service_detail_list
    )


@app.route("/service_register", methods=["GET", "POST"])
def register_new_service(error_message=""):  # 新しいサービスを登録する
    db = get_db()
    is_any_service_exists = db.execute(  # 既に同じ名前のサービスが登録されているかどうかを確認
        "select * from service"
    ).fetchone()
    if request.method == "POST":  # 登録ボタンが押された場合の処理
        # request.form.getで得られるのは全部str型
        service_name = request.form.get("service_name")  # 画面から送られてきたサービス名
        upper_limit = request.form.get("upper_limit")  # 画面から送られてきたサービスの使用上限金額
        yyyymm = get_current_yyyymm()
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
            "year_month": yyyymm,
            "service_name": service_name,
            "upper_limit": upper_limit,
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
    if is_any_service_exists is None:
        error_message = "サービスが登録されていません。まずは購入したサービスと、使用する上限金額を登録してください。"
    return render_template("service_register.html", error_message=error_message)


@app.route("/<service_name>/service_edit", methods=["GET", "POST"])
def edit_service(service_name):  # サービスの上限金額を編集する
    # 編集しようとしているサービスの内容を検索する
    db = get_db()
    yyyymm = get_current_yyyymm()
    post = db.execute(
        "select service_name, upper_limit from service where service_name = ? and year_month = ?",
        [service_name, yyyymm],
    ).fetchone()

    # 編集完了ボタンが押された時の処理
    if request.method == "POST":
        service_name = request.form.get("service_name")  # 画面から送られてきたサービス名
        upper_limit = request.form.get("upper_limit")  # 画面から送られてきたサービスの使用上限金額

        # 入力が空欄の場合のエラーキャッチ
        if upper_limit == "":
            return render_template(
                "service_edit.html", error_message="使用上限金額が空欄です", post=post
            )

        # DBに上書き登録する処理
        db.execute(
            "update service set upper_limit = ? where service_name = ? and year_month = ?",
            [upper_limit, service_name, yyyymm],
        )
        db.commit()
        return redirect("/service_detail")  # DBの情報を編集したら、TOP画面に戻る

    return render_template("service_edit.html", error_message="", post=post)


@app.route("/<service_name>/service_delete", methods=["GET", "POST"])
def delete_service(service_name):  # 登録されているサービスを削除する
    db = get_db()
    yyyymm = get_current_yyyymm()

    if request.method == "POST":
        service_name = request.form.get("service_name")  # 画面から送られてきたメモのタイトル

        # DBからサービスを削除する
        db.execute(
            "delete from service where service_name = ? and year_month = ?",
            [service_name, yyyymm],
        )
        db.commit()  # BEGINは暗黙的に行われるので、変更はcommitするだけで良い
        return redirect("/service_detail")  # DBからサービスを削除したら、TOP画面に戻る

    post = db.execute(  # 削除画面を表示するために対象のサービスの内容を取得
        "select service_name, upper_limit from service where service_name = ? and year_month = ?",
        [service_name, yyyymm],
    ).fetchone()
    return render_template("service_delete.html", post=post)


# ここから商品画面
@app.route("/<service_name>/<yyyymm>/item_detail")
def show_registered_items(service_name, yyyymm):  # 登録した商品の一覧を表示
    db = get_db()  # 接続を確立
    item_detail_list = db.execute(  # 特定のサービスについて、ある月に購入した商品全てを取得する
        "select * from item where purchase_date like ? and service_name = ?",
        [
            yyyymm + "%",
            service_name,
        ],
    ).fetchall()
    service_data = db.execute(  # 対象のサービスの内容を取得
        "select service_name, upper_limit from service where service_name = ? and year_month = ?",
        [service_name, yyyymm],
    ).fetchone()

    if service_data is not None:  # サービスが登録されていた場合、使用金額が上限金額のどれくらいなのかを計算する
        service_detail = add_usage_info_to_service_detail(
            service_data, sum([item["item_price"] for item in item_detail_list])
        )

        return render_template(
            "item_detail.html",
            item_detail_list=item_detail_list,
            year=yyyymm[:4],
            month=yyyymm[5:],
            service_detail=service_detail,
        )
    else:  # サービスが登録されていない場合、商品のみを表示する
        service_detail = {
            "service_name": service_name,
            "current_usage": sum([item["item_price"] for item in item_detail_list]),
            "upper_limit": 0,
            "text_style_usage_ratio": "width:0.0%",
            "usage_ratio_with_percent": "-",
        }

        return render_template(
            "item_detail.html",
            item_detail_list=item_detail_list,
            year=yyyymm[:4],
            month=yyyymm[5:],
            service_detail=service_detail,
        )


@app.route("/item_register", methods=["GET", "POST"])
def register_new_item():  # 新しい商品を登録する
    db = get_db()
    yyyymm = get_current_yyyymm()
    service_detail_list = db.execute(
        "select * from service where year_month = ?", [yyyymm]
    ).fetchall()
    if service_detail_list == []:
        return redirect("/service_register")

    if request.method == "POST":  # 登録ボタンが押された場合の処理
        # request.form.getで得られるのは全部str型
        purchase_date = request.form.get("purchase_date")  # 画面から送られてきた購入日 2023-09-01とか
        service_name = request.form.get("service_name")  # 画面から送られてきたサービス名
        item_name = request.form.get("item_name")  # 画面から送られてきた商品名
        item_price = request.form.get("item_price")  # 画面から送られてきた商品の金額
        item_attribute = request.form.get("item_attribute")  # 画面から送られてきた商品の属性

        is_existed_item = db.execute(  # 既に同じ名前の商品が同じサービスで購入されているかどうかを確認
            "select service_name, item_name from item where service_name = ? and item_name = ?",
            [
                service_name,
                item_name,
            ],
        ).fetchall()

        # 同じ商品が同じサービスで購入されている場合・入力が空欄の場合のエラーキャッチ
        if is_existed_item:
            return render_template(
                "item_register.html",
                error_message="同じ名前の商品がこのサービスで既に購入されています",
                service_detail_list=service_detail_list,
                item_attribute_list=ITEM_ATTRIBUTE_LIST,
            )
        if (
            is_there_empty_entry(
                [
                    purchase_date,
                    service_name,
                    item_name,
                    item_price,
                    item_attribute,
                ]
            )
            is True
        ):
            return render_template(
                "item_register.html",
                error_message="全て入力してください",
                service_detail_list=service_detail_list,
                item_attribute_list=ITEM_ATTRIBUTE_LIST,
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
        return redirect(
            f"/{service_name}/{purchase_date[:7]}/item_detail"
        )  # DBに新たなサービスを入れたら、商品登録画面に戻る

    return render_template(
        "item_register.html",
        error_message="",
        service_detail_list=service_detail_list,
        item_attribute_list=ITEM_ATTRIBUTE_LIST,
    )


@app.route("/<service_name>/item_edit/<item_id>", methods=["GET", "POST"])
def edit_item(service_name, item_id):  # 商品を編集する
    yyyymm = get_current_yyyymm()
    db = get_db()  # 接続を確立
    service_detail_list = db.execute(  # サービスの検索
        "select * from service where year_month = ?", [yyyymm]
    ).fetchall()
    objective_item = db.execute(  # 編集対象の商品
        "select * from item where item_id = ?", [item_id]
    ).fetchone()

    if request.method == "POST":  # 登録ボタンが押された場合の処理
        # request.form.getで得られるのは全部str型
        purchase_date = request.form.get("purchase_date")  # 画面から送られてきた購入日 2023-09-01とか
        service_name = request.form.get("service_name")  # 画面から送られてきたサービス名
        item_name = request.form.get("item_name")  # 画面から送られてきた商品名
        item_price = request.form.get("item_price")  # 画面から送られてきた商品の金額
        item_attribute = request.form.get("item_attribute")  # 画面から送られてきた商品の属性

        # 入力が空欄の場合のエラーキャッチ
        if (
            is_there_empty_entry(
                [
                    purchase_date,
                    service_name,
                    item_name,
                    item_price,
                    item_attribute,
                ]
            )
            is True
        ):
            return render_template(
                "item_edit.html",
                error_message="全て入力してください",
                objective_item=objective_item,
                service_detail_list=service_detail_list,
                item_attribute_list=ITEM_ATTRIBUTE_LIST,
            )

        # DBに上書き登録する処理
        db.execute(
            "update item set purchase_date = ?, service_name = ?, item_name = ?, item_price = ?, item_attribute = ? where item_id = ?",
            [
                purchase_date,
                service_name,
                item_name,
                item_price,
                item_attribute,
                item_id,
            ],
        )
        db.commit()
        return redirect(
            f"/{service_name}/{purchase_date[:7]}/item_detail"
        )  # DBの情報を編集したら、TOP画面に戻る

    return render_template(
        "item_edit.html",
        error_message="",
        objective_item=objective_item,
        service_detail_list=service_detail_list,
        item_attribute_list=ITEM_ATTRIBUTE_LIST,
    )


@app.route("/<service_name>/item_delete/<item_id>", methods=["GET", "POST"])
def delete_item(service_name, item_id):  # 登録されている商品を削除する
    db = get_db()

    if request.method == "POST":
        # DBから商品を削除する
        purchase_date = db.execute(
            "select purchase_date from item where item_id = ?", [item_id]
        ).fetchone()["purchase_date"]
        db.execute(
            "delete from item where item_id = ?",
            [item_id],
        )
        db.commit()  # BEGINは暗黙的に行われるので、変更はcommitするだけで良い
        return redirect(
            f"/{service_name}/{purchase_date[:7]}/item_detail"
        )  # DBから商品を削除したら、TOP画面に戻る

    objective_item = db.execute(
        "select * from item where item_id = ?",
        [
            item_id,
        ],
    ).fetchone()
    yyyymm = get_current_yyyymm()
    service_detail_list = db.execute(
        "select * from service where year_month = ?", [yyyymm]
    ).fetchall()
    return render_template(
        "item_delete.html",
        objective_item=objective_item,
        service_detail_list=service_detail_list,
        item_attribute_list=ITEM_ATTRIBUTE_LIST,
    )


@app.route("/history", methods=["GET", "POST"])
def show_graph():
    db = get_db()
    service_detail_list = db.execute(
        "select * from service",
    ).fetchall()
    # いくら節約できたかを可視化したいので、サービスの上限金額が記録されている月だけ選ぶ
    recorded_year_month_list = list(
        set([service_detail["year_month"] for service_detail in service_detail_list])
    )
    recorded_year_month_list.sort()

    total_upper_limit_and_usage_for_each_month = {}  # 各月の上限金額と使用金額を格納する
    for year_month in recorded_year_month_list:
        total_upper_limit_and_usage_for_each_month[year_month] = {
            "total_upper_limit": 0,
            "total_usage": 0,
        }

    for service_detail in service_detail_list:
        total_upper_limit_and_usage_for_each_month[service_detail["year_month"]][
            "total_upper_limit"
        ] += service_detail["upper_limit"]

    item_detail_list = db.execute("select * from item").fetchall()
    for item_detail in item_detail_list:
        # サービスの使用上限金額が決まっている月に購入された商品のみ購入する
        if (
            item_detail["purchase_date"][:7]
            in total_upper_limit_and_usage_for_each_month
        ):
            total_upper_limit_and_usage_for_each_month[
                item_detail["purchase_date"][:7]
            ]["total_usage"] += item_detail["item_price"]

    total_upper_limit = [
        total_upper_limit_and_usage["total_upper_limit"]
        for total_upper_limit_and_usage in total_upper_limit_and_usage_for_each_month.values()
    ]
    total_usage = [
        total_upper_limit_and_usage["total_usage"]
        for total_upper_limit_and_usage in total_upper_limit_and_usage_for_each_month.values()
    ]

    # グラフの見栄えを良くするために、最初に記録された月より一ヶ月前にデータを追加する
    if recorded_year_month_list:  # 過去の記録がある場合
        first_recorded_year_month = recorded_year_month_list[0]
        if first_recorded_year_month[5:] == "01":
            previous_year = str(int(first_recorded_year_month[:4]) - 1)
            previous_month = "12"
            recorded_year_month_list = [
                previous_year + "-" + previous_month
            ] + recorded_year_month_list
            total_upper_limit = [0] + total_upper_limit
            total_usage = [0] + total_usage
        else:
            previous_month = str(int(first_recorded_year_month[5:]) - 1).zfill(2)
            recorded_year_month_list = [
                first_recorded_year_month[:4] + "-" + previous_month
            ] + recorded_year_month_list
            total_upper_limit = [0] + total_upper_limit
            total_usage = [0] + total_usage

    return render_template(
        "line_graph.html",
        recorded_year_month_list=recorded_year_month_list,
        total_upper_limit=total_upper_limit,
        total_usage=total_usage,
        sum_of_total_upper_limit=sum(total_upper_limit),
        sum_of_total_usage=sum(total_usage),
    )


# ここから貯金画面
@app.route("/extra_item_detail")
def show_registered_extra_items():  # 登録した商品の一覧を表示
    db = get_db()  # 接続を確立
    service_detail_list = db.execute(
        "select * from service",
    ).fetchall()
    # 毎月登録している商品とサービスについて、使用額と上限額の合計を出す
    item_detail_list = db.execute("select * from item").fetchall()
    if item_detail_list:
        (
            _,
            _,
            _,
            sum_of_total_upper_limit,
            sum_of_total_usage,
            _,
        ) = get_total_usage_info(service_detail_list, item_detail_list)

        extra_money = sum_of_total_upper_limit - sum_of_total_usage  # 節約した金額
        extra_item_detail_list = db.execute("select * from extra_item").fetchall()
        extra_item_usage = sum(
            [extra_item["extra_item_price"] for extra_item in extra_item_detail_list]
        )
        extra_usage_ratio = round((extra_item_usage * 100) / extra_money, 1)

        return render_template(
            "extra_item_detail.html",
            extra_item_detail_list=extra_item_detail_list,
            sum_of_total_upper_limit=extra_money,
            sum_of_total_usage=extra_item_usage,
            text_style_usage_ratio=f"width:{extra_usage_ratio}%",
            usage_ratio_with_percent=f"{extra_usage_ratio}%",
        )
    else:
        return render_template(
            "extra_item_detail.html",
            extra_item_detail_list=[],
            sum_of_total_upper_limit=0,
            sum_of_total_usage=0,
            text_style_usage_ratio=f"width:{0}%",
            usage_ratio_with_percent=f"-",
        )


@app.route("/extra_item_register", methods=["GET", "POST"])
def register_new_extra_item():  # 新しい商品を登録する
    db = get_db()

    if request.method == "POST":  # 登録ボタンが押された場合の処理
        # request.form.getで得られるのは全部str型
        purchase_date = request.form.get("purchase_date")  # 画面から送られてきた購入日 2023-09-01とか
        service_name = request.form.get("service_name")  # 画面から送られてきたサービス名
        extra_item_name = request.form.get("extra_item_name")  # 画面から送られてきた商品名
        extra_item_price = request.form.get("extra_item_price")  # 画面から送られてきた商品の金額
        extra_item_attribute = request.form.get(
            "extra_item_attribute"
        )  # 画面から送られてきた商品の属性
        if (
            is_there_empty_entry(
                [
                    purchase_date,
                    service_name,
                    extra_item_name,
                    extra_item_price,
                    extra_item_attribute,
                ]
            )
            is True
        ):
            return render_template(
                "extra_item_register.html",
                error_message="全て入力してください",
                extra_item_attribute_list=ITEM_ATTRIBUTE_LIST,
            )

        # ここからDBに登録する処理
        register_body = {
            "purchase_date": purchase_date,
            "service_name": service_name,
            "extra_item_name": extra_item_name,
            "extra_item_price": extra_item_price,
            "extra_item_attribute": extra_item_attribute,
        }
        statement = "".join(
            [
                "insert into extra_item (",
                ", ".join("`" + key + "`" for key in register_body.keys()),
                ") values (",
                ", ".join(["?"] * len(register_body)),
                ")",
            ]
        )  # db.execute("insert into memo (title, body) values (?,?)", [service_name, body])みたいな形式
        db.execute(statement, [value for value in register_body.values()])
        db.commit()  # BEGINは暗黙的に行われるので、変更はcommitするだけで良い
        return redirect("/extra_item_detail")  # DBに新たなサービスを入れたら、商品登録画面に戻る

    return render_template(
        "extra_item_register.html",
        error_message="",
        extra_item_attribute_list=ITEM_ATTRIBUTE_LIST,
    )


@app.route("/extra_item_edit/<extra_item_id>", methods=["GET", "POST"])
def edit_extra_item(extra_item_id):  # 商品を編集する
    db = get_db()  # 接続を確立
    objective_extra_item = db.execute(  # 編集対象の商品
        "select * from extra_item where extra_item_id = ?", [extra_item_id]
    ).fetchone()

    if request.method == "POST":  # 編集ボタンが押された場合の処理
        # request.form.getで得られるのは全部str型
        purchase_date = request.form.get("purchase_date")  # 画面から送られてきた購入日 2023-09-01とか
        service_name = request.form.get("service_name")  # 画面から送られてきたサービス名
        extra_item_name = request.form.get("extra_item_name")  # 画面から送られてきた商品名
        extra_item_price = request.form.get("extra_item_price")  # 画面から送られてきた商品の金額
        extra_item_attribute = request.form.get(
            "extra_item_attribute"
        )  # 画面から送られてきた商品の属性

        # 入力が空欄の場合のエラーキャッチ
        if (
            is_there_empty_entry(
                [
                    purchase_date,
                    service_name,
                    extra_item_name,
                    extra_item_price,
                    extra_item_attribute,
                ]
            )
            is True
        ):
            return render_template(
                "extra_item_edit.html",
                error_message="全て入力してください",
                objective_extra_item=objective_extra_item,
                extra_item_attribute_list=ITEM_ATTRIBUTE_LIST,
            )

        # DBに上書き登録する処理
        db.execute(
            "update extra_item set purchase_date = ?, service_name = ?, extra_item_name = ?, extra_item_price = ?, extra_item_attribute = ? where extra_item_id = ?",
            [
                purchase_date,
                service_name,
                extra_item_name,
                extra_item_price,
                extra_item_attribute,
                extra_item_id,
            ],
        )
        db.commit()
        return redirect("/extra_item_detail")  # DBの情報を編集したら、TOP画面に戻る

    return render_template(
        "extra_item_edit.html",
        error_message="",
        objective_extra_item=objective_extra_item,
        extra_item_attribute_list=ITEM_ATTRIBUTE_LIST,
    )


@app.route("/extra_item_delete/<extra_item_id>", methods=["GET", "POST"])
def delete_extra_item(extra_item_id):  # 登録されているサービスを削除する
    db = get_db()

    if request.method == "POST":
        # DBからサービスを削除する
        db.execute(
            "delete from extra_item where extra_item_id = ?",
            [extra_item_id],
        )
        db.commit()  # BEGINは暗黙的に行われるので、変更はcommitするだけで良い
        return redirect("/extra_item_detail")  # DBからサービスを削除したら、TOP画面に戻る

    objective_extra_item = db.execute(
        "select * from extra_item where extra_item_id = ?",
        [
            extra_item_id,
        ],
    ).fetchone()
    return render_template(
        "extra_item_delete.html",
        objective_extra_item=objective_extra_item,
        extra_item_attribute_list=ITEM_ATTRIBUTE_LIST,
    )


con = sqlite3.connect("kakeibo.db")
cur = con.cursor()
cur.execute(
    "create table if not exists service(service_id integer primary key autoincrement, year_month text not null, service_name text not null, upper_limit integer not null)"
)
cur.execute(
    "create table if not exists item(item_id integer primary key autoincrement, purchase_date text not null, service_name text not null, item_name text not null, item_price integer not null, item_attribute text not null)"
)
cur.execute(
    "create table if not exists extra_item(extra_item_id integer primary key autoincrement, purchase_date text not null, service_name text not null, extra_item_name text not null, extra_item_price integer not null, extra_item_attribute text not null)"
)
con.close()
app.run(debug=True)  # debug=Trueでリロードすればコードの変更が反映される
