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
