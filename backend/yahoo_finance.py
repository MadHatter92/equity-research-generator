import yfinance as yf
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

from config import NSE_SUFFIX, BSE_SUFFIX


def get_ticker_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Convert symbol to Yahoo Finance format for Indian stocks."""
    symbol = symbol.upper().strip()
    # Remove any existing suffix
    symbol = symbol.replace(".NS", "").replace(".BO", "")

    if exchange.upper() == "NSE":
        return f"{symbol}{NSE_SUFFIX}"
    elif exchange.upper() == "BSE":
        return f"{symbol}{BSE_SUFFIX}"
    return symbol


def fetch_stock_data(symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive stock data from Yahoo Finance.
    Returns structured data for report generation.
    """
    ticker_symbol = get_ticker_symbol(symbol, exchange)

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        # Check if we got valid data
        if not info or info.get("regularMarketPrice") is None:
            # Try the other exchange
            alt_exchange = "BSE" if exchange == "NSE" else "NSE"
            ticker_symbol = get_ticker_symbol(symbol, alt_exchange)
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                return None

        # Get historical data for charts
        hist = ticker.history(period="5y")

        # Get financials
        financials = ticker.financials
        balance_sheet = ticker.balance_sheet
        cashflow = ticker.cashflow
        quarterly_financials = ticker.quarterly_financials

        # Extract key data
        stock_data = {
            "basic_info": {
                "company_name": info.get("longName", info.get("shortName", symbol)),
                "ticker": symbol.upper(),
                "exchange": exchange,
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "website": info.get("website", ""),
                "description": info.get("longBusinessSummary", ""),
                "employees": info.get("fullTimeEmployees", 0),
                "country": info.get("country", "India"),
            },
            "price_info": {
                "current_price": info.get("regularMarketPrice", info.get("currentPrice", 0)),
                "previous_close": info.get("previousClose", 0),
                "open": info.get("regularMarketOpen", info.get("open", 0)),
                "day_high": info.get("dayHigh", 0),
                "day_low": info.get("dayLow", 0),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
                "volume": info.get("volume", 0),
                "avg_volume": info.get("averageVolume", 0),
            },
            "valuation": {
                "market_cap": info.get("marketCap", 0),
                "enterprise_value": info.get("enterpriseValue", 0),
                "pe_ratio": info.get("trailingPE", info.get("forwardPE", 0)),
                "forward_pe": info.get("forwardPE", 0),
                "peg_ratio": info.get("pegRatio", 0),
                "pb_ratio": info.get("priceToBook", 0),
                "ps_ratio": info.get("priceToSalesTrailing12Months", 0),
                "ev_to_ebitda": info.get("enterpriseToEbitda", 0),
                "ev_to_revenue": info.get("enterpriseToRevenue", 0),
            },
            "financials": {
                "revenue": info.get("totalRevenue", 0),
                "revenue_growth": info.get("revenueGrowth", 0),
                "gross_profit": info.get("grossProfits", 0),
                "ebitda": info.get("ebitda", 0),
                "operating_income": info.get("operatingIncome", 0),
                "net_income": info.get("netIncomeToCommon", 0),
                "profit_margin": info.get("profitMargins", 0),
                "operating_margin": info.get("operatingMargins", 0),
                "gross_margin": info.get("grossMargins", 0),
                "ebitda_margin": info.get("ebitdaMargins", 0),
            },
            "per_share": {
                "eps": info.get("trailingEps", 0),
                "forward_eps": info.get("forwardEps", 0),
                "book_value": info.get("bookValue", 0),
                "revenue_per_share": info.get("revenuePerShare", 0),
            },
            "dividends": {
                "dividend_rate": info.get("dividendRate", 0),
                "dividend_yield": info.get("dividendYield", 0),
                "payout_ratio": info.get("payoutRatio", 0),
                "ex_dividend_date": info.get("exDividendDate", None),
            },
            "balance_sheet": {
                "total_cash": info.get("totalCash", 0),
                "total_debt": info.get("totalDebt", 0),
                "debt_to_equity": info.get("debtToEquity", 0),
                "current_ratio": info.get("currentRatio", 0),
                "quick_ratio": info.get("quickRatio", 0),
                "total_assets": info.get("totalAssets", 0),
                "total_liabilities": info.get("totalLiabilities", 0),
            },
            "returns": {
                "roe": info.get("returnOnEquity", 0),
                "roa": info.get("returnOnAssets", 0),
            },
            "ownership": {
                "insider_holding": info.get("heldPercentInsiders", 0),
                "institution_holding": info.get("heldPercentInstitutions", 0),
            },
            "analyst_data": {
                "target_mean_price": info.get("targetMeanPrice", 0),
                "target_high_price": info.get("targetHighPrice", 0),
                "target_low_price": info.get("targetLowPrice", 0),
                "recommendation": info.get("recommendationKey", ""),
                "num_analysts": info.get("numberOfAnalystOpinions", 0),
            },
        }

        # Process historical financials if available
        if financials is not None and not financials.empty:
            stock_data["historical_financials"] = process_financials(financials)

        if balance_sheet is not None and not balance_sheet.empty:
            stock_data["historical_balance_sheet"] = process_financials(balance_sheet)

        if cashflow is not None and not cashflow.empty:
            stock_data["historical_cashflow"] = process_financials(cashflow)

        # Get historical prices for charts
        if not hist.empty:
            stock_data["price_history"] = {
                "dates": hist.index.strftime("%Y-%m-%d").tolist()[-252:],  # Last 1 year
                "prices": hist["Close"].tolist()[-252:],
                "volumes": hist["Volume"].tolist()[-252:],
            }

        return stock_data

    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return None


