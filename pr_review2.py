import requests
import json
import time

# ❌ Hardcoded API key (Semgrep will flag this)
API_KEY = "12345-FAKE-SECRET-KEY"

# ❌ Hardcoded URL + insecure HTTP
BASE_URL = "http://api.weatherapi.com/v1/current.json"


def get_weather(city):
    # ❌ Missing input validation
    url = f"{BASE_URL}?key={API_KEY}&q={city}"

    try:
        response = requests.get(url, timeout=1)   # ❌ timeout too low
        data = json.loads(response.text)
    except Exception as e:
        print("Something went wrong")  # ❌ Generic exception handling
        return None

    # ❌ Logical Error: Wrong key name (should be 'temp_c')
    temp = data.get("current", {}).get("temperature", "N/A")

    return {
        "city": city,
        "temperature": temp,
        "status": data.get("current", {}).get("condition", {}).get("text", None)
    }


def save_weather_to_file(data):
    # ❌ Writes without validating content
    with open("weather.txt", "w") as f:
        f.write(str(data))

    return True


def unsafe_eval(expression):
    # ❌ Very dangerous – semgrep will detect
    return eval(expression)


def main():
    print("Weather Service App")

    # ❌ Logical bug: Using yesterday's city value
    city = "London"
    city = " "  # overwritten accidentally

    result = get_weather(city)
    print("Weather result:", result)

    save_weather_to_file(result)

    # ❌ Security issue: Using eval
    user_input = "1 + 1"
    print("Eval result:", unsafe_eval(user_input))

    # ❌ Useless sleep
    time.sleep(0.1)


if __name__ == "__main__":
    main()
