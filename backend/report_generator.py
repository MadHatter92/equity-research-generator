import anthropic
import json
from typing import Dict, Any, Optional
from datetime import datetime

from config import ANTHROPIC_API_KEY
from yahoo_finance import format_market_cap, format_indian_number, calculate_upside


def generate_ai_analysis(stock_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use Claude to generate investment analysis based on stock data.
    Returns structured analysis for the report.
    """
    if not ANTHROPIC_API_KEY:
        return generate_fallback_analysis(stock_data)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Prepare data summary for Claude
    data_summary = prepare_data_summary(stock_data)

    prompt = f"""You are a HIGHLY OPINIONATED senior equity research analyst at a top investment bank. You have strong convictions and are not afraid to make bold calls. Your reputation is built on taking clear, decisive stances - not wishy-washy "hold" recommendations.

You're also known for your ENGAGING writing style. You open every report with a hook that grabs attention - either an anecdote, a recent company event described in everyday terms, or a clever analogy comparing the company to something relatable.

STOCK DATA:
{json.dumps(data_summary, indent=2)}

YOUR TASK: Generate a STRONG, OPINIONATED investment thesis. Take a clear stance - either you love this stock or you don't. Avoid fence-sitting.

CRITICAL INSTRUCTIONS:
1. OPENING HOOK: Start with ONE of these (pick the most compelling for this stock):
   - An anecdote that illustrates the company's position or recent performance
   - A recent company event/news described in simple, everyday language (like explaining to a friend)
   - A vivid analogy comparing this company to its peers (e.g., "If HDFC Bank is the reliable family sedan, this bank is...")
   The hook should be 2-3 sentences, conversational, and set up your investment thesis.
2. BE DECISIVE: If the fundamentals are good, give a strong BUY with conviction. If they're bad, give a clear SELL. Only use HOLD if truly mixed.
3. USE THE NEWS: Reference the recent news headlines to support your thesis. What are the catalysts or red flags?
4. ANALYZE QUARTERLY TRENDS: Look at the last 4 quarters. Is revenue/profit growing or declining? This is CRUCIAL.
5. BE SPECIFIC: Use actual numbers from the data. Don't be vague.
6. HAVE CONVICTION: Write like you're putting your own money on this call.

Return your analysis in this JSON format:
{{
    "recommendation": "STRONG BUY" or "BUY" or "HOLD" or "SELL" or "STRONG SELL",
    "conviction_level": "HIGH" or "MEDIUM" or "LOW",
    "target_price": <number - your 12-month target price>,
    "opening_hook": "<2-3 sentence engaging opener: an anecdote, recent event in everyday terms, or analogy with peers. Make it memorable and conversational.>",
    "investment_thesis": "<3-4 sentence STRONG thesis. Start with your conviction: 'We are bullish/bearish on X because...' Be specific about catalysts.>",
    "quarterly_analysis": "<Analysis of last quarter results. Was it a beat or miss? What's the trend?>",
    "news_impact": "<How recent news affects your view. Reference specific headlines.>",
    "bull_case": [
        "<specific point with numbers>",
        "<specific point with numbers>",
        "<specific point with numbers>",
        "<specific point with numbers>"
    ],
    "bear_case": [
        "<specific concern with context>",
        "<specific concern with context>",
        "<specific concern with context>"
    ],
    "key_risks": [
        {{
            "title": "<risk title>",
            "description": "<detailed risk with potential impact>",
            "probability": "HIGH" or "MEDIUM" or "LOW"
        }},
        {{
            "title": "<risk title>",
            "description": "<detailed risk with potential impact>",
            "probability": "HIGH" or "MEDIUM" or "LOW"
        }}
    ],
    "business_analysis": "<paragraph with STRONG opinions on business model, moat, and competitive position>",
    "financial_analysis": "<paragraph analyzing margins, growth trajectory, and what the numbers REALLY tell us>",
    "valuation_analysis": "<paragraph on whether this is CHEAP or EXPENSIVE. Use PE, PB, compare to growth rate. Be definitive.>",
    "competitive_advantages": [
        {{
            "title": "<moat name>",
            "description": "<why this matters>"
        }}
    ],
    "catalysts": [
        "<upcoming event or trigger that could move the stock>"
    ],
    "price_action_note": "<brief comment on where the stock is trading relative to 52-week range>"
}}

Remember: Great analysts have OPINIONS. Don't hedge everything. Take a stand!
Return ONLY valid JSON, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract JSON from response
        response_text = response.content[0].text.strip()

        # Try to parse JSON
        # Handle cases where response might have markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        analysis = json.loads(response_text)
        return analysis

    except Exception as e:
        print(f"Error generating AI analysis: {str(e)}")
        return generate_fallback_analysis(stock_data)


def prepare_data_summary(stock_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare a clean summary of stock data for AI analysis."""
    basic = stock_data.get("basic_info", {})
    price = stock_data.get("price_info", {})
    valuation = stock_data.get("valuation", {})
    financials = stock_data.get("financials", {})
    returns = stock_data.get("returns", {})
    balance = stock_data.get("balance_sheet", {})
    per_share = stock_data.get("per_share", {})
    dividends = stock_data.get("dividends", {})
    analyst = stock_data.get("analyst_data", {})
    quarterly = stock_data.get("quarterly_results", [])
    news = stock_data.get("recent_news", [])

    # Format news for the AI
    news_summary = []
    for article in news[:7]:  # Top 7 news items
        if article.get("title"):
            news_summary.append({
                "headline": article.get("title"),
                "source": article.get("publisher", "Unknown"),
            })

    # Calculate price position in 52-week range
    current = price.get("current_price", 0)
    low_52 = price.get("fifty_two_week_low", 0)
    high_52 = price.get("fifty_two_week_high", 0)
    if high_52 and low_52 and high_52 != low_52:
        position_in_range = ((current - low_52) / (high_52 - low_52)) * 100
    else:
        position_in_range = 50

    return {
        "company_name": basic.get("company_name"),
        "sector": basic.get("sector"),
        "industry": basic.get("industry"),
        "description": basic.get("description", "")[:500],
        "current_price": price.get("current_price"),
        "52_week_high": price.get("fifty_two_week_high"),
        "52_week_low": price.get("fifty_two_week_low"),
        "position_in_52week_range_pct": round(position_in_range, 1),
        "market_cap_inr": valuation.get("market_cap"),
        "pe_ratio": valuation.get("pe_ratio"),
        "pb_ratio": valuation.get("pb_ratio"),
        "ev_to_ebitda": valuation.get("ev_to_ebitda"),
        "peg_ratio": valuation.get("peg_ratio"),
        "revenue": financials.get("revenue"),
        "revenue_growth": financials.get("revenue_growth"),
        "profit_margin": financials.get("profit_margin"),
        "operating_margin": financials.get("operating_margin"),
        "ebitda_margin": financials.get("ebitda_margin"),
        "roe": returns.get("roe"),
        "roa": returns.get("roa"),
        "debt_to_equity": balance.get("debt_to_equity"),
        "current_ratio": balance.get("current_ratio"),
        "eps": per_share.get("eps"),
        "book_value": per_share.get("book_value"),
        "dividend_yield": dividends.get("dividend_yield"),
        "analyst_target_price": analyst.get("target_mean_price"),
        "analyst_recommendation": analyst.get("recommendation"),
        "quarterly_results": quarterly[:4] if quarterly else [],
        "recent_news": news_summary,
    }


def generate_fallback_analysis(stock_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate basic analysis when AI is unavailable."""
    basic = stock_data.get("basic_info", {})
    price = stock_data.get("price_info", {})
    valuation = stock_data.get("valuation", {})
    financials = stock_data.get("financials", {})
    returns = stock_data.get("returns", {})
    analyst = stock_data.get("analyst_data", {})

    current_price = price.get("current_price", 0)
    pe_ratio = valuation.get("pe_ratio", 0)
    roe = returns.get("roe", 0)

    # Simple recommendation logic
    if pe_ratio and pe_ratio < 15 and roe and roe > 0.15:
        recommendation = "BUY"
    elif pe_ratio and pe_ratio > 40:
        recommendation = "SELL"
    else:
        recommendation = "HOLD"

    # Simple target price (use analyst target or 10% upside)
    analyst_target = analyst.get("target_mean_price", 0)
    if analyst_target and analyst_target > 0:
        target_price = analyst_target
    else:
        target_price = current_price * 1.10 if current_price else 0

    return {
        "recommendation": recommendation,
        "conviction_level": "MEDIUM",
        "target_price": round(target_price, 2),
        "investment_thesis": f"{basic.get('company_name', 'This company')} operates in the {basic.get('sector', 'N/A')} sector. Based on current valuations and financial metrics, the stock appears to be fairly valued.",
        "quarterly_analysis": "Quarterly financial data analysis is not available. Please refer to the company's investor relations for the latest quarterly results.",
        "news_impact": "Recent news and its impact on the stock could not be analyzed at this time.",
        "catalysts": [
            "Upcoming quarterly earnings announcement",
            "Sector-wide policy changes",
            "Management commentary on guidance"
        ],
        "price_action_note": f"The stock is currently trading within its 52-week range.",
        "bull_case": [
            f"Established player in {basic.get('sector', 'its')} sector",
            "Consistent financial performance",
            "Potential for growth in current market conditions",
            "Reasonable valuation metrics"
        ],
        "bear_case": [
            "Market volatility could impact short-term performance",
            "Competition from industry peers",
            "Macroeconomic headwinds"
        ],
        "key_risks": [
            {
                "title": "Market Risk",
                "description": "General market volatility and economic conditions could impact stock performance.",
                "probability": "MEDIUM"
            },
            {
                "title": "Industry Risk",
                "description": f"Changes in the {basic.get('sector', 'industry')} sector could affect the company's competitive position.",
                "probability": "MEDIUM"
            }
        ],
        "business_analysis": f"{basic.get('company_name', 'The company')} operates in the {basic.get('industry', basic.get('sector', 'N/A'))} space. The business model appears stable with ongoing operations across its core segments.",
        "financial_analysis": f"The company shows {'strong' if roe and roe > 0.15 else 'moderate'} profitability metrics. {'ROE is healthy indicating efficient use of shareholder capital.' if roe and roe > 0.15 else 'Returns metrics are in line with industry standards.'}",
        "valuation_analysis": f"At current P/E of {pe_ratio:.1f}x, the stock {'appears reasonably valued' if pe_ratio and 15 < pe_ratio < 30 else 'may be overvalued' if pe_ratio and pe_ratio > 30 else 'appears attractively valued'}.",
        "competitive_advantages": [
            {
                "title": "Market Position",
                "description": f"Established presence in the {basic.get('sector', 'industry')} sector"
            }
        ]
    }


def generate_report_html(stock_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Generate the complete HTML report."""

    basic = stock_data.get("basic_info", {})
    price = stock_data.get("price_info", {})
    valuation = stock_data.get("valuation", {})
    financials = stock_data.get("financials", {})
    returns = stock_data.get("returns", {})
    balance = stock_data.get("balance_sheet", {})
    per_share = stock_data.get("per_share", {})
    dividends = stock_data.get("dividends", {})
    ownership = stock_data.get("ownership", {})

    current_price = price.get("current_price", 0)
    target_price = analysis.get("target_price", current_price * 1.1)
    upside = calculate_upside(current_price, target_price)
    recommendation = analysis.get("recommendation", "HOLD")

    # Format values
    market_cap_formatted = format_market_cap(valuation.get("market_cap", 0))
    pe_ratio = valuation.get("pe_ratio", 0) or 0
    pb_ratio = valuation.get("pb_ratio", 0) or 0
    dividend_yield = (dividends.get("dividend_yield", 0) or 0) * 100
    roe = (returns.get("roe", 0) or 0) * 100
    fifty_two_week_low = price.get("fifty_two_week_low", 0)
    fifty_two_week_high = price.get("fifty_two_week_high", 0)

    # Generate bull points HTML
    bull_points = "\n".join([f"<li>{point}</li>" for point in analysis.get("bull_case", [])])
    bear_points = "\n".join([f"<li>{point}</li>" for point in analysis.get("bear_case", [])])

    # Generate risk items HTML
    risk_items = ""
    for risk in analysis.get("key_risks", []):
        risk_items += f'''
        <div class="risk-item">
            <span class="risk-icon">&#9888;</span>
            <div>
                <strong>{risk.get("title", "Risk")}:</strong> {risk.get("description", "")}
            </div>
        </div>
        '''

    # Generate competitive advantages HTML
    moat_cards = ""
    colors = ["var(--primary)", "var(--secondary)", "var(--warning)", "#9f7aea"]
    for i, moat in enumerate(analysis.get("competitive_advantages", [])):
        color = colors[i % len(colors)]
        moat_cards += f'''
        <div style="background: var(--bg-light); padding: 1.25rem; border-radius: 8px; border-left: 4px solid {color};">
            <strong style="color: var(--primary);">{moat.get("title", "")}</strong>
            <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.5rem;">{moat.get("description", "")}</p>
        </div>
        '''

    # Recommendation color class
    rec_class = recommendation.lower().replace(" ", "-")  # Handle "strong buy" etc.

    # Get new opinionated fields
    conviction_level = analysis.get("conviction_level", "MEDIUM")
    quarterly_analysis = analysis.get("quarterly_analysis", "")
    news_impact = analysis.get("news_impact", "")
    catalysts = analysis.get("catalysts", [])
    price_action_note = analysis.get("price_action_note", "")

    # Generate catalysts HTML
    catalysts_html = ""
    for catalyst in catalysts:
        catalysts_html += f'<li>{catalyst}</li>'

    report_date = datetime.now().strftime("%B %d, %Y")

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{basic.get("company_name", "Company")} - Equity Research Report | Permabullish</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --primary: #1e3a5f;
            --primary-light: #243b53;
            --primary-dark: #102a43;
            --secondary: #38a169;
            --accent: #e8913a;
            --accent-hover: #d97316;
            --accent-light: #fdecd4;
            --danger: #e53e3e;
            --warning: #e8913a;
            --bg-light: #f7fafc;
            --bg-card: #ffffff;
            --text-primary: #1a202c;
            --text-secondary: #4a5568;
            --text-muted: #718096;
            --border: #e2e8f0;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }}

        body {{
            font-family: 'DM Sans', 'Inter', system-ui, -apple-system, sans-serif;
            background: var(--bg-light);
            color: var(--text-primary);
            line-height: 1.6;
        }}

        .font-display {{
            font-family: 'DM Serif Display', Georgia, serif;
        }}

        .nav {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
            padding: 0 2rem;
            z-index: 1000;
            box-shadow: var(--shadow-lg);
        }}

        .nav-content {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 64px;
        }}

        .nav-brand {{
            color: white;
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .nav-brand .font-display {{
            font-family: 'DM Serif Display', Georgia, serif;
        }}

        .nav-brand .ticker {{
            background: rgba(255,255,255,0.2);
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-family: 'DM Sans', system-ui, sans-serif;
        }}

        .nav-links {{
            display: flex;
            gap: 0.5rem;
        }}

        .nav-link {{
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.875rem;
            transition: all 0.2s;
        }}

        .nav-link:hover, .nav-link.active {{
            background: rgba(255,255,255,0.15);
            color: white;
        }}

        .header {{
            margin-top: 64px;
            background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 50%, var(--primary-light) 100%);
            color: white;
            padding: 3rem 2rem;
        }}

        .header-content {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 2rem;
        }}

        .company-info h1 {{
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        .company-meta {{
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
            font-size: 0.95rem;
            opacity: 0.9;
        }}

        .recommendation-box {{
            text-align: center;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 1.5rem 2.5rem;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.2);
        }}

        .recommendation {{
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        .recommendation.buy, .recommendation.strong-buy {{ color: #68d391; }}
        .recommendation.hold {{ color: #f6e05e; }}
        .recommendation.sell, .recommendation.strong-sell {{ color: #fc8181; }}

        .conviction-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 0.5rem;
        }}

        .conviction-badge.high {{
            background: rgba(72, 187, 120, 0.2);
            color: #68d391;
        }}

        .conviction-badge.medium {{
            background: rgba(246, 224, 94, 0.2);
            color: #f6e05e;
        }}

        .conviction-badge.low {{
            background: rgba(252, 129, 129, 0.2);
            color: #fc8181;
        }}

        .catalyst-list li {{
            padding: 0.5rem 0;
            padding-left: 1.5rem;
            position: relative;
            color: var(--text-primary);
        }}

        .catalyst-list li::before {{
            content: '⚡';
            position: absolute;
            left: 0;
            top: 0.5rem;
        }}

        .price-info {{
            font-size: 0.9rem;
            opacity: 0.9;
        }}

        .price-current {{
            font-size: 1.5rem;
            font-weight: 600;
        }}

        .metrics-strip {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid rgba(255,255,255,0.2);
        }}

        .metric-item {{
            text-align: center;
            padding: 1rem;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            transition: transform 0.2s, background 0.2s;
        }}

        .metric-item:hover {{
            transform: translateY(-2px);
            background: rgba(255,255,255,0.1);
        }}

        .metric-label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.8;
            margin-bottom: 0.25rem;
        }}

        .metric-value {{
            font-size: 1.25rem;
            font-weight: 600;
        }}

        .main {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .section {{
            background: var(--bg-card);
            border-radius: 12px;
            box-shadow: var(--shadow);
            margin-bottom: 1.5rem;
            overflow: hidden;
            border: 1px solid var(--border);
        }}

        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.25rem 1.5rem;
            background: linear-gradient(to right, var(--bg-light), transparent);
            cursor: pointer;
            transition: background 0.2s;
            user-select: none;
        }}

        .section-header:hover {{
            background: var(--bg-light);
        }}

        .section-title {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--primary);
        }}

        .section-icon {{
            width: 32px;
            height: 32px;
            background: var(--primary);
            color: white;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.875rem;
        }}

        .section-toggle {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s;
        }}

        .section.collapsed .section-toggle {{
            transform: rotate(-90deg);
        }}

        .section-content {{
            padding: 1.5rem;
            border-top: 1px solid var(--border);
            max-height: 2000px;
            overflow: hidden;
            transition: max-height 0.4s ease, padding 0.4s ease, opacity 0.3s ease;
            opacity: 1;
        }}

        .section.collapsed .section-content {{
            max-height: 0;
            padding-top: 0;
            padding-bottom: 0;
            opacity: 0;
        }}

        .thesis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }}

        .thesis-card {{
            padding: 1.25rem;
            border-radius: 8px;
            border-left: 4px solid;
        }}

        .thesis-card.bull {{
            background: linear-gradient(to right, #f0fff4, transparent);
            border-color: var(--secondary);
        }}

        .thesis-card.bear {{
            background: linear-gradient(to right, #fff5f5, transparent);
            border-color: var(--danger);
        }}

        .thesis-card h4 {{
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.75rem;
            color: var(--text-secondary);
        }}

        .thesis-card ul {{
            list-style: none;
        }}

        .thesis-card li {{
            padding: 0.5rem 0;
            padding-left: 1.5rem;
            position: relative;
            color: var(--text-primary);
        }}

        .thesis-card li::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0.9rem;
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}

        .thesis-card.bull li::before {{ background: var(--secondary); }}
        .thesis-card.bear li::before {{ background: var(--danger); }}

        .risks-container {{
            margin-top: 1.5rem;
        }}

        .risk-item {{
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            padding: 1rem;
            background: var(--accent-light);
            border-radius: 8px;
            margin-bottom: 0.75rem;
            border-left: 3px solid var(--accent);
        }}

        .risk-icon {{
            color: var(--accent);
            font-size: 1.25rem;
        }}

        .business-desc {{
            color: var(--text-secondary);
            margin-bottom: 1.5rem;
            font-size: 1rem;
            line-height: 1.8;
        }}

        .valuation-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .valuation-card {{
            background: var(--bg-light);
            padding: 1.25rem;
            border-radius: 8px;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .valuation-card:hover {{
            transform: translateY(-3px);
            box-shadow: var(--shadow);
        }}

        .valuation-metric {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }}

        .valuation-value {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--primary);
        }}

        .disclaimer {{
            background: var(--bg-light);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.7;
        }}

        .disclaimer h4 {{
            color: var(--primary);
            margin-bottom: 0.75rem;
        }}

        @media (max-width: 768px) {{
            .nav-links {{ display: none; }}
            .header-top {{ flex-direction: column; }}
            .recommendation-box {{ width: 100%; }}
        }}

        @media print {{
            .nav {{ display: none; }}
            .header {{ margin-top: 0; }}
            .section.collapsed .section-content {{
                max-height: none;
                opacity: 1;
                padding: 1.5rem;
            }}
        }}
    </style>
</head>
<body>
    <nav class="nav">
        <div class="nav-content">
            <div class="nav-brand">
                <span class="font-display">Perma<span style="color: #e8913a;">bullish</span></span>
                <span class="ticker">{basic.get("ticker", "")}</span>
            </div>
            <div class="nav-links">
                <a href="#summary" class="nav-link active">Summary</a>
                <a href="#quarterly" class="nav-link">Quarterly</a>
                <a href="#news-catalysts" class="nav-link">News</a>
                <a href="#financials" class="nav-link">Financials</a>
                <a href="#valuation" class="nav-link">Valuation</a>
            </div>
        </div>
    </nav>

    <header class="header">
        <div class="header-content">
            <div class="header-top">
                <div class="company-info">
                    <h1>{basic.get("company_name", "Company")}</h1>
                    <div class="company-meta">
                        <span>{basic.get("sector", "N/A")}</span>
                        <span>|</span>
                        <span>NSE: {basic.get("ticker", "")} | BSE: {basic.get("ticker", "")}</span>
                        <span>|</span>
                        <span>Report Date: {report_date}</span>
                    </div>
                </div>
                <div class="recommendation-box">
                    <div class="recommendation {rec_class}">{recommendation}</div>
                    <div class="conviction-badge {conviction_level.lower()}">{conviction_level} Conviction</div>
                    <div class="price-info">
                        <div>CMP: <span class="price-current">₹{current_price:,.2f}</span></div>
                        <div>Target: ₹{target_price:,.0f} | Upside: {upside:.1f}%</div>
                    </div>
                </div>
            </div>

            <div class="metrics-strip">
                <div class="metric-item">
                    <div class="metric-label">Market Cap</div>
                    <div class="metric-value">{market_cap_formatted}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">P/E Ratio</div>
                    <div class="metric-value">{pe_ratio:.1f}x</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">P/B Ratio</div>
                    <div class="metric-value">{pb_ratio:.1f}x</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Dividend Yield</div>
                    <div class="metric-value">{dividend_yield:.1f}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">52W Range</div>
                    <div class="metric-value">₹{fifty_two_week_low:,.0f} - ₹{fifty_two_week_high:,.0f}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">ROE</div>
                    <div class="metric-value">{roe:.1f}%</div>
                </div>
            </div>
        </div>
    </header>

    <main class="main">
        <!-- Investment Summary -->
        <section class="section" id="summary">
            <div class="section-header" onclick="toggleSection(this)">
                <div class="section-title">
                    <div class="section-icon">1</div>
                    Investment Summary
                </div>
                <div class="section-toggle">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 4L6 8L10 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <p class="business-desc">{analysis.get("investment_thesis", "")}</p>

                <div class="thesis-grid">
                    <div class="thesis-card bull">
                        <h4>Bull Case</h4>
                        <ul>
                            {bull_points}
                        </ul>
                    </div>
                    <div class="thesis-card bear">
                        <h4>Bear Case</h4>
                        <ul>
                            {bear_points}
                        </ul>
                    </div>
                </div>

                <div class="risks-container">
                    <h4 style="color: var(--text-secondary); margin-bottom: 1rem; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.5px;">Key Risks to Monitor</h4>
                    {risk_items}
                </div>
            </div>
        </section>

        <!-- Quarterly Results Analysis -->
        <section class="section" id="quarterly">
            <div class="section-header" onclick="toggleSection(this)">
                <div class="section-title">
                    <div class="section-icon" style="background: var(--secondary);">Q</div>
                    Quarterly Results Analysis
                </div>
                <div class="section-toggle">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 4L6 8L10 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <div style="background: linear-gradient(to right, #f0fff4, transparent); padding: 1.25rem; border-radius: 8px; border-left: 4px solid var(--secondary); margin-bottom: 1rem;">
                    <p style="color: var(--text-primary); line-height: 1.8;">{quarterly_analysis if quarterly_analysis else "Quarterly data analysis not available for this stock."}</p>
                </div>
                <div style="background: var(--bg-light); padding: 1rem; border-radius: 8px;">
                    <p style="font-size: 0.9rem; color: var(--text-secondary);"><strong>Price Action:</strong> {price_action_note if price_action_note else "N/A"}</p>
                </div>
            </div>
        </section>

        <!-- News & Catalysts -->
        <section class="section" id="news-catalysts">
            <div class="section-header" onclick="toggleSection(this)">
                <div class="section-title">
                    <div class="section-icon" style="background: var(--warning);">!</div>
                    News Impact & Catalysts
                </div>
                <div class="section-toggle">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 4L6 8L10 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <div style="margin-bottom: 1.5rem;">
                    <h4 style="color: var(--primary); margin-bottom: 0.75rem;">How Recent News Affects Our View</h4>
                    <p style="color: var(--text-secondary); line-height: 1.8;">{news_impact if news_impact else "No significant recent news to analyze."}</p>
                </div>

                <div style="background: linear-gradient(to right, var(--accent-light), transparent); padding: 1.25rem; border-radius: 8px; border-left: 4px solid var(--accent);">
                    <h4 style="color: var(--accent); margin-bottom: 0.75rem;">Upcoming Catalysts</h4>
                    <ul class="catalyst-list" style="list-style: none; padding: 0;">
                        {catalysts_html if catalysts_html else "<li style='color: var(--text-secondary); padding-left: 0;'>No specific near-term catalysts identified.</li>"}
                    </ul>
                </div>
            </div>
        </section>

        <!-- Company Overview -->
        <section class="section" id="company">
            <div class="section-header" onclick="toggleSection(this)">
                <div class="section-title">
                    <div class="section-icon">2</div>
                    Company Overview
                </div>
                <div class="section-toggle">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 4L6 8L10 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <p class="business-desc">{basic.get("description", analysis.get("business_analysis", ""))}</p>

                <h4 style="color: var(--primary); margin: 1.5rem 0 1rem;">Competitive Advantages</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                    {moat_cards}
                </div>
            </div>
        </section>

        <!-- Financial Analysis -->
        <section class="section" id="financials">
            <div class="section-header" onclick="toggleSection(this)">
                <div class="section-title">
                    <div class="section-icon">3</div>
                    Financial Analysis
                </div>
                <div class="section-toggle">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 4L6 8L10 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <p class="business-desc">{analysis.get("financial_analysis", "")}</p>

                <div class="valuation-grid">
                    <div class="valuation-card">
                        <div class="valuation-metric">Revenue</div>
                        <div class="valuation-value">{format_market_cap(financials.get("revenue", 0))}</div>
                    </div>
                    <div class="valuation-card">
                        <div class="valuation-metric">EBITDA</div>
                        <div class="valuation-value">{format_market_cap(financials.get("ebitda", 0))}</div>
                    </div>
                    <div class="valuation-card">
                        <div class="valuation-metric">Profit Margin</div>
                        <div class="valuation-value">{(financials.get("profit_margin", 0) or 0) * 100:.1f}%</div>
                    </div>
                    <div class="valuation-card">
                        <div class="valuation-metric">Debt/Equity</div>
                        <div class="valuation-value">{(balance.get("debt_to_equity", 0) or 0) / 100:.2f}</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Valuation -->
        <section class="section" id="valuation">
            <div class="section-header" onclick="toggleSection(this)">
                <div class="section-title">
                    <div class="section-icon">4</div>
                    Valuation
                </div>
                <div class="section-toggle">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 4L6 8L10 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <div class="valuation-grid">
                    <div class="valuation-card">
                        <div class="valuation-metric">P/E Ratio</div>
                        <div class="valuation-value">{pe_ratio:.1f}x</div>
                    </div>
                    <div class="valuation-card">
                        <div class="valuation-metric">P/B Ratio</div>
                        <div class="valuation-value">{pb_ratio:.1f}x</div>
                    </div>
                    <div class="valuation-card">
                        <div class="valuation-metric">EV/EBITDA</div>
                        <div class="valuation-value">{valuation.get("ev_to_ebitda", 0) or 0:.1f}x</div>
                    </div>
                    <div class="valuation-card">
                        <div class="valuation-metric">PEG Ratio</div>
                        <div class="valuation-value">{valuation.get("peg_ratio", 0) or 0:.2f}</div>
                    </div>
                </div>

                <div style="background: var(--bg-light); padding: 1.5rem; border-radius: 8px; margin-top: 1.5rem;">
                    <h4 style="color: var(--primary); margin-bottom: 0.75rem;">Valuation Summary</h4>
                    <p style="color: var(--text-secondary); line-height: 1.8;">
                        {analysis.get("valuation_analysis", "")}
                    </p>
                </div>
            </div>
        </section>

        <!-- Disclaimer -->
        <section class="section" id="disclaimer">
            <div class="section-header" onclick="toggleSection(this)">
                <div class="section-title">
                    <div class="section-icon">!</div>
                    Disclaimer
                </div>
                <div class="section-toggle">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 4L6 8L10 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <div class="disclaimer">
                    <h4>Important Disclosures</h4>
                    <p>
                        This report is for informational and educational purposes only and should not be construed as investment advice,
                        a recommendation, or an offer to buy or sell any securities. The information contained herein is based on sources
                        believed to be reliable, but its accuracy or completeness is not guaranteed.
                    </p>
                    <p style="margin-top: 1rem;">
                        Past performance is not indicative of future results. Investments in securities are subject to market risks.
                        Please read all related documents carefully before investing. The author(s) of this report may or may not hold
                        positions in the securities mentioned. Investors should conduct their own due diligence and/or consult a
                        qualified financial advisor before making investment decisions.
                    </p>
                </div>
            </div>
        </section>
    </main>

    <footer style="background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%); color: white; padding: 2rem; text-align: center; margin-top: 2rem;">
        <p style="font-family: 'DM Serif Display', Georgia, serif; font-size: 1.1rem; margin-bottom: 0.5rem;">
            Perma<span style="color: #e8913a;">bullish</span>
        </p>
        <p style="opacity: 0.8; font-size: 0.85rem;">
            AI-Powered Equity Research | {report_date} | For Educational Purposes Only
        </p>
    </footer>

    <script>
        function toggleSection(header) {{
            const section = header.parentElement;
            section.classList.toggle('collapsed');
        }}

        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function(e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            }});
        }});
    </script>
</body>
</html>'''

    return html