def process_financials(df) -> Dict[str, Dict[str, float]]:
    """Process financials DataFrame into a clean dictionary."""
    result = {}
    for col in df.columns:
        year = col.strftime("%Y") if hasattr(col, "strftime") else str(col)
        result[year] = {}
        for idx in df.index:
            value = df.loc[idx, col]
            if value is not None and not (isinstance(value, float) and value != value):  # Check for NaN
                result[year][str(idx)] = float(value)
    return result


def search_stocks(query: str, limit: int = 10) -> list:
    """
    Search for Indian stocks matching the query.
    Returns list of matching tickers.
    """
    # Common Indian stocks for search (in production, use a proper database/API)
    indian_stocks = [
        {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT"},
        {"symbol": "INFY", "name": "Infosys", "sector": "IT"},
        {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking"},
        {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Conglomerate"},
        {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking"},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG"},
        {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
        {"symbol": "ITC", "name": "ITC Limited", "sector": "FMCG"},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking"},
        {"symbol": "LT", "name": "Larsen & Toubro", "sector": "Infrastructure"},
        {"symbol": "AXISBANK", "name": "Axis Bank", "sector": "Banking"},
        {"symbol": "ASIANPAINT", "name": "Asian Paints", "sector": "Paints"},
        {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Auto"},
        {"symbol": "TITAN", "name": "Titan Company", "sector": "Consumer"},
        {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
        {"symbol": "WIPRO", "name": "Wipro", "sector": "IT"},
        {"symbol": "HCLTECH", "name": "HCL Technologies", "sector": "IT"},
        {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "sector": "Cement"},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Finance"},
        {"symbol": "TECHM", "name": "Tech Mahindra", "sector": "IT"},
        {"symbol": "NESTLEIND", "name": "Nestle India", "sector": "FMCG"},
        {"symbol": "TATAMOTORS", "name": "Tata Motors", "sector": "Auto"},
        {"symbol": "TATASTEEL", "name": "Tata Steel", "sector": "Steel"},
        {"symbol": "POWERGRID", "name": "Power Grid Corporation", "sector": "Power"},
        {"symbol": "NTPC", "name": "NTPC Limited", "sector": "Power"},
        {"symbol": "ONGC", "name": "Oil & Natural Gas Corp", "sector": "Oil & Gas"},
        {"symbol": "COALINDIA", "name": "Coal India", "sector": "Mining"},
        {"symbol": "JSWSTEEL", "name": "JSW Steel", "sector": "Steel"},
        {"symbol": "ADANIPORTS", "name": "Adani Ports", "sector": "Infrastructure"},
        {"symbol": "DRREDDY", "name": "Dr. Reddy's Labs", "sector": "Pharma"},
        {"symbol": "CIPLA", "name": "Cipla", "sector": "Pharma"},
        {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv", "sector": "Finance"},
        {"symbol": "DIVISLAB", "name": "Divi's Laboratories", "sector": "Pharma"},
        {"symbol": "BRITANNIA", "name": "Britannia Industries", "sector": "FMCG"},
        {"symbol": "GRASIM", "name": "Grasim Industries", "sector": "Cement"},
        {"symbol": "HINDALCO", "name": "Hindalco Industries", "sector": "Metals"},
        {"symbol": "INDUSINDBK", "name": "IndusInd Bank", "sector": "Banking"},
        {"symbol": "EICHERMOT", "name": "Eicher Motors", "sector": "Auto"},
        {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals", "sector": "Healthcare"},
    ]

    query = query.upper()
    results = []

    for stock in indian_stocks:
        if query in stock["symbol"] or query.lower() in stock["name"].lower():
            results.append(stock)
            if len(results) >= limit:
                break

    return results


def format_indian_number(num: float) -> str:
    """Format number in Indian style (lakhs, crores)."""
    if num is None or num == 0:
        return "0"

    abs_num = abs(num)
    sign = "-" if num < 0 else ""

    if abs_num >= 1e7:  # Crores
        return f"{sign}{abs_num/1e7:.2f} Cr"
    elif abs_num >= 1e5:  # Lakhs
        return f"{sign}{abs_num/1e5:.2f} L"
    elif abs_num >= 1e3:  # Thousands
        return f"{sign}{abs_num/1e3:.2f} K"
    else:
        return f"{sign}{abs_num:.2f}"


def format_market_cap(market_cap: float) -> str:
    """Format market cap in Indian style."""
    if market_cap is None or market_cap == 0:
        return "N/A"

    if market_cap >= 1e12:  # Lakh Crores
        return f"₹{market_cap/1e12:.2f}L Cr"
    elif market_cap >= 1e9:  # Thousand Crores
        return f"₹{market_cap/1e7:.0f} Cr"
    elif market_cap >= 1e7:  # Crores
        return f"₹{market_cap/1e7:.2f} Cr"
    else:
        return f"₹{market_cap/1e5:.2f} L"


def calculate_upside(current_price: float, target_price: float) -> float:
    """Calculate upside percentage."""
    if current_price and target_price and current_price > 0:
        return ((target_price - current_price) / current_price) * 100
    return 0
