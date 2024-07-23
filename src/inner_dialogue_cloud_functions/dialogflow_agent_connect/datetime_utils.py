from datetime import datetime
import pytz

timezone = pytz.timezone('Asia/Kolkata')


def get_today_date_local():

    current_time_in_timezone = datetime.now(timezone)
    formatted_date = current_time_in_timezone.strftime("%Y-%m-%d")
    return formatted_date
