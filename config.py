import os
from dotenv import load_dotenv

load_dotenv()

CHART_IMG_API_KEY = os.getenv("CHART_IMG_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
