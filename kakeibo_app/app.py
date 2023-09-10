from flask import Flask, render_template
import datetime

app = Flask(__name__)


@app.route("/")
def top():  # トップ画面を表示
    tokyo_tz = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.now(tokyo_tz)

    service_detail_list = [
        {
            "service_name": "service_1",
            "current_usage": 4000,
            "upper_limit": 12000,
            "usage_ratio": 33.3,
            "text_style_usage_ratio": "width:33.3%",
            "usage_ratio_with_percent": "33.3%",
        },
        {
            "service_name": "service_2",
            "current_usage": 9000,
            "upper_limit": 10000,
            "usage_ratio": 90.0,
            "text_style_usage_ratio": "width:90.0%",
            "usage_ratio_with_percent": "90.0%",
        },
        {
            "service_name": "service_3",
            "current_usage": 10000,
            "upper_limit": 5000,
            "usage_ratio": 200.0,
            "text_style_usage_ratio": "width:200.0%",
            "usage_ratio_with_percent": "200.0%",
        },
    ]

    total_current_usage = sum(
        [service_detail["current_usage"] for service_detail in service_detail_list]
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
        total_current_usage=total_current_usage,
        total_upper_limit=total_upper_limit,
        text_style_total_usage_ratio=text_style_total_usage_ratio,
        total_usage_ratio_with_percent=total_usage_ratio_with_percent,
        service_detail_list=service_detail_list,
    )


@app.route("/service_detail")
def show_registered_services():  # 登録したサービスの一覧を表示
    service_detail_list = [
        {
            "service_name": "service_1",
            "current_usage": 4000,
            "upper_limit": 12000,
            "usage_ratio": 33.3,
            "text_style_usage_ratio": "width:33.3%",
            "usage_ratio_with_percent": "33.3%",
        },
        {
            "service_name": "service_2",
            "current_usage": 9000,
            "upper_limit": 10000,
            "usage_ratio": 90.0,
            "text_style_usage_ratio": "width:90.0%",
            "usage_ratio_with_percent": "90.0%",
        },
        {
            "service_name": "service_3",
            "current_usage": 10000,
            "upper_limit": 5000,
            "usage_ratio": 200.0,
            "text_style_usage_ratio": "width:200.0%",
            "usage_ratio_with_percent": "200.0%",
        },
    ]
    return render_template(
        "service_detail.html", service_detail_list=service_detail_list
    )


app.run()
