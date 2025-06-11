import requests
import json
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from datetime import datetime
import os
from flask import Flask, jsonify, render_template

template_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "templates")
)
app = Flask(__name__, template_folder=template_dir)


class GrowAGardenScraper:
    def __init__(self):
        self.base_url = "https://growagarden.gg"
        self.fallback_url = "https://growagardenstock.com/api"
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.6",
            "cache-control": "max-age=0",
            "priority": "u=0, i",
            "sec-ch-ua": '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

        self.fallback_headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
        }

    def fetch_page(self, path: str) -> str:
        try:
            response = requests.get(
                f"{self.base_url}/{path}", headers=self.headers, timeout=10
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching page: {e}")
            return None

    def fetch_fallback_stock(self, stock_type: str) -> Dict[str, Any]:
        try:
            timestamp = int(datetime.now().timestamp() * 1000)

            if stock_type == "gear-seeds":
                url = f"{self.fallback_url}/stock?type=gear-seeds&ts={timestamp}"
            elif stock_type in ["honey", "cosmetics"]:
                url = f"{self.fallback_url}/special-stock?type={stock_type}&ts={timestamp}"
            elif stock_type == "egg":
                url = f"{self.fallback_url}/stock?type=egg&ts={timestamp}"
            else:
                return None

            response = requests.get(url, headers=self.fallback_headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching fallback stock data for {stock_type}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing fallback JSON for {stock_type}: {e}")
            return None

    def parse_fallback_item(self, item_string: str) -> Dict[str, Any]:
        if "**x" in item_string and "**" in item_string:
            parts = item_string.split("**x")
            if len(parts) == 2:
                name = parts[0].strip()
                quantity_part = parts[1].replace("**", "").strip()
                try:
                    quantity = int(quantity_part)
                    return {"name": name, "quantity": quantity}
                except ValueError:
                    pass

        return {"name": item_string.replace("**", "").strip(), "quantity": 1}

    def convert_fallback_to_main_format(
        self, fallback_data: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        converted = {
            "gear": [],
            "egg": [],
            "seed": [],
            "easter": [],
            "night": [],
            "honey": [],
            "cosmetic": [],
        }

        if "gear" in fallback_data:
            converted["gear"] = [
                self.parse_fallback_item(item) for item in fallback_data["gear"]
            ]

        if "seeds" in fallback_data:
            converted["seed"] = [
                self.parse_fallback_item(item) for item in fallback_data["seeds"]
            ]

        if "egg" in fallback_data:
            converted["egg"] = [
                self.parse_fallback_item(item) for item in fallback_data["egg"]
            ]

        if "honey" in fallback_data:
            converted["honey"] = [
                self.parse_fallback_item(item) for item in fallback_data["honey"]
            ]

        if "cosmetics" in fallback_data:
            converted["cosmetic"] = [
                self.parse_fallback_item(item) for item in fallback_data["cosmetics"]
            ]

        return converted

    def get_fallback_stocks(self) -> Dict[str, List[Dict[str, Any]]]:
        print("Attempting to fetch stock data from fallback API...")

        all_fallback_data = {}

        # Fetch gear and seeds together
        gear_seeds_data = self.fetch_fallback_stock("gear-seeds")
        if gear_seeds_data:
            all_fallback_data.update(gear_seeds_data)
            print(f"Fetched gear-seeds data: {gear_seeds_data}")

        # Fetch other categories
        egg_data = self.fetch_fallback_stock("egg")
        if egg_data:
            all_fallback_data.update(egg_data)

        honey_data = self.fetch_fallback_stock("honey")
        if honey_data:
            all_fallback_data.update(honey_data)

        cosmetics_data = self.fetch_fallback_stock("cosmetics")
        if cosmetics_data:
            all_fallback_data.update(cosmetics_data)

        print(f"All fallback data collected: {all_fallback_data}")

        if all_fallback_data:
            converted_data = self.convert_fallback_to_main_format(all_fallback_data)
            print(f"Converted fallback data: {converted_data}")
            print("Successfully retrieved stock data from fallback API")
            return converted_data

        print("Failed to retrieve data from fallback API")
        return None

    def extract_data_from_script(
        self, script_content: str, data_key: str
    ) -> Dict[str, Any]:
        if not script_content or data_key not in script_content:
            return None

        def find_key_recursively(data: Any) -> Any:
            if isinstance(data, dict):
                if data_key in data:
                    return data[data_key]
                for v in data.values():
                    found = find_key_recursively(v)
                    if found is not None:
                        return found
            elif isinstance(data, list):
                for item in data:
                    found = find_key_recursively(item)
                    if found is not None:
                        return found
            return None

        try:
            push_match = re.search(
                r'self\.__next_f\.push\(\[1,"(.*)"\]\)$', script_content, re.DOTALL
            )
            if not push_match:
                return None

            escaped_content = push_match.group(1)
            unescaped = escaped_content.replace('\\"', '"').replace("\\\\", "\\")
            array_match = re.search(r"^\d+:\[(.*)\](?:\\n)?$", unescaped, re.DOTALL)
            if not array_match:
                return None

            array_content = "[" + array_match.group(1) + "]"

            try:
                parsed_array = json.loads(array_content)
                return find_key_recursively(parsed_array)
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                return None
        except Exception as e:
            print(f"Error in extraction: {e}")
            return None
        return None

    def extract_data(self, html_content: str, data_key: str) -> Dict[str, Any]:
        if not html_content:
            return None
        soup = BeautifulSoup(html_content, "html.parser")
        script_tags = soup.find_all("script")
        for i, script in enumerate(script_tags):
            if script.string and data_key in script.string:
                result = self.extract_data_from_script(script.string.strip(), data_key)
                if result:
                    return result
        return None

    def get_all_stocks(self) -> Dict[str, List[Dict[str, Any]]]:
        print("Attempting to fetch stock data from main source...")
        html_content = self.fetch_page("stocks")
        if not html_content:
            print("Failed to fetch HTML content for stocks from main source")
            return self.get_fallback_stocks()

        stock_data = self.extract_data(html_content, "stockDataSSR")
        if not stock_data:
            print("Failed to extract stock data from main source")
            return self.get_fallback_stocks()

        for key, value in stock_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        item.pop("image", None)
                        item.pop("emoji", None)

        result = {
            "gear": stock_data.get("gearStock", []),
            "egg": stock_data.get("eggStock", []),
            "seed": stock_data.get("seedsStock", []),
            "easter": stock_data.get("easterStock", []),
            "night": stock_data.get("nightStock", []),
            "honey": stock_data.get("honeyStock", []),
            "cosmetic": stock_data.get("cosmeticsStock", []),
        }

        print("Successfully retrieved stock data from main source")
        return result

    def get_weather(self) -> Dict[str, Any]:
        html_content = self.fetch_page("weather")
        if not html_content:
            print("Failed to fetch HTML content for weather")
            return None
        weather_data = self.extract_data(html_content, "weatherDataSSR")
        if not weather_data:
            print("Failed to extract weather data.")
            return None

        if isinstance(weather_data.get("currentWeather"), dict):
            weather_data["currentWeather"].pop("image", None)

        if weather_data.get("nextWeatherTimestamp"):
            try:
                timestamp_ms = int(weather_data["nextWeatherTimestamp"])
                timestamp_s = timestamp_ms / 1000.0
                dt_object = datetime.fromtimestamp(timestamp_s)
                weather_data["nextWeatherTimestampISO"] = dt_object.isoformat()

                hour = dt_object.strftime("%I")
                if hour.startswith("0"):
                    hour = hour[1:]

                weather_data["nextWeatherFormatted"] = (
                    f"{dt_object.strftime('%b').lower()} {dt_object.day} {dt_object.year} - {hour}:{dt_object.strftime('%M%p').lower()}"
                )
            except (ValueError, TypeError, KeyError):
                pass

        if isinstance(weather_data.get("specialWeathers"), dict):
            for event, event_data in weather_data["specialWeathers"].items():
                if isinstance(event_data, dict) and "timestamp" in event_data:
                    try:
                        timestamp_ms = int(event_data["timestamp"])
                        timestamp_s = timestamp_ms / 1000.0
                        dt_object = datetime.fromtimestamp(timestamp_s)
                        event_data["timestampISO"] = dt_object.isoformat()

                        hour = dt_object.strftime("%I")
                        if hour.startswith("0"):
                            hour = hour[1:]

                        event_data["timestampFormatted"] = (
                            f"{dt_object.strftime('%b').lower()} {dt_object.day} {dt_object.year} - {hour}:{dt_object.strftime('%M%p').lower()}"
                        )
                    except (ValueError, TypeError, KeyError):
                        pass

        return weather_data


scraper = GrowAGardenScraper()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/docs", methods=["GET"])
def docs():
    return render_template("docs.html")


@app.route("/api", methods=["GET"])
def api_info():
    return jsonify(
        {
            "name": "GrowAGarden.gg API Scraper",
            "version": "1.0.0",
            "description": "Unofficial API for GrowAGarden.gg game data including stocks and weather information",
            "credits": {
                "original_site": "https://growagarden.gg",
                "developer": "Community API Wrapper",
                "note": "This is an unofficial API. All data belongs to GrowAGarden.gg",
            },
            "endpoints": {
                "/": {
                    "method": "GET",
                    "description": "Web interface showing current stocks and weather",
                },
                "/docs": {"method": "GET", "description": "API documentation page"},
                "/api": {"method": "GET", "description": "API information (JSON)"},
                "/api/stocks": {
                    "method": "GET",
                    "description": "Get all stock data from all categories",
                    "returns": "Complete stock inventory across all shop categories",
                },
                "/api/stocks/{category}": {
                    "method": "GET",
                    "description": "Get stock data for a specific category",
                    "parameters": {"category": "Stock category name"},
                    "valid_categories": [
                        "seed",
                        "gear",
                        "egg",
                        "cosmetic",
                        "honey",
                        "easter",
                        "night",
                    ],
                    "example": "/api/stocks/seed",
                    "returns": "Stock data for the specified category only",
                },
                "/api/weather": {
                    "method": "GET",
                    "description": "Get current and upcoming weather information",
                    "returns": "Current weather state, timestamps, and special weather events",
                },
            },
            "data_format": {
                "stocks": "Array of items with name, price, quantity, and availability info",
                "weather": "Current weather state, timestamps, and special weather events",
            },
            "rate_limits": "Please use responsibly to avoid overloading the source website",
            "disclaimer": "This API scrapes data from GrowAGarden.gg. Data accuracy depends on the source site.",
        }
    )


@app.route("/stocks", methods=["GET"])
@app.route("/api/stocks", methods=["GET"])
def api_all_stocks():
    try:
        stocks = scraper.get_all_stocks()
        if stocks:
            return jsonify(stocks)
        return jsonify({"error": "Failed to retrieve stock data"}), 500
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/stocks/<category>", methods=["GET"])
@app.route("/api/stocks/<category>", methods=["GET"])
def api_stock_category(category):
    valid_categories = ["seed", "gear", "egg", "cosmetic", "honey", "easter", "night"]
    if category not in valid_categories:
        return (
            jsonify(
                {
                    "error": f"Invalid category. Valid categories are: {', '.join(valid_categories)}"
                }
            ),
            400,
        )

    try:
        stocks = scraper.get_all_stocks()
        if stocks and category in stocks:
            return jsonify({category: stocks[category]})
        return (
            jsonify(
                {"error": f"Failed to retrieve stock data for category: {category}"}
            ),
            500,
        )
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/weather", methods=["GET"])
@app.route("/api/weather", methods=["GET"])
def api_weather():
    try:
        weather = scraper.get_weather()
        if weather:
            return jsonify(weather)
        return jsonify({"error": "Failed to retrieve weather data"}), 500
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)
