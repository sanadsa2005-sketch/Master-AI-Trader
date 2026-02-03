import streamlit as st
import time
from services.chart_service import get_chart
from services.ai_service import analyze_candlestick_chart, analyze_indicator, synthesize_reports
from services.pdf_service import generate_pdf
from config import CHART_IMG_API_KEY, GEMINI_API_KEY

# Page Configuration
st.set_page_config(
    page_title="Master AI Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Premium" feel
st.markdown("""
<style>
    .report-title {
        color: #4CAF50;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: bold;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        height: 3em;
        width: 100%;
    }
    .stProgress .st-bo {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("🧙‍♂️ Master AI Trader")
    st.markdown("### professional Technical Analysis Powered by AI")

    # --- Sidebar Inputs ---
    with st.sidebar:
        st.header("Configuration")
        
        exchange = st.text_input("Exchange", value="BINANCE", help="e.g., BINANCE, COINBASE")
        ticker = st.text_input("Ticker Info", value="BTCUSDT", help="e.g., BTCUSDT, ETHUSD")
        interval = st.selectbox("Interval", ["15m", "1h", "4h", "1d", "1w"], index=2)
        theme = st.selectbox("Chart Theme", ["dark", "light"], index=0)

        st.subheader("Indicators")
        # Standard indicators available
        available_indicators = [
            "RSI", "MACD", "Volume", "Bollinger Bands", 
            "ATR", "OBV", "VWAP", "Stochastic RSI", 
            "Ichimoku Cloud", "MA Double"
        ]
        selected_indicators = st.multiselect(
            "Select Indicators for Analysis", 
            available_indicators,
            default=["RSI", "MACD", "Volume"]
        )
        
        # Check API Keys
        if not CHART_IMG_API_KEY or not GEMINI_API_KEY:
            st.error("Missing API Keys! Please check .env file.")
            st.stop()
            
        generate_btn = st.button("Generate Analysis")

    # --- Main Logic ---
    if generate_btn:
        if not ticker or not exchange:
            st.warning("Please enter Exchange and Ticker.")
            return

        status_container = st.container()
        results_container = st.container()

        reports = []

        try:
            # 1. Generate & Analyze Candlestick Chart (Base)
            with status_container:
                st.info("Step 1/3: Analyzing Price Action & Candlesticks...")
                
            # Generate Base Chart
            base_chart_url = get_chart(exchange, ticker, interval, "Candlestick", theme)
            
            # Use columns to show progress and chart preview
            col1, col2 = st.columns([1, 2])
            with col1:
                 st.image(base_chart_url, caption="Price Action", use_container_width=True)
            
            with col2:
                with st.spinner("AI Analyst is reviewing price action..."):
                    candlestick_report = analyze_candlestick_chart(ticker, interval, base_chart_url)
                    reports.append(candlestick_report)
                    st.success("Candlestick Analysis Complete")

            # 2. Parallel Indicator Analysis
            with status_container:
                st.info(f"Step 2/3: Analyzing {len(selected_indicators)} Indicators...")
            
            progress_bar = st.progress(0)
            
            for idx, ind in enumerate(selected_indicators):
                with st.spinner(f"Analyzing {ind}..."):
                    # Generate Chart for Indicator
                    chart_url = get_chart(exchange, ticker, interval, ind, theme)
                    
                    # Analyze
                    ind_report = analyze_indicator(ticker, interval, ind, chart_url)
                    reports.append(ind_report)
                    
                    # Update Progress
                    progress_bar.progress((idx + 1) / len(selected_indicators))
                    
                    # Polite delay for Free Tier
                    time.sleep(10)
            
            # 3. Final Synthesis
            with status_container:
                 st.info("Step 3/3: Synthesizing Final Report...")
                 
            with st.spinner("Master Analyst is compiling the final verdict..."):
                 final_json = synthesize_reports(ticker, interval, reports)
                 
            # --- Display Results ---
            status_container.empty() # Clear status
            
            with results_container:
                if final_json.get("error"):
                    st.error("Failed to generate report JSON.")
                    st.text(final_json.get("raw_output"))
                else:
                    display_final_report(final_json, reports)
                    
                    # --- PDF Download ---
                    with st.spinner("Generating PDF Report..."):
                         try:
                             pdf_bytes = generate_pdf(ticker, interval, final_json, reports)
                             
                             filename = f"Master_AI_Trader_{ticker}_{interval}_{final_json.get('Date')}.pdf"
                             st.download_button(
                                 label="📥 Download PDF Report",
                                 data=pdf_bytes,
                                 file_name=filename,
                                 mime="application/pdf"
                             )
                         except Exception as e:
                             st.error(f"Failed to generate PDF: {e}")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.exception(e)

def display_final_report(final_data: dict, raw_reports: list):
    """
    Renders the final stylish report.
    """
    st.markdown("---")
    st.header(final_data.get("Title", "Technical Analysis Report"))
    st.caption(f"Date: {final_data.get('Date')} | Time: {final_data.get('Time')}")
    
    # Verdict Banner
    verdict = final_data.get("FinalVerdict", "NEUTRAL").upper()
    color = "gray"
    if "BULL" in verdict: color = "green"
    if "BEAR" in verdict: color = "red"
    
    st.markdown(f"""
    <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 20px;">
        <h1 style="margin:0;">{verdict}</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Summary
    st.subheader("EXECUTIVE SUMMARY")
    st.write(final_data.get("AnalysisSummary"))
    
    # Trade Setup
    setup = final_data.get("TradeSetup", {})
    if setup:
        st.subheader("🎯 TRADE IDEA")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Direction", setup.get("Direction"))
        c2.metric("Entry", setup.get("EntryZone"))
        c3.metric("Stop Loss", setup.get("StopLoss"))
        c4.metric("Take Profit", setup.get("TakeProfit"))
        st.caption(f"Risk/Reward: {setup.get('RiskRewardRatio')}")

    # Confluence Factors
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("✅ Bullish Confluence")
        for p in final_data.get("BullishConfluence", []):
            st.markdown(f"- {p}")
            
    with c2:
        st.subheader("🔻 Bearish Confluence")
        for p in final_data.get("BearishConfluence", []):
            st.markdown(f"- {p}")
            
    if final_data.get("Contradictions"):
        st.warning(f"**Contradictions to Note:** {', '.join(final_data.get('Contradictions'))}")

    # Raw Reports Expander
    with st.expander("📂 View Individual Analysis Reports"):
        for report in raw_reports:
            st.markdown("---")
            if report.get("type") == "CandlestickChartAnalysis":
                st.subheader("Price Action Analysis")
            else:
                st.subheader(f"{report.get('indicator')} Analysis")
                
            st.image(report.get("chart_url"), width=600)
            st.markdown(report.get("content"))

if __name__ == "__main__":
    main()
