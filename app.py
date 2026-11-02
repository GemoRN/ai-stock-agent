import os
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

@app.get("/api/evaluate")
def evaluate_stock(ticker: str):
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker input empty")
        
    # Whitespace remove karein aur uppercase karein
    search_ticker = ticker.upper().strip()
    
    # Agar user ne space diya hai (jaise YES BANK), toh use join karein
    search_ticker = search_ticker.replace(" ", "")
    
    if not (search_ticker.endswith(".NS") or search_ticker.endswith(".BO")):
        search_ticker = f"{search_ticker}.NS"
        
    try:
        stock = yf.Ticker(search_ticker)
        
        # Safe handling for network limits
        try:
            info = stock.info
        except Exception:
            info = {}
            
        # Hard Fallback: Agar info empty hai toh history se details nikalenge
        current_price = "N/A"
        if info and (info.get('currentPrice') or info.get('regularMarketPrice')):
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        else:
            # History fallback method
            hist = stock.history(period="1d")
            if not hist.empty:
                current_price = round(hist['Close'].iloc[-1], 2)
            else:
                raise HTTPException(status_code=404, detail="Invalid Stock Symbol on NSE")

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
        
        if passed >= 6:
            verdict, color = "STRONG BUY", "#34d399"
        elif passed >= 4:
            verdict, color = "HOLD", "#fbbf24"
        else:
            verdict, color = "AVOID", "#f87171"
            
        return {
            "name": info.get("longName") or f"{search_ticker.replace('.NS', '')} Stock",
            "price": f"₹{current_price}",
            "verdict": verdict,
            "color": color,
            "score": f"{passed} / {len(metrics)}",
            "checklist": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Stock symbol galat hai ya market data server down hai.")

@app.get("/", response_class=HTMLResponse)
def frontend():
    with open("index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())
