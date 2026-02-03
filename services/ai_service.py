import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted
import requests
import json
import datetime
import time 
from PIL import Image
from io import BytesIO
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import GEMINI_API_KEY
from utils.prompts import CANDLESTICK_ANALYSIS_PROMPT, INDICATOR_PROMPTS, MASTER_SYNTHESIS_PROMPT

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Safety settings to prevent blocking of financial analysis
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

GENERATION_CONFIG = {
    "temperature": 0.1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

def get_image_from_url(url: str):
    """Downloads an image from a URL and converts it to PIL Image."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        # Optimize: Aggressively resize image for Free Tier
        img.thumbnail((256, 256))
        return img
    except Exception as e:
        print(f"Failed to download image {url}: {e}")
        return None

# Configure retry logic
def log_retry(retry_state):
    print(f"Rate limit/Error encountered. Retrying in {retry_state.next_action.sleep:.1f}s... (Attempt {retry_state.attempt_number})")

@retry(
    retry=retry_if_exception_type(Exception), 
    wait=wait_exponential(multiplier=2, min=5, max=60),
    stop=stop_after_attempt(10),
    before_sleep=log_retry
)
def call_gemini(system_prompt: str, content_parts: list, force_json: bool = False) -> str:
    """
    Calls Gemini model with automatic retries for rate limits.
    """
    try:
        config = GENERATION_CONFIG.copy()
        if force_json:
            config["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(
            model_name="gemini-flash-lite-latest",
            system_instruction=system_prompt,
            generation_config=config,
            safety_settings=SAFETY_SETTINGS
        )
        
        response = model.generate_content(content_parts)
        
        # Check if response was blocked or empty
        if not response.parts:
            # If blocked, don't retry, just return error
            return f"Gemini response blocked/empty. Feedback: {response.prompt_feedback}"
            
        return response.text
    except Exception as e:
        error_str = str(e)
        # Check for Rate Limit errors (429 or ResourceExhausted)
        if "429" in error_str or "ResourceExhausted" in error_str:
            print(f"Rate limit hit. Waiting for quota... Error: {error_str}")
            raise e # Re-raise to trigger tenacity retry
        
        # For other errors, just return the message
        error_msg = f"Gemini Call failed: {error_str}"
        print(error_msg)
        return error_msg

def analyze_candlestick_chart(ticker: str, interval: str, chart_url: str) -> dict:
    """
    Analyzes the Candlestick chart + Volume. Returns JSON.
    """
    current_year = datetime.datetime.now().year
    system_prompt = CANDLESTICK_ANALYSIS_PROMPT.format(
        ticker=ticker,
        current_year=current_year
    )
    
    # Download Image
    image = get_image_from_url(chart_url)
    if not image:
        return {"error": "Failed to download chart image"}

    user_text = f"Asset Name: {ticker}\nChart URL: {chart_url}\n\nPlease perform the specific analysis requested."
    
    response_text = call_gemini(system_prompt, [user_text, image])
    
    return {
        "type": "CandlestickChartAnalysis",
        "content": response_text,
        "chart_url": chart_url
    }

def analyze_indicator(ticker: str, interval: str, indicator_name: str, chart_url: str) -> dict:
    """
    Analyzes a specific indicator chart.
    """
    base_prompt = INDICATOR_PROMPTS.get(indicator_name)
    if not base_prompt:
        return {"error": f"No prompt found for {indicator_name}"}
        
    system_prompt = base_prompt.format(ticker=ticker, interval=interval)
    
    # Download Image
    image = get_image_from_url(chart_url)
    if not image:
        return {"error": "Failed to download chart image"}
        
    user_text = f"Here is the {indicator_name} chart for {ticker}."
    
    response_text = call_gemini(system_prompt, [user_text, image])
    
    return {
        "type": "IndicatorAnalysis",
        "indicator": indicator_name,
        "content": response_text,
        "chart_url": chart_url
    }

def synthesize_reports(ticker: str, interval: str, reports: list) -> dict:
    """
    Synthesizes multiple analysis reports into one final JSON report.
    """
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")
    
    # Prune heavy content (like raw image bytes if we stored them) before JSON dump
    # Currently reports list is just text and URLs, so it is fine.
    reports_json_str = json.dumps(reports, indent=2)
    
    prompt = MASTER_SYNTHESIS_PROMPT.format(
        ticker=ticker,
        interval=interval,
        timestamp=f"{date_str} {time_str}",
        date=date_str,
        time=time_str,
        reports_json=reports_json_str
    )
    
    system_prompt = "You are a Master Financial Analyst. Output strictly valid JSON."
    
    response_text = call_gemini(system_prompt, [prompt], force_json=True)
    
    try:
        # Clean markdown code blocks if present (Gemini might still wrap in ```json even with mime_type)
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        return data
    except json.JSONDecodeError:
        print("Failed to decode synthesis JSON")
        return {"raw_output": response_text, "error": "JSON Decode Failed"}
