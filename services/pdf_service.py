from fpdf import FPDF
import requests
import os
import tempfile
from datetime import datetime

def clean_text(text):
    if not isinstance(text, str): return str(text)
    replacements = {
        "🟢": " ", "🔴": " ", "✅": "+", "❌": "-", "⚠️": "!", "🎯": "->", 
        "📉": "", "📈": "", "🧙‍♂️": "", "✨": "", "•": "-"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

class ReportPDF(FPDF):
    def __init__(self, ticker, interval):
        super().__init__()
        self.ticker = ticker
        self.interval = interval
        self.set_auto_page_break(auto=True, margin=15)
        # Standard fonts only to avoid missing file errors
        
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, f'Master AI Trader Report - {self.ticker} ({self.interval})', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, clean_text(title), 0, 1, 'L', fill=True)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Helvetica', '', 10)
        body = clean_text(body)
        self.multi_cell(0, 6, body)
        self.ln()
    
    def add_image_from_url(self, url, w=170):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    for chunk in response.iter_content(1024):
                        tmp.write(chunk)
                    tmp_path = tmp.name
                
                self.image(tmp_path, w=w, x=(210-w)/2) # Center image
                self.ln(5)
                os.unlink(tmp_path)
            else:
                self.cell(0, 10, "[Image Download Failed]", 0, 1)
        except Exception as e:
            self.cell(0, 10, f"[Image Error: {str(e)}]", 0, 1)

def generate_pdf(ticker, interval, final_json, reports):
    pdf = ReportPDF(ticker, interval)
    pdf.add_page()
    
    # Title Section
    pdf.set_font('Helvetica', 'B', 16)
    title = final_json.get("Title", "Technical Analysis Report")
    pdf.cell(0, 10, clean_text(title), 0, 1, 'C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 10, clean_text(f"Date: {final_json.get('Date')} | Time: {final_json.get('Time')}"), 0, 1, 'C')
    pdf.ln(5)

    # Verdict
    verdict = final_json.get("FinalVerdict", "NEUTRAL").upper()
    pdf.set_font('Helvetica', 'B', 14)
    if "BULL" in verdict:
        pdf.set_text_color(0, 128, 0)
    elif "BEAR" in verdict:
        pdf.set_text_color(128, 0, 0)
    pdf.cell(0, 10, clean_text(f"VERDICT: {verdict}"), 0, 1, 'C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # Executive Summary
    pdf.chapter_title("Executive Summary")
    pdf.chapter_body(final_json.get("AnalysisSummary", "No summary provided."))
    
    # Trade Setup
    setup = final_json.get("TradeSetup", {})
    if setup:
        pdf.chapter_title("Trade Idea")
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(40, 8, clean_text(f"Direction: {setup.get('Direction')}"), 0, 1)
        pdf.cell(40, 8, clean_text(f"Entry: {setup.get('EntryZone')}"), 0, 1)
        pdf.cell(40, 8, clean_text(f"Stop Loss: {setup.get('StopLoss')}"), 0, 1)
        pdf.cell(40, 8, clean_text(f"Take Profit: {setup.get('TakeProfit')}"), 0, 1)
        pdf.cell(40, 8, clean_text(f"R/R Ratio: {setup.get('RiskRewardRatio')}"), 0, 1)
        pdf.ln(5)

    # Confluence
    pdf.chapter_title("Confluence Factors")
    if final_json.get("BullishConfluence"):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 8, "Bullish:", 0, 1)
        pdf.set_font('Helvetica', '', 10)
        for item in final_json.get("BullishConfluence"):
            pdf.cell(5)
            pdf.cell(0, 6, clean_text(f"- {item}"), 0, 1)
    
    if final_json.get("BearishConfluence"):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 8, "Bearish:", 0, 1)
        pdf.set_font('Helvetica', '', 10)
        for item in final_json.get("BearishConfluence"):
            pdf.cell(5)
            pdf.cell(0, 6, clean_text(f"- {item}"), 0, 1)
    pdf.ln()

    # Detailed Reports
    for report in reports:
        pdf.add_page()
        name = "Candlestick Analysis" if report.get("type") == "CandlestickChartAnalysis" else f"{report.get('indicator')} Analysis"
        pdf.chapter_title(name)
        
        # Image
        if report.get("chart_url"):
            pdf.add_image_from_url(report.get("chart_url"))
            
        # Content
        # Gemini text usually contains markdown like ## headers. 
        # We'll just strip basic markdown for PDF cleanliness or dump it.
        # Minimal cleanup:
        content = report.get("content", "").replace("**", "").replace("## ", "").replace("### ", "")
        pdf.chapter_body(content)

    return bytes(pdf.output(dest='S')) # Return as bytes for Streamlit
