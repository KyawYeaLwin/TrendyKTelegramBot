# TrendyKBot — Telegram Menu Bot

A Python Telegram bot that lets users browse your product catalogue from a Google Sheet.

## Menu Flow

```
/start
 ├─ 📦 Check Stock
 │    └─ [Brand / Category]
 │          └─ [Product]  →  Detail card (price, weight, stock, expiry, branch)
 └─ ℹ️  Help / Info
```

## Files

| File | Purpose |
|---|---|
| `bot.py` | Main bot entry-point & handlers |
| `sheets_service.py` | Google Sheets data layer |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure `.env`
Copy `.env.example` → `.env` and fill in:

```env
BOT_TOKEN=xxxxx
GOOGLE_SHEET_ID=xxxxx
GOOGLE_SERVICE_ACCOUNT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
```

### 3. Google Sheet requirements
- Share your Google Sheet with your **service account email** (Editor access).
- The first worksheet must have these column headers:

| Column | Description |
|---|---|
| No. | Row number |
| Product Code | Unique product ID |
| Product Name | Product display name |
| Brand Name | Category / brand |
| Weight | Weight (e.g. 500g) |
| Available Count | Stock quantity |
| Branch Name | Store branch |
| Expiry Date | Expiry date |
| Selling Price | Price |

### 4. Run the bot
```bash
python bot.py
```

## Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable **Google Sheets API** and **Google Drive API**
4. Create a **Service Account** and download the JSON key
5. Copy `client_email` and `private_key` into your `.env`
6. Share the Google Sheet with the service account email
