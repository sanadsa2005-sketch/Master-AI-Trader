import requests
import json
from config import CHART_IMG_API_KEY

BASE_URL = "https://api.chart-img.com/v2/tradingview/advanced-chart/storage"

def get_chart(exchange: str, ticker: str, interval: str, indicator_type: str, theme: str = "dark") -> str:
    """
    Generates a chart URL from chart-img.com based on the parameters.
    """
    symbol = f"{exchange}:{ticker}"
    
    # Map intervals to API format (TradingView usually expects uppercase for D/W)
    interval_map = {
        "1d": "1D",
        "1w": "1W"
    }
    api_interval = interval_map.get(interval, interval)

    
    studies = []
    
    # Default override for aesthetic charts
    common_override = {}

    if indicator_type == "RSI":
        studies.append({
            "name": "Relative Strength Index",
            "forceOverlay": False,
            "input": {"length": 14},
            "override": {
                "Plot.color": "rgb(156,39,176)",
                "Plot.linewidth": 2
            }
        })
    elif indicator_type == "MACD":
        studies.append({
            "name": "MACD",
            "forceOverlay": False,
            "input": {"fastLength": 12, "slowLength": 26, "signalLength": 9},
            "override": {}
        })
    elif indicator_type == "Volume":
        studies.append({
            "name": "Volume",
            "forceOverlay": False, 
            "input": {},
            "override": {}
        })
    elif indicator_type == "Bollinger Bands":
        studies.append({
            "name": "Bollinger Bands",
            "forceOverlay": True,
            "input": {"length": 20, "stdDev": 2},
            "override": {}
        })
    elif indicator_type == "ATR":
        studies.append({
            "name": "Average True Range",
            "forceOverlay": False,
            "input": {"length": 14},
            "override": {}
        })
    elif indicator_type == "OBV":
        studies.append({
            "name": "On Balance Volume",
            "forceOverlay": False,
            "input": {},
            "override": {}
        })
    elif indicator_type == "VWAP":
        studies.append({
            "name": "VWAP",
            "forceOverlay": True,
            "input": {},
            "override": {}
        })
    elif indicator_type == "Stochastic RSI":
        studies.append({
            "name": "Stochastic RSI",
            "forceOverlay": False,
            "input": {"k": 3, "d": 3, "rsiLength": 14, "stochLength": 14},
            "override": {}
        })
    elif indicator_type == "Ichimoku Cloud":
        studies.append({
            "name": "Ichimoku Cloud",
            "forceOverlay": True,
            "input": {
                "conversionLineLength": 9,
                "baseLineLength": 26,
                "leadingSpanBLength": 52,
                "displacement": 26
            },
            "override": {}
        })
    elif indicator_type == "MA Double":
        studies.append({
            "name": "Moving Average Exponential",
            "forceOverlay": True,
            "input": {"length": 21},
            "override": {"Plot.color": "rgb(0,0,255)", "Plot.linewidth": 2}
        })
        studies.append({
            "name": "Moving Average Exponential",
            "forceOverlay": True,
            "input": {"length": 55},
            "override": {"Plot.color": "rgb(255,165,0)", "Plot.linewidth": 2}
        })

    payload = {
        "symbol": symbol,
        "interval": api_interval,
        "theme": theme,
        "studies": studies,
        "width": 800,
        "height": 600,
        "timezone": "Etc/UTC" # Defaulting to UTC
    }
    
    headers = {
        "x-api-key": CHART_IMG_API_KEY,
        "Content-Type": "application/json"
    }
    
    # For debugging/verification (remove in prod if needed, or keep for logs)
    # print(f"Requesting chart for {indicator_type}...")
    
    response = requests.post(BASE_URL, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Chart generation failed: {response.text}")
        
    data = response.json()
    return data.get("url")
