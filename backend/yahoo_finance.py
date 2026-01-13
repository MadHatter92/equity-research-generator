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
        quarterly_balance_sheet = ticker.quarterly_balance_sheet

        # Get latest news
        try:
            news = ticker.news[:10] if ticker.news else []
        except:
            news = []

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

        # Process quarterly financials (last 4 quarters)
        if quarterly_financials is not None and not quarterly_financials.empty:
            stock_data["quarterly_results"] = process_quarterly_financials(quarterly_financials)

        # Add news
        stock_data["recent_news"] = []
        for article in news:
            try:
                stock_data["recent_news"].append({
                    "title": article.get("title", ""),
                    "publisher": article.get("publisher", ""),
                    "link": article.get("link", ""),
                    "published": article.get("providerPublishTime", 0),
                    "type": article.get("type", ""),
                })
            except:
                pass

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


def process_quarterly_financials(df) -> list:
    """Process quarterly financials into a list of quarter results."""
    quarters = []
    for col in df.columns[:4]:  # Last 4 quarters
        quarter_data = {
            "period": col.strftime("%b %Y") if hasattr(col, "strftime") else str(col),
        }
        for idx in df.index:
            value = df.loc[idx, col]
            if value is not None and not (isinstance(value, float) and value != value):
                # Clean up the key name
                key = str(idx).replace(" ", "_").lower()
                quarter_data[key] = float(value)
        quarters.append(quarter_data)
    return quarters


