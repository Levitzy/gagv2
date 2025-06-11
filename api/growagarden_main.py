import requests
import json
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from datetime import datetime


class GrowAGardenMainAPI:
    def __init__(self):
        self.base_url = "https://growagarden.gg"
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

    def fetch_page(self, path: str) -> str:
        try:
            response = requests.get(
                f"{self.base_url}/{path}", headers=self.headers, timeout=10
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching page from main API: {e}")
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

    def normalize_stock_data(
        self, stock_data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        normalized = {}

        for category, items in stock_data.items():
            normalized_items = []
            for item in items:
                normalized_item = {
                    "name": item.get("name", ""),
                    "value": item.get("value", item.get("quantity", 1)),
                }

                if "price" in item:
                    normalized_item["price"] = item["price"]

                if "available" in item:
                    normalized_item["available"] = item["available"]

                normalized_items.append(normalized_item)

            normalized[category] = normalized_items

        return normalized

    def get_stocks(self) -> Dict[str, List[Dict[str, Any]]]:
        print("🔍 Attempting to fetch stock data from main source...")

        try:
            html_content = self.fetch_page("stocks")
            if not html_content:
                print("❌ Failed to fetch HTML content for stocks from main source")
                return None

            stock_data = self.extract_data(html_content, "stockDataSSR")
            if not stock_data:
                print("❌ Failed to extract stock data from main source")
                return None

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

            normalized_result = self.normalize_stock_data(result)

            total_items = sum(
                len(category_items) for category_items in normalized_result.values()
            )
            print(
                f"✅ Successfully retrieved stock data from main source - Total items: {total_items}"
            )

            for category, items in normalized_result.items():
                if items:
                    items_with_available = [
                        item for item in items if "available" in item
                    ]
                    if items_with_available:
                        available_items = [
                            item
                            for item in items_with_available
                            if item.get("available", True)
                        ]
                        print(
                            f"  - {category}: {len(items)} items ({len(available_items)} available)"
                        )
                    else:
                        print(f"  - {category}: {len(items)} items")

            return normalized_result

        except Exception as e:
            print(f"❌ Error fetching from main source: {e}")
            return None

    def get_weather(self) -> Dict[str, Any]:
        print("🔍 Attempting to fetch weather data from main source...")

        try:
            html_content = self.fetch_page("weather")
            if not html_content:
                print("❌ Failed to fetch HTML content for weather from main source")
                return None

            weather_data = self.extract_data(html_content, "weatherDataSSR")
            if not weather_data:
                print("❌ Failed to extract weather data from main source")
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

            print("✅ Successfully retrieved weather data from main source")
            return weather_data

        except Exception as e:
            print(f"❌ Error fetching weather from main source: {e}")
            return None
