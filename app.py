import os
import requests
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Live AI Stock Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. BROWSER IMMUNITY HEADERS (Yahoo code bypass architecture)
custom_session = requests.Session()
custom_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
})

@app.get("/api/evaluate")
def evaluate_stock(ticker: str):
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker input empty")
        
    symbol = ticker.upper().strip().replace(" ", "")
    
    # Jio Financial Services ticker format handle
    if symbol in ["JIO", "JIOFINANCIAL", "JPL"]:
        symbol = "JIOFIN"
        
    if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        search_ticker = f"{symbol}.NS"
    else:
        search_ticker = symbol
        
    try:
        stock = yf.Ticker(search_ticker, session=custom_session)
        info = stock.info
        
        # Pull live price safely from daily history packet
        hist = stock.history(period="1d")
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found on NSE.")
            
        raw_price = hist['Close'].iloc[-1]
        current_price = f"{raw_price:,.2f}"

        # Fetch ratios with structured zero-fallbacks safely
        pe = info.get("trailingPE") or info.get("forwardPE") or 0
        peg = info.get("pegRatio") or 0
        pb = info.get("priceToBook") or 0
        div_yield = (info.get("dividendYield") or 0) * 100
        sales_growth = (info.get("revenueGrowth") or info.get("earningsGrowth") or 0) * 100
        opm = (info.get("operatingMargins") or 0) * 100
        roe = (info.get("returnOnEquity") or 0) * 100
        debt = (info.get("debtToEquity") or 0) / 100
        current_ratio = info.get("currentRatio") or 0
        promoter = (info.get("heldPercentInsiders") or 0) * 100

        metrics = [
            {"id": 1, "name": "P/E Ratio", "val": f"{pe:.2f}" if pe else "N/A", "status": "Pass" if 0 < pe < 30 else "Fail", "desc": "Ideal: < 30"},
            {"id": 2, "name": "PEG Ratio", "val": f"{peg:.2f}" if peg else "N/A", "status": "Pass" if 0 < peg < 1.0 else "Fail", "desc": "Ideal: < 1.0"},
            {"id": 3, "name": "P/B Ratio", "val": f"{pb:.2f}" if pb else "N/A", "status": "Pass" if pb < 2.0 else "Fail", "desc": "Ideal: < 2.0"},
            {"id": 4, "name": "Dividend Yield", "val": f"{div_yield:.2f}%" if div_yield else "0.00%", "status": "Pass" if div_yield >= 0 else "Fail", "desc": "Ideal: 1% to 5%"},
            {"id": 5, "name": "Sales Growth", "val": f"{sales_growth:.2f}%" if sales_growth else "N/A", "status": "Pass" if sales_growth >= 10 or sales_growth == 0 else "Fail", "desc": "Ideal: > 10%"},
            {"id": 6, "name": "Operating Margin", "val": f"{opm:.2f}%" if opm else "N/A", "status": "Pass" if opm >= 15 or opm == 0 else "Fail", "desc": "Ideal: > 15%"},
            {"id": 7, "name": "Debt-to-Equity", "val": f"{debt:.2f}" if debt else "0.00", "status": "Pass" if debt < 0.5 else "Fail", "desc": "Ideal: < 0.5"},
            {"id": 8, "name": "Current Ratio", "val": f"{current_ratio:.2f}" if current_ratio else "N/A", "status": "Pass" if current_ratio >= 1.5 or current_ratio == 0 else "Fail", "desc": "Ideal: > 1.5"},
            {"id": 9, "name": "Return on Equity", "val": f"{roe:.2f}%" if roe else "N/A", "status": "Pass" if roe >= 15 or roe == 0 else "Fail", "desc": "Ideal: > 15%"},
            {"id": 10, "name": "Promoter Holding", "val": f"{promoter:.2f}%" if promoter else "N/A", "status": "Pass" if promoter >= 50 or promoter == 0 else "Fail", "desc": "Ideal: > 50%"}
        ]
        
        passed = sum(1 for m in metrics if m["status"] == "Pass")
        verdict, color = ("STRONG BUY", "#34d399") if passed >= 6 else ("HOLD", "#fbbf24") if passed >= 4 else ("AVOID", "#f87171")
        
        return {
            "name": info.get("longName") or f"{symbol} Stock",
            "price": f"₹{current_price}",
            "verdict": verdict,
            "color": color,
            "score": f"{passed} / 10",
            "checklist": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Data fetch timeout. Valid NSE ticker use karein.")

@app.get("/", response_class=HTMLResponse)
def frontend():
    with open("index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())
