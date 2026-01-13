# Equity Research Generator

AI-powered equity research report generator for Indian stocks. Generate professional research reports with investment recommendations, financial analysis, and valuation insights.

## Features

- **User Authentication**: Secure login/registration system
- **Stock Search**: Search for Indian stocks (NSE/BSE)
- **AI-Powered Analysis**: Claude AI generates investment thesis, bull/bear cases, and recommendations
- **Interactive Reports**: Beautiful HTML reports with charts and collapsible sections
- **Usage Tracking**: 20 reports per month per user
- **Report History**: Save and access all generated reports

## Tech Stack

- **Backend**: Python FastAPI
- **Database**: SQLite
- **Data Source**: Yahoo Finance (via yfinance)
- **AI**: Anthropic Claude API
- **Frontend**: HTML/CSS/JavaScript with Tailwind CSS

## Setup

### Prerequisites

- Python 3.9+
- Anthropic API key (for AI analysis)

### Installation

1. **Clone and navigate to the project**
   ```bash
   cd equity-research-generator
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Windows
   set ANTHROPIC_API_KEY=your_api_key_here

   # Mac/Linux
   export ANTHROPIC_API_KEY=your_api_key_here
   ```

5. **Run the server**
   ```bash
   cd backend
   python main.py
   ```

6. **Open the frontend**
   - Open `frontend/index.html` in your browser
   - Or serve it with a local server:
     ```bash
     cd frontend
     python -m http.server 3000
     ```
   - Then visit `http://localhost:3000`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get token
- `GET /api/auth/me` - Get current user info

### Stocks
- `GET /api/stocks/search?q=query` - Search stocks
- `GET /api/stocks/{symbol}` - Get stock info

### Reports
- `POST /api/reports/generate` - Generate new report
- `GET /api/reports` - Get user's reports
- `GET /api/reports/{id}` - Get report details
- `GET /api/reports/{id}/html` - Get report HTML
- `DELETE /api/reports/{id}` - Delete report

### Usage
- `GET /api/usage` - Get usage statistics

## Project Structure

```
equity-research-generator/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── auth.py              # Authentication logic
│   ├── database.py          # Database models & operations
│   ├── yahoo_finance.py     # Stock data fetching
│   ├── report_generator.py  # AI analysis & HTML generation
│   ├── config.py            # Configuration
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html           # Login/Register page
│   ├── dashboard.html       # User dashboard
│   ├── generate.html        # Report generation
│   └── report.html          # Report viewer
├── data/
│   └── research.db          # SQLite database (auto-created)
└── README.md
```

## Configuration

Edit `backend/config.py` to customize:

- `SECRET_KEY` - JWT secret (change in production!)
- `MONTHLY_REPORT_LIMIT` - Reports per month (default: 20)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiry

## Usage Notes

1. **First Time**: Register a new account on the login page
2. **Generate Report**: Search for a company, select it, and click Generate
3. **View Reports**: Access all reports from the dashboard
4. **Download**: Download reports as HTML files for offline viewing

## Limitations

- Yahoo Finance data may have delays or missing fields for some stocks
- AI analysis requires valid Anthropic API key
- 20 reports per month limit (configurable)

## Disclaimer

This tool is for educational purposes only. The generated reports do not constitute financial advice. Always conduct your own research and consult qualified financial advisors before making investment decisions.
