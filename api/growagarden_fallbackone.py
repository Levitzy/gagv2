import requests
import json
from typing import Dict, List, Any
from datetime import datetime


class GrowAGardenFallbackAPI:
    def __init__(self):
        self.fallback_url = "https://growagardenstock.com/api"
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
                print(f"Unknown stock type: {stock_type}")
                return None

            print(f"Fetching from fallback URL: {url}")
            response = requests.get(url, headers=self.fallback_headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            print(f"Fallback API response for {stock_type}: {data}")
            return data

        except requests.RequestException as e:
            print(f"Network error fetching fallback stock data for {stock_type}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error for {stock_type}: {e}")
            print(
                f"Raw response: {response.text[:500] if 'response' in locals() else 'No response'}"
            )
            return None
        except Exception as e:
            print(
                f"Unexpected error fetching fallback stock data for {stock_type}: {e}"
            )
            return None

    def parse_fallback_item(self, item_string: str) -> Dict[str, Any]:
        clean_item = item_string.replace("**", "").strip()

        if "x" in clean_item:
            parts = clean_item.split("x")
            if len(parts) == 2:
                name = parts[0].strip()
                try:
                    value = int(parts[1].strip())
                    return {"name": name, "value": value}
                except ValueError:
                    pass

        return {"name": clean_item, "value": 1}

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

        if "gear" in fallback_data and isinstance(fallback_data["gear"], list):
            converted["gear"] = [
                self.parse_fallback_item(item) for item in fallback_data["gear"]
            ]

        if "seeds" in fallback_data and isinstance(fallback_data["seeds"], list):
            converted["seed"] = [
                self.parse_fallback_item(item) for item in fallback_data["seeds"]
            ]

        if "egg" in fallback_data and isinstance(fallback_data["egg"], list):
            converted["egg"] = [
                self.parse_fallback_item(item) for item in fallback_data["egg"]
            ]

        if "honey" in fallback_data and isinstance(fallback_data["honey"], list):
            converted["honey"] = [
                self.parse_fallback_item(item) for item in fallback_data["honey"]
            ]

        if "cosmetics" in fallback_data and isinstance(
            fallback_data["cosmetics"], list
        ):
            converted["cosmetic"] = [
                self.parse_fallback_item(item) for item in fallback_data["cosmetics"]
            ]

        return converted

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
        print("🔄 Attempting to fetch stock data from fallback API...")

        all_fallback_data = {}
        fallback_success = False

        try:
            gear_seeds_data = self.fetch_fallback_stock("gear-seeds")
            if gear_seeds_data:
                all_fallback_data.update(gear_seeds_data)
                print(
                    f"✓ Fetched gear-seeds: {len(gear_seeds_data.get('gear', []))} gear items, {len(gear_seeds_data.get('seeds', []))} seed items"
                )
                fallback_success = True
            else:
                print("✗ Failed to fetch gear-seeds data")
        except Exception as e:
            print(f"✗ Error fetching gear-seeds: {e}")

        try:
            egg_data = self.fetch_fallback_stock("egg")
            if egg_data:
                all_fallback_data.update(egg_data)
                print(f"✓ Fetched eggs: {len(egg_data.get('egg', []))} items")
                fallback_success = True
            else:
                print("✗ Failed to fetch egg data")
        except Exception as e:
            print(f"✗ Error fetching eggs: {e}")

        try:
            honey_data = self.fetch_fallback_stock("honey")
            if honey_data:
                all_fallback_data.update(honey_data)
                print(f"✓ Fetched honey: {len(honey_data.get('honey', []))} items")
                fallback_success = True
            else:
                print("✗ Failed to fetch honey data")
        except Exception as e:
            print(f"✗ Error fetching honey: {e}")

        try:
            cosmetics_data = self.fetch_fallback_stock("cosmetics")
            if cosmetics_data:
                all_fallback_data.update(cosmetics_data)
                print(
                    f"✓ Fetched cosmetics: {len(cosmetics_data.get('cosmetics', []))} items"
                )
                fallback_success = True
            else:
                print("✗ Failed to fetch cosmetics data")
        except Exception as e:
            print(f"✗ Error fetching cosmetics: {e}")

        if fallback_success and all_fallback_data:
            converted_data = self.convert_fallback_to_main_format(all_fallback_data)

            total_items = sum(
                len(category_items) for category_items in converted_data.values()
            )
            print(
                f"✅ Successfully converted fallback data - Total items: {total_items}"
            )

            for category, items in converted_data.items():
                if items:
                    print(f"  - {category}: {len(items)} items")

            return self.normalize_stock_data(converted_data)

        print("❌ Failed to retrieve any data from fallback API")
        return None

    def get_weather(self) -> Dict[str, Any]:
        print("🔄 Fallback API does not support weather data")
        return None
