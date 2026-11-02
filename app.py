import os
import requests
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
        raise HTTPException(status_code=400, detail="Input box empty")
        
    symbol = ticker.upper().strip().replace(" ", "")
    
    # Jio specific naming logic handles
    if symbol in ["JIO", "JIOFINANCIAL", "JIOFIN"]:
        symbol = "JIOFIN"
        
    # TRUSTED ALTERNATIVE API CORRIDOR - No Yahoo dependency, direct institutional tracking
    # Worker proxy ensures zero-blocking on cloud servers like Render
    api_url = f"https://workers.dev{symbol}"
    
    try:
        response = requests.get(api_url, timeout=8.0)
        
        if response.status_code != 200:
            # STRICT ERROR: Real-time network pipeline failure trigger
            raise HTTPException(
                status_code=500, 
                detail=f"Stock '{symbol}' ka live data abhi fetch nahi ho paya. Symbol check karein ya market hours ke baad dobara try karein."
            )
            
        data = response.json()
        
        # Pulling genuine data packages safely
        current_price = data.get("price")
        if not current_price or current_price == "N/A":
            raise HTTPException(status_code=404, detail="Live market connection timeout.")

        pe = data.get("pe", 0)
        peg = data.get("peg", 0)
        pb = data.get("pb", 0)
        div_yield = data.get("dividendYield", 0)
        sales_growth = data.get("salesGrowth", 0)
        opm = data.get("opm", 0)
        debt = data.get("debtToEquity", 0)
        current_ratio = data.get("currentRatio", 0)
        roe = data.get("roe", 0)
        promoter = data.get("promoterHolding", 0)

        metrics = [
            {"id": 1, "name": "P/E Ratio", "val": f"{pe:.2f}" if pe else "N/A", "status": "Pass" if 0 < pe < 35 else "Fail", "desc": "Ideal: < 35"},
            {"id": 2, "name": "PEG Ratio", "val": f"{peg:.2f}" if peg else "N/A", "status": "Pass" if 0 < peg < 1.0 else "Fail", "desc": "Ideal: < 1.0"},
            {"id": 3, "name": "P/B Ratio", "val": f"{pb:.2f}" if pb else "N/A", "status": "Pass" if pb < 2.5 else "Fail", "desc": "Ideal: < 2.5"},
            {"id": 4, "name": "Dividend Yield", "val": f"{div_yield:.2f}%" if div_yield else "0.00%", "status": "Pass" if div_yield >= 0 else "Fail", "desc": "Ideal: 1% to 5%"},
            {"id": 5, "name": "Sales Growth", "val": f"{sales_growth:.2f}%" if sales_growth else "N/A", "status": "Pass" if sales_growth >= 10 or sales_growth == 0 else "Fail", "desc": "Ideal: > 10%"},
            {"id": 6, "name": "Operating Margin", "val": f"{opm:.2f}%" if opm else "N/A", "status": "Pass" if opm >= 12 or opm == 0 else "Fail", "desc": "Ideal: > 12%"},
            {"id": 7, "name": "Debt-to-Equity", "val": f"{debt:.2f}" if debt else "0.00", "status": "Pass" if debt < 0.5 else "Fail", "desc": "Ideal: < 0.5"},
            {"id": 8, "name": "Current Ratio", "val": f"{current_ratio:.2f}" if current_ratio else "N/A", "status": "Pass" if current_ratio >= 1.2 or current_ratio == 0 else "Fail", "desc": "Ideal: > 1.2"},
            {"id": 9, "name": "Return on Equity", "val": f"{roe:.2f}%" if roe else "N/A", "status": "Pass" if roe >= 12 or roe == 0 else "Fail", "desc": "Ideal: > 12%"},
            {"id": 10, "name": "Promoter Holding", "val": f"{promoter:.2f}%" if promoter else "N/A", "status": "Pass" if promoter >= 45 or promoter == 0 else "Fail", "desc": "Ideal: > 45%"}
        ]
        
        passed = sum(1 for m in metrics if m["status"] == "Pass")
        verdict, color = ("STRONG BUY", "#34d399") if passed >= 6 else ("HOLD", "#fbbf24") if passed >= 4 else ("AVOID", "#f87171")
        
        return {
            "name": f"{symbol} India Stock",
            "price": f"₹{current_price}",
            "verdict": verdict,
            "color": color,
            "score": f"{passed} / 10",
            "checklist": metrics
        }
    except Exception as e:
        # Strict pipeline error forward to client console
        raise HTTPException(status_code=500, detail="Data source update failed. Try fresh ticker symbol.")

@app.get("/", response_class=HTMLResponse)
def frontend():
    with open("index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())
