import os
from flask import Flask, jsonify, render_template
from growagarden_main import GrowAGardenMainAPI
from growagarden_fallbackone import GrowAGardenFallbackAPI

template_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "templates")
)
app = Flask(__name__, template_folder=template_dir)


class GrowAGardenService:
    def __init__(self):
        self.main_api = GrowAGardenMainAPI()
        self.fallback_api = GrowAGardenFallbackAPI()

    def get_all_stocks(self):
        try:
            stocks = self.main_api.get_stocks()
            if stocks:
                return stocks
            else:
                print("⚠️ Main API failed, trying fallback API...")
                fallback_stocks = self.fallback_api.get_stocks()
                return fallback_stocks
        except Exception as e:
            print(f"❌ Error in main service, trying fallback: {e}")
            try:
                fallback_stocks = self.fallback_api.get_stocks()
                return fallback_stocks
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {fallback_error}")
                return None

    def get_weather(self):
        try:
            weather = self.main_api.get_weather()
            if weather:
                return weather
            else:
                print("⚠️ Main API weather failed, fallback API doesn't support weather")
                return None
        except Exception as e:
            print(f"❌ Error fetching weather: {e}")
            return None


service = GrowAGardenService()


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
            "version": "2.0.0",
            "description": "Unofficial API for GrowAGarden.gg game data including stocks and weather information",
            "architecture": {
                "main_api": "Primary data source from growagarden.gg",
                "fallback_api": "Secondary data source from growagardenstock.com/api",
                "auto_failover": "Automatically switches to fallback when main API fails",
            },
            "credits": {
                "original_site": "https://growagarden.gg",
                "fallback_source": "https://growagardenstock.com/api",
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
                    "fallback": "Supports automatic fallback to secondary API",
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
                    "fallback": "Supports automatic fallback to secondary API",
                },
                "/api/weather": {
                    "method": "GET",
                    "description": "Get current and upcoming weather information",
                    "returns": "Current weather state, timestamps, and special weather events",
                    "fallback": "Only available from main API",
                },
            },
            "data_format": {
                "stocks": "Array of items with name and value info (available field only from main API)",
                "weather": "Current weather state, timestamps, and special weather events (main API only)",
            },
            "reliability": {
                "main_api_features": "Full feature set including availability status",
                "fallback_api_features": "Stock data only, no weather or availability status",
                "auto_switching": "Seamless failover between APIs for maximum uptime",
            },
            "rate_limits": "Please use responsibly to avoid overloading the source websites",
            "disclaimer": "This API scrapes data from multiple sources. Data accuracy depends on the source sites.",
        }
    )


@app.route("/stocks", methods=["GET"])
@app.route("/api/stocks", methods=["GET"])
def api_all_stocks():
    try:
        stocks = service.get_all_stocks()
        if stocks:
            return jsonify(stocks)
        return jsonify({"error": "Failed to retrieve stock data from all sources"}), 500
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
        stocks = service.get_all_stocks()
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
        weather = service.get_weather()
        if weather:
            return jsonify(weather)
        return jsonify({"error": "Failed to retrieve weather data"}), 500
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify API status"""
    try:
        main_status = "unknown"
        fallback_status = "unknown"

        try:
            test_stocks = service.main_api.get_stocks()
            main_status = "online" if test_stocks else "offline"
        except:
            main_status = "offline"

        try:
            test_fallback = service.fallback_api.get_stocks()
            fallback_status = "online" if test_fallback else "offline"
        except:
            fallback_status = "offline"

        overall_status = (
            "healthy"
            if (main_status == "online" or fallback_status == "online")
            else "unhealthy"
        )

        return jsonify(
            {
                "status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "apis": {
                    "main_api": {
                        "status": main_status,
                        "source": "growagarden.gg",
                        "features": ["stocks", "weather"],
                    },
                    "fallback_api": {
                        "status": fallback_status,
                        "source": "growagardenstock.com/api",
                        "features": ["stocks"],
                    },
                },
                "version": "2.0.0",
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)