def search_stocks(query: str, limit: int = 10) -> list:
    """
    Search for Indian stocks matching the query.
    Returns list of matching tickers.
    """
    # Nifty 250 stocks (Nifty 100 + Nifty Midcap 150)
    indian_stocks = [
        # Nifty 50
        {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Oil & Gas"},
        {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT"},
        {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking"},
        {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking"},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
        {"symbol": "INFY", "name": "Infosys", "sector": "IT"},
        {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
        {"symbol": "ITC", "name": "ITC Limited", "sector": "FMCG"},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG"},
        {"symbol": "LT", "name": "Larsen & Toubro", "sector": "Infrastructure"},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Finance"},
        {"symbol": "HCLTECH", "name": "HCL Technologies", "sector": "IT"},
        {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Auto"},
        {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
        {"symbol": "ADANIENT", "name": "Adani Enterprises", "sector": "Conglomerate"},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking"},
        {"symbol": "TITAN", "name": "Titan Company", "sector": "Consumer"},
        {"symbol": "ONGC", "name": "Oil & Natural Gas Corp", "sector": "Oil & Gas"},
        {"symbol": "TATAMOTORS", "name": "Tata Motors", "sector": "Auto"},
        {"symbol": "AXISBANK", "name": "Axis Bank", "sector": "Banking"},
        {"symbol": "NTPC", "name": "NTPC Limited", "sector": "Power"},
        {"symbol": "DMART", "name": "Avenue Supermarts", "sector": "Retail"},
        {"symbol": "ADANIPORTS", "name": "Adani Ports", "sector": "Infrastructure"},
        {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "sector": "Cement"},
        {"symbol": "ASIANPAINT", "name": "Asian Paints", "sector": "Paints"},
        {"symbol": "COALINDIA", "name": "Coal India", "sector": "Mining"},
        {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv", "sector": "Finance"},
        {"symbol": "POWERGRID", "name": "Power Grid Corporation", "sector": "Power"},
        {"symbol": "NESTLEIND", "name": "Nestle India", "sector": "FMCG"},
        {"symbol": "WIPRO", "name": "Wipro", "sector": "IT"},
        {"symbol": "M&M", "name": "Mahindra & Mahindra", "sector": "Auto"},
        {"symbol": "JSWSTEEL", "name": "JSW Steel", "sector": "Steel"},
        {"symbol": "TATASTEEL", "name": "Tata Steel", "sector": "Steel"},
        {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance", "sector": "Insurance"},
        {"symbol": "SBILIFE", "name": "SBI Life Insurance", "sector": "Insurance"},
        {"symbol": "GRASIM", "name": "Grasim Industries", "sector": "Cement"},
        {"symbol": "LTIM", "name": "LTIMindtree", "sector": "IT"},
        {"symbol": "TECHM", "name": "Tech Mahindra", "sector": "IT"},
        {"symbol": "BRITANNIA", "name": "Britannia Industries", "sector": "FMCG"},
        {"symbol": "INDUSINDBK", "name": "IndusInd Bank", "sector": "Banking"},
        {"symbol": "HINDALCO", "name": "Hindalco Industries", "sector": "Metals"},
        {"symbol": "DIVISLAB", "name": "Divi's Laboratories", "sector": "Pharma"},
        {"symbol": "BPCL", "name": "Bharat Petroleum", "sector": "Oil & Gas"},
        {"symbol": "DRREDDY", "name": "Dr. Reddy's Labs", "sector": "Pharma"},
        {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals", "sector": "Healthcare"},
        {"symbol": "CIPLA", "name": "Cipla", "sector": "Pharma"},
        {"symbol": "EICHERMOT", "name": "Eicher Motors", "sector": "Auto"},
        {"symbol": "TATACONSUM", "name": "Tata Consumer Products", "sector": "FMCG"},
        {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp", "sector": "Auto"},
        {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto", "sector": "Auto"},
        # Nifty Next 50
        {"symbol": "ADANIGREEN", "name": "Adani Green Energy", "sector": "Power"},
        {"symbol": "ADANIPOWER", "name": "Adani Power", "sector": "Power"},
        {"symbol": "AMBUJACEM", "name": "Ambuja Cements", "sector": "Cement"},
        {"symbol": "ATGL", "name": "Adani Total Gas", "sector": "Gas"},
        {"symbol": "AWL", "name": "Adani Wilmar", "sector": "FMCG"},
        {"symbol": "BANKBARODA", "name": "Bank of Baroda", "sector": "Banking"},
        {"symbol": "BEL", "name": "Bharat Electronics", "sector": "Defence"},
        {"symbol": "BERGEPAINT", "name": "Berger Paints", "sector": "Paints"},
        {"symbol": "BIOCON", "name": "Biocon", "sector": "Pharma"},
        {"symbol": "BOSCHLTD", "name": "Bosch", "sector": "Auto Ancillary"},
        {"symbol": "CANBK", "name": "Canara Bank", "sector": "Banking"},
        {"symbol": "CHOLAFIN", "name": "Cholamandalam Finance", "sector": "Finance"},
        {"symbol": "COLPAL", "name": "Colgate-Palmolive", "sector": "FMCG"},
        {"symbol": "DLF", "name": "DLF Limited", "sector": "Real Estate"},
        {"symbol": "GAIL", "name": "GAIL India", "sector": "Gas"},
        {"symbol": "GODREJCP", "name": "Godrej Consumer Products", "sector": "FMCG"},
        {"symbol": "HAVELLS", "name": "Havells India", "sector": "Consumer Durables"},
        {"symbol": "HAL", "name": "Hindustan Aeronautics", "sector": "Defence"},
        {"symbol": "ICICIPRULI", "name": "ICICI Prudential Life", "sector": "Insurance"},
        {"symbol": "ICICIGI", "name": "ICICI Lombard", "sector": "Insurance"},
        {"symbol": "INDUSTOWER", "name": "Indus Towers", "sector": "Telecom"},
        {"symbol": "IOC", "name": "Indian Oil Corporation", "sector": "Oil & Gas"},
        {"symbol": "IRCTC", "name": "IRCTC", "sector": "Travel"},
        {"symbol": "JINDALSTEL", "name": "Jindal Steel & Power", "sector": "Steel"},
        {"symbol": "LICI", "name": "LIC India", "sector": "Insurance"},
        {"symbol": "LUPIN", "name": "Lupin", "sector": "Pharma"},
        {"symbol": "MARICO", "name": "Marico", "sector": "FMCG"},
        {"symbol": "MOTHERSON", "name": "Samvardhana Motherson", "sector": "Auto Ancillary"},
        {"symbol": "NAUKRI", "name": "Info Edge (Naukri)", "sector": "Internet"},
        {"symbol": "PFC", "name": "Power Finance Corporation", "sector": "Finance"},
        {"symbol": "PIDILITIND", "name": "Pidilite Industries", "sector": "Chemicals"},
        {"symbol": "PNB", "name": "Punjab National Bank", "sector": "Banking"},
        {"symbol": "RECLTD", "name": "REC Limited", "sector": "Finance"},
        {"symbol": "SHREECEM", "name": "Shree Cement", "sector": "Cement"},
        {"symbol": "SHRIRAMFIN", "name": "Shriram Finance", "sector": "Finance"},
        {"symbol": "SIEMENS", "name": "Siemens", "sector": "Capital Goods"},
        {"symbol": "SRF", "name": "SRF Limited", "sector": "Chemicals"},
        {"symbol": "TATAPOWER", "name": "Tata Power", "sector": "Power"},
        {"symbol": "TORNTPHARM", "name": "Torrent Pharma", "sector": "Pharma"},
        {"symbol": "TRENT", "name": "Trent", "sector": "Retail"},
        {"symbol": "UNIONBANK", "name": "Union Bank of India", "sector": "Banking"},
        {"symbol": "VEDL", "name": "Vedanta", "sector": "Metals"},
        {"symbol": "VBL", "name": "Varun Beverages", "sector": "Beverages"},
        {"symbol": "YESBANK", "name": "Yes Bank", "sector": "Banking"},
        {"symbol": "ZOMATO", "name": "Zomato", "sector": "Internet"},
        {"symbol": "ZYDUSLIFE", "name": "Zydus Lifesciences", "sector": "Pharma"},
        # Nifty Midcap 150 (selected)
        {"symbol": "AARTIIND", "name": "Aarti Industries", "sector": "Chemicals"},
        {"symbol": "ABB", "name": "ABB India", "sector": "Capital Goods"},
        {"symbol": "ABCAPITAL", "name": "Aditya Birla Capital", "sector": "Finance"},
        {"symbol": "ABFRL", "name": "Aditya Birla Fashion", "sector": "Retail"},
        {"symbol": "ACC", "name": "ACC Limited", "sector": "Cement"},
        {"symbol": "AFFLE", "name": "Affle India", "sector": "IT"},
        {"symbol": "AJANTPHARM", "name": "Ajanta Pharma", "sector": "Pharma"},
        {"symbol": "ALKEM", "name": "Alkem Laboratories", "sector": "Pharma"},
        {"symbol": "APLLTD", "name": "Alembic Pharma", "sector": "Pharma"},
        {"symbol": "APLAPOLLO", "name": "APL Apollo Tubes", "sector": "Steel"},
        {"symbol": "ASTRAL", "name": "Astral Limited", "sector": "Building Materials"},
        {"symbol": "ATUL", "name": "Atul Limited", "sector": "Chemicals"},
        {"symbol": "AUBANK", "name": "AU Small Finance Bank", "sector": "Banking"},
        {"symbol": "AUROPHARMA", "name": "Aurobindo Pharma", "sector": "Pharma"},
        {"symbol": "BALKRISIND", "name": "Balkrishna Industries", "sector": "Tyres"},
        {"symbol": "BANDHANBNK", "name": "Bandhan Bank", "sector": "Banking"},
        {"symbol": "BATAINDIA", "name": "Bata India", "sector": "Footwear"},
        {"symbol": "BHARATFORG", "name": "Bharat Forge", "sector": "Auto Ancillary"},
        {"symbol": "BHEL", "name": "Bharat Heavy Electricals", "sector": "Capital Goods"},
        {"symbol": "BIRLACORPN", "name": "Birla Corporation", "sector": "Cement"},
        {"symbol": "BSE", "name": "BSE Limited", "sector": "Financial Services"},
        {"symbol": "CANFINHOME", "name": "Can Fin Homes", "sector": "Finance"},
        {"symbol": "CASTROLIND", "name": "Castrol India", "sector": "Oil & Gas"},
        {"symbol": "CDSL", "name": "CDSL", "sector": "Financial Services"},
        {"symbol": "CENTRALBK", "name": "Central Bank of India", "sector": "Banking"},
        {"symbol": "CGPOWER", "name": "CG Power", "sector": "Capital Goods"},
        {"symbol": "CHAMBLFERT", "name": "Chambal Fertilizers", "sector": "Fertilizers"},
        {"symbol": "CLEAN", "name": "Clean Science", "sector": "Chemicals"},
        {"symbol": "COFORGE", "name": "Coforge", "sector": "IT"},
        {"symbol": "CONCOR", "name": "Container Corp", "sector": "Logistics"},
        {"symbol": "COROMANDEL", "name": "Coromandel International", "sector": "Fertilizers"},
        {"symbol": "CROMPTON", "name": "Crompton Greaves", "sector": "Consumer Durables"},
        {"symbol": "CUMMINSIND", "name": "Cummins India", "sector": "Capital Goods"},
        {"symbol": "CYIENT", "name": "Cyient", "sector": "IT"},
        {"symbol": "DABUR", "name": "Dabur India", "sector": "FMCG"},
        {"symbol": "DALBHARAT", "name": "Dalmia Bharat", "sector": "Cement"},
        {"symbol": "DEEPAKNTR", "name": "Deepak Nitrite", "sector": "Chemicals"},
        {"symbol": "DELTACORP", "name": "Delta Corp", "sector": "Hotels"},
        {"symbol": "DEVYANI", "name": "Devyani International", "sector": "QSR"},
        {"symbol": "DIXON", "name": "Dixon Technologies", "sector": "Consumer Durables"},
        {"symbol": "EMAMILTD", "name": "Emami", "sector": "FMCG"},
        {"symbol": "ENDURANCE", "name": "Endurance Technologies", "sector": "Auto Ancillary"},
        {"symbol": "ESCORTS", "name": "Escorts Kubota", "sector": "Auto"},
        {"symbol": "EXIDEIND", "name": "Exide Industries", "sector": "Auto Ancillary"},
        {"symbol": "FEDERALBNK", "name": "Federal Bank", "sector": "Banking"},
        {"symbol": "FORTIS", "name": "Fortis Healthcare", "sector": "Healthcare"},
        {"symbol": "GICRE", "name": "General Insurance Corp", "sector": "Insurance"},
        {"symbol": "GILLETTE", "name": "Gillette India", "sector": "FMCG"},
        {"symbol": "GLAXO", "name": "GlaxoSmithKline Pharma", "sector": "Pharma"},
        {"symbol": "GLENMARK", "name": "Glenmark Pharma", "sector": "Pharma"},
        {"symbol": "GMRINFRA", "name": "GMR Airports", "sector": "Infrastructure"},
        {"symbol": "GNFC", "name": "GNFC", "sector": "Fertilizers"},
        {"symbol": "GODREJIND", "name": "Godrej Industries", "sector": "Conglomerate"},
        {"symbol": "GODREJPROP", "name": "Godrej Properties", "sector": "Real Estate"},
        {"symbol": "GRANULES", "name": "Granules India", "sector": "Pharma"},
        {"symbol": "GRAPHITE", "name": "Graphite India", "sector": "Capital Goods"},
        {"symbol": "GSFC", "name": "Gujarat State Fertilizers", "sector": "Fertilizers"},
        {"symbol": "GSPL", "name": "Gujarat State Petronet", "sector": "Gas"},
        {"symbol": "GUJGASLTD", "name": "Gujarat Gas", "sector": "Gas"},
        {"symbol": "HDFCAMC", "name": "HDFC AMC", "sector": "Finance"},
        {"symbol": "HINDCOPPER", "name": "Hindustan Copper", "sector": "Metals"},
        {"symbol": "HINDPETRO", "name": "Hindustan Petroleum", "sector": "Oil & Gas"},
        {"symbol": "HINDZINC", "name": "Hindustan Zinc", "sector": "Metals"},
        {"symbol": "HONAUT", "name": "Honeywell Automation", "sector": "Capital Goods"},
        {"symbol": "IBREALEST", "name": "Indiabulls Real Estate", "sector": "Real Estate"},
        {"symbol": "IDFCFIRSTB", "name": "IDFC First Bank", "sector": "Banking"},
        {"symbol": "IEX", "name": "Indian Energy Exchange", "sector": "Financial Services"},
        {"symbol": "IGL", "name": "Indraprastha Gas", "sector": "Gas"},
        {"symbol": "IIFL", "name": "IIFL Finance", "sector": "Finance"},
        {"symbol": "INDHOTEL", "name": "Indian Hotels", "sector": "Hotels"},
        {"symbol": "INDIACEM", "name": "India Cements", "sector": "Cement"},
        {"symbol": "INDIAMART", "name": "IndiaMART", "sector": "Internet"},
        {"symbol": "INDIANB", "name": "Indian Bank", "sector": "Banking"},
        {"symbol": "IPCALAB", "name": "IPCA Laboratories", "sector": "Pharma"},
        {"symbol": "IRB", "name": "IRB Infrastructure", "sector": "Infrastructure"},
        {"symbol": "IRFC", "name": "Indian Railway Finance", "sector": "Finance"},
        {"symbol": "ISEC", "name": "ICICI Securities", "sector": "Finance"},
        {"symbol": "JKCEMENT", "name": "JK Cement", "sector": "Cement"},
        {"symbol": "JKLAKSHMI", "name": "JK Lakshmi Cement", "sector": "Cement"},
        {"symbol": "JMFINANCIL", "name": "JM Financial", "sector": "Finance"},
        {"symbol": "JSL", "name": "Jindal Stainless", "sector": "Steel"},
        {"symbol": "JSWENERGY", "name": "JSW Energy", "sector": "Power"},
        {"symbol": "JUBLFOOD", "name": "Jubilant FoodWorks", "sector": "QSR"},
        {"symbol": "JUSTDIAL", "name": "Just Dial", "sector": "Internet"},
        {"symbol": "KAJARIACER", "name": "Kajaria Ceramics", "sector": "Building Materials"},
        {"symbol": "KANSAINER", "name": "Kansai Nerolac", "sector": "Paints"},
        {"symbol": "KEI", "name": "KEI Industries", "sector": "Capital Goods"},
        {"symbol": "KIMS", "name": "Krishna Institute Medical", "sector": "Healthcare"},
        {"symbol": "KPITTECH", "name": "KPIT Technologies", "sector": "IT"},
        {"symbol": "KRBL", "name": "KRBL", "sector": "FMCG"},
        {"symbol": "L&TFH", "name": "L&T Finance", "sector": "Finance"},
        {"symbol": "LALPATHLAB", "name": "Dr Lal PathLabs", "sector": "Healthcare"},
        {"symbol": "LATENTVIEW", "name": "Latent View Analytics", "sector": "IT"},
        {"symbol": "LAURUSLABS", "name": "Laurus Labs", "sector": "Pharma"},
        {"symbol": "LICHSGFIN", "name": "LIC Housing Finance", "sector": "Finance"},
        {"symbol": "LTTS", "name": "L&T Technology Services", "sector": "IT"},
        {"symbol": "M&MFIN", "name": "Mahindra & Mahindra Finance", "sector": "Finance"},
        {"symbol": "MANAPPURAM", "name": "Manappuram Finance", "sector": "Finance"},
        {"symbol": "MANKIND", "name": "Mankind Pharma", "sector": "Pharma"},
        {"symbol": "MASFIN", "name": "MAS Financial Services", "sector": "Finance"},
        {"symbol": "MAXHEALTH", "name": "Max Healthcare", "sector": "Healthcare"},
        {"symbol": "MCX", "name": "Multi Commodity Exchange", "sector": "Financial Services"},
        {"symbol": "METROPOLIS", "name": "Metropolis Healthcare", "sector": "Healthcare"},
        {"symbol": "MFSL", "name": "Max Financial Services", "sector": "Insurance"},
        {"symbol": "MGL", "name": "Mahanagar Gas", "sector": "Gas"},
        {"symbol": "MPHASIS", "name": "Mphasis", "sector": "IT"},
        {"symbol": "MRF", "name": "MRF", "sector": "Tyres"},
        {"symbol": "MUTHOOTFIN", "name": "Muthoot Finance", "sector": "Finance"},
        {"symbol": "NAM-INDIA", "name": "Nippon Life AMC", "sector": "Finance"},
        {"symbol": "NATIONALUM", "name": "National Aluminium", "sector": "Metals"},
        {"symbol": "NATCOPHARM", "name": "Natco Pharma", "sector": "Pharma"},
        {"symbol": "NAUKRI", "name": "Info Edge", "sector": "Internet"},
        {"symbol": "NAVINFLUOR", "name": "Navin Fluorine", "sector": "Chemicals"},
        {"symbol": "NCC", "name": "NCC Limited", "sector": "Infrastructure"},
        {"symbol": "NHPC", "name": "NHPC", "sector": "Power"},
        {"symbol": "NMDC", "name": "NMDC", "sector": "Mining"},
        {"symbol": "OBEROIRLTY", "name": "Oberoi Realty", "sector": "Real Estate"},
        {"symbol": "OFSS", "name": "Oracle Financial Services", "sector": "IT"},
        {"symbol": "OIL", "name": "Oil India", "sector": "Oil & Gas"},
        {"symbol": "PAGEIND", "name": "Page Industries", "sector": "Textiles"},
        {"symbol": "PAYTM", "name": "One97 Communications", "sector": "Fintech"},
        {"symbol": "PERSISTENT", "name": "Persistent Systems", "sector": "IT"},
        {"symbol": "PETRONET", "name": "Petronet LNG", "sector": "Gas"},
        {"symbol": "PFIZER", "name": "Pfizer", "sector": "Pharma"},
        {"symbol": "PHOENIXLTD", "name": "Phoenix Mills", "sector": "Real Estate"},
        {"symbol": "PIIND", "name": "PI Industries", "sector": "Chemicals"},
        {"symbol": "POLICYBZR", "name": "PB Fintech", "sector": "Fintech"},
        {"symbol": "POLYCAB", "name": "Polycab India", "sector": "Capital Goods"},
        {"symbol": "POONAWALLA", "name": "Poonawalla Fincorp", "sector": "Finance"},
        {"symbol": "PRESTIGE", "name": "Prestige Estates", "sector": "Real Estate"},
        {"symbol": "PVRINOX", "name": "PVR Inox", "sector": "Entertainment"},
        {"symbol": "RADICO", "name": "Radico Khaitan", "sector": "Beverages"},
        {"symbol": "RAIN", "name": "Rain Industries", "sector": "Chemicals"},
        {"symbol": "RAJESHEXPO", "name": "Rajesh Exports", "sector": "Gems & Jewellery"},
        {"symbol": "RAMCOCEM", "name": "Ramco Cements", "sector": "Cement"},
        {"symbol": "RBLBANK", "name": "RBL Bank", "sector": "Banking"},
        {"symbol": "RELAXO", "name": "Relaxo Footwears", "sector": "Footwear"},
        {"symbol": "ROUTE", "name": "Route Mobile", "sector": "IT"},
        {"symbol": "SAIL", "name": "Steel Authority of India", "sector": "Steel"},
        {"symbol": "SANOFI", "name": "Sanofi India", "sector": "Pharma"},
        {"symbol": "SAPPHIRE", "name": "Sapphire Foods", "sector": "QSR"},
        {"symbol": "SCHAEFFLER", "name": "Schaeffler India", "sector": "Auto Ancillary"},
        {"symbol": "SJVN", "name": "SJVN", "sector": "Power"},
        {"symbol": "SKFINDIA", "name": "SKF India", "sector": "Capital Goods"},
        {"symbol": "SOBHA", "name": "Sobha Limited", "sector": "Real Estate"},
        {"symbol": "SONACOMS", "name": "Sona BLW Precision", "sector": "Auto Ancillary"},
        {"symbol": "STARHEALTH", "name": "Star Health Insurance", "sector": "Insurance"},
        {"symbol": "SUMICHEM", "name": "Sumitomo Chemical", "sector": "Chemicals"},
        {"symbol": "SUNPHARMA", "name": "Sun Pharma", "sector": "Pharma"},
        {"symbol": "SUNTV", "name": "Sun TV Network", "sector": "Media"},
        {"symbol": "SUPREMEIND", "name": "Supreme Industries", "sector": "Building Materials"},
        {"symbol": "SUVENPHAR", "name": "Suven Pharma", "sector": "Pharma"},
        {"symbol": "SYNGENE", "name": "Syngene International", "sector": "Pharma"},
        {"symbol": "TANLA", "name": "Tanla Platforms", "sector": "IT"},
        {"symbol": "TATACOMM", "name": "Tata Communications", "sector": "Telecom"},
        {"symbol": "TATAELXSI", "name": "Tata Elxsi", "sector": "IT"},
        {"symbol": "TATACHEM", "name": "Tata Chemicals", "sector": "Chemicals"},
        {"symbol": "TCIEXP", "name": "TCI Express", "sector": "Logistics"},
        {"symbol": "THERMAX", "name": "Thermax", "sector": "Capital Goods"},
        {"symbol": "TIINDIA", "name": "Tube Investments", "sector": "Auto Ancillary"},
        {"symbol": "TIMKEN", "name": "Timken India", "sector": "Capital Goods"},
        {"symbol": "TORNTPOWER", "name": "Torrent Power", "sector": "Power"},
        {"symbol": "TTML", "name": "Tata Teleservices", "sector": "Telecom"},
        {"symbol": "TV18BRDCST", "name": "TV18 Broadcast", "sector": "Media"},
        {"symbol": "TVSMOTOR", "name": "TVS Motor", "sector": "Auto"},
        {"symbol": "UBL", "name": "United Breweries", "sector": "Beverages"},
        {"symbol": "UCOBANK", "name": "UCO Bank", "sector": "Banking"},
        {"symbol": "UJJIVAN", "name": "Ujjivan Small Finance", "sector": "Banking"},
        {"symbol": "UPL", "name": "UPL Limited", "sector": "Chemicals"},
        {"symbol": "UTIAMC", "name": "UTI AMC", "sector": "Finance"},
        {"symbol": "VOLTAS", "name": "Voltas", "sector": "Consumer Durables"},
        {"symbol": "WELCORP", "name": "Welspun Corp", "sector": "Steel"},
        {"symbol": "WHIRLPOOL", "name": "Whirlpool of India", "sector": "Consumer Durables"},
        {"symbol": "ZEEL", "name": "Zee Entertainment", "sector": "Media"},
        {"symbol": "ZENSAR", "name": "Zensar Technologies", "sector": "IT"},
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
