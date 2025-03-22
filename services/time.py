from datetime import datetime
from typing import Dict


def is_time_query(text: str) -> bool:
    """check if query is about time or date.

    args:
        text: input text

    returns:
        true if time-related, false otherwise
    """
    time_words = [
        'time', 'what time', 'current time', 'clock',
        'date', 'day', 'today', 'month', 'year', 'what day'
    ]
    text_lower = text.lower()
    return any(word in text_lower for word in time_words)


def get_time_data() -> Dict[str, str]:
    """get current time and date info.

    returns:
        dict with time and date details
    """
    now = datetime.now()

    return {
        "current_time": now.strftime("%I:%M %p"),
        "current_date": now.strftime("%A, %B %d, %Y"),
        "day_of_week": now.strftime("%A"),
        "month": now.strftime("%B"),
        "day": now.strftime("%d"),
        "year": now.strftime("%Y"),
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def format_time_data_for_prompt(time_data: Dict[str, str]) -> str:
    """format time data for prompt.

    args:
        time_data: dict from get_time_data()

    returns:
        formatted time info string
    """
    return f"""
--- CURRENT TIME DATA ---
Time: {time_data['current_time']}
Date: {time_data['current_date']}
Day: {time_data['day_of_week']}
"""