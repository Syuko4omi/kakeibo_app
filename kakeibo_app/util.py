import datetime


def get_current_yyyymm() -> str:  # 年と月を取得する
    tokyo_tz = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.now(tokyo_tz)
    year = str(dt.year)
    month = "{:02}".format(dt.month)
    return year + "-" + month


def is_there_empty_entry(entry_list) -> bool:
    for entry in entry_list:
        if entry == "":
            return True
    return False


def get_total_usage_info(service_detail_list, item_detail_list):
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
