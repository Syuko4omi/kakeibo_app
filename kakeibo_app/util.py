import datetime
import sqlite3


def get_current_yyyymm() -> str:  # 年と月を取得する
    tokyo_tz = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.now(tokyo_tz)
    year = str(dt.year)
    month = "{:02}".format(dt.month)
    return year + "-" + month


def is_there_empty_entry(entry_list: list[str]) -> bool:
    for entry in entry_list:
        if entry == "":
            return True
    return False


def get_total_usage_info(
    service_detail_list: list[sqlite3.Row], item_detail_list: list[sqlite3.Row]
):
    # 毎月登録している商品とサービスについて、使用額と上限額の合計を出す
    # いくら節約できたかを可視化したいので、サービスの上限金額が記録されている月だけ選ぶ
    recorded_year_month_list = list(
        set([service_detail["year_month"] for service_detail in service_detail_list])
    )
    recorded_year_month_list.sort()

    total_upper_limit_and_usage_for_each_month = {}
    for year_month in recorded_year_month_list:
        total_upper_limit_and_usage_for_each_month[year_month] = {
            "total_upper_limit": 0,
            "total_usage": 0,
        }

    for service_detail in service_detail_list:
        total_upper_limit_and_usage_for_each_month[service_detail["year_month"]][
            "total_upper_limit"
        ] += service_detail["upper_limit"]

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
    sum_of_total_upper_limit = sum(total_upper_limit)
    sum_of_total_usage = sum(total_usage)
    usage_ratio = round((sum_of_total_usage * 100) / sum_of_total_upper_limit, 1)

    return (
        recorded_year_month_list,
        total_upper_limit,
        total_usage,
        sum_of_total_upper_limit,
        sum_of_total_usage,
        usage_ratio,
    )


def add_usage_info_to_service_detail(service_detail: sqlite3.Row, current_usage: int):
    # ある月のサービスの上限金額と、そのサービスで買った商品の合計金額を元に、使用率を計算する
    service_name = service_detail["service_name"]
    upper_limit = service_detail["upper_limit"]
    usage_ratio = round((current_usage * 100 / upper_limit), 1)
    text_style_usage_ratio = f"width:{usage_ratio}%"
    usage_ratio_with_percent = f"{usage_ratio}%"

    return {
        "service_name": service_name,
        "current_usage": current_usage,
        "upper_limit": upper_limit,
        "text_style_usage_ratio": text_style_usage_ratio,
        "usage_ratio_with_percent": usage_ratio_with_percent,
    }
