import json
import os
from datetime import datetime

import python_weather

# default location if none specified
DEFAULT_LOCATION = "Santa Cruz"
# file to store user's location
LOCATION_CONFIG_FILE = "location_config.json"


async def get_weather_data(location=None):
    """get weather data for location.

    args:
        location: location to check (uses saved or default if none)

    returns:
        dict with weather data or none if failed
    """
    try:
        # use saved location if none given
        if location is None:
            location = get_saved_location()

        # get weather
        async with python_weather.Client(unit=python_weather.IMPERIAL) as sky_eye:
            # fetch data
            sky_report = await sky_eye.get(location)

            # current conditions
            current = {
                "location": sky_report.location,
                "region": sky_report.region,
                "country": sky_report.country,
                "temperature": sky_report.temperature,
                "feels_like": sky_report.feels_like,
                "humidity": sky_report.humidity,
                "description": sky_report.description,
                "kind": sky_report.kind.name,
                "wind_speed": sky_report.wind_speed,
                "wind_direction": sky_report.wind_direction.name,
                "precipitation": sky_report.precipitation,
                "local_time": sky_report.datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # today's forecast
            if sky_report.daily_forecasts:
                today = sky_report.daily_forecasts[0]
                current.update({
                    "today_high": today.highest_temperature,
                    "today_low": today.lowest_temperature,
                    "sunrise": today.sunrise.strftime("%H:%M") if today.sunrise else "N/A",
                    "sunset": today.sunset.strftime("%H:%M") if today.sunset else "N/A",
                })

                # upcoming hours
                coming_hours = []
                for hour in today.hourly_forecasts:
                    if hour.time > datetime.now().time():
                        coming_hours.append({
                            "time": hour.time.strftime("%H:%M"),
                            "temperature": hour.temperature,
                            "description": hour.description,
                            "chance_of_rain": hour.chances_of_rain,
                        })
                        # just get next few hours
                        if len(coming_hours) >= 3:
                            break

                if coming_hours:
                    current["upcoming_hours"] = coming_hours

            return current
    except Exception as e:
        print(f"error getting weather: {e}")
        return None


def get_saved_location():
    """get user's saved location.

    returns:
        saved location or default
    """
    try:
        if os.path.exists(LOCATION_CONFIG_FILE):
            with open(LOCATION_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('location', DEFAULT_LOCATION)
    except Exception as e:
        print(f"error reading location config: {e}")

    return DEFAULT_LOCATION


def save_location(location):
    """save user's location.

    args:
        location: location to save

    returns:
        true if successful, false otherwise
    """
    try:
        config = {'location': location}
        with open(LOCATION_CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return True
    except Exception as e:
        print(f"error saving location: {e}")
        return False


def is_weather_query(text):
    """check if query is about weather.

    args:
        text: user's query

    returns:
        true if weather-related, false otherwise
    """
    sky_words = [
        'weather', 'temperature', 'forecast', 'rain', 'sunny', 'cloudy',
        'snow', 'storm', 'cold', 'hot', 'humid', 'wind', 'windy',
        'precipitation', 'climate', 'foggy', 'frost', 'hail', 'thunder',
        'lightning', 'temperature', 'degrees', 'sunrise', 'sunset'
    ]

    # check for location setting request
    if "set my location" in text.lower() or "change my location" in text.lower():
        return True

    # check if any weather words are in the text
    text_lower = text.lower()
    for word in sky_words:
        if word in text_lower:
            return True

    return False


def extract_location(text):
    """extract location from text.

    args:
        text: text to extract from

    returns:
        location or none if not found
    """
    text_lower = text.lower()

    # check for location patterns
    location_phrases = [
        "set my location to ",
        "change my location to ",
        "my location is ",
        "weather in ",
        "temperature in ",
        "forecast for ",
        "weather for ",
        "how's the weather in ",
        "how is the weather in ",
        "weather"
    ]

    for phrase in location_phrases:
        if phrase in text_lower:
            # get location after phrase
            place = text_lower.split(phrase, 1)[1].strip()
            # remove sentence endings
            for ending in ['.', '?', '!']:
                if ending in place:
                    place = place.split(ending, 1)[0].strip()
            return place if place else None

    return None


def format_weather_data_for_prompt(weather_data):
    """format weather data for prompt.

    args:
        weather_data: data from get_weather_data

    returns:
        formatted weather text
    """
    if not weather_data:
        return "weather data couldn't be retrieved."

    # format current weather
    sky_text = f"""
        --- CURRENT WEATHER DATA ---
        Location: {weather_data['location']}, {weather_data['region']}, {weather_data['country']}
        Current Time: {weather_data['local_time']}
        Temperature: {weather_data['temperature']}°F (Feels like: {weather_data['feels_like']}°F)
        Conditions: {weather_data['description']}
        Humidity: {weather_data['humidity']}%
        Wind: {weather_data['wind_speed']} km/h {weather_data['wind_direction']}
"""

    # add high/low
    if 'today_high' in weather_data and 'today_low' in weather_data:
        sky_text += f"Today's High: {weather_data['today_high']}°F / Low: {weather_data['today_low']}°F\n"

    # add sunrise/sunset
    if 'sunrise' in weather_data and 'sunset' in weather_data:
        sky_text += f"Sunrise: {weather_data['sunrise']} / Sunset: {weather_data['sunset']}\n"

    # add upcoming hours
    if 'upcoming_hours' in weather_data and weather_data['upcoming_hours']:
        sky_text += "\nUpcoming Hours:\n"
        for hour in weather_data['upcoming_hours']:
            rain_chance = f" ({hour['chance_of_rain']}% chance of rain)" if hour['chance_of_rain'] > 0 else ""
            sky_text += f"- {hour['time']}: {hour['temperature']}°F, {hour['description']}{rain_chance}\n"

    return sky_text