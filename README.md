# Digital Subscriptions Bot: Vercel + Convex

Telegram store bot. Customers top up USDT with @CryptoBot and buy products, and the bot
buys from the Nexa API and delivers the codes instantly. It runs on **Vercel** (webhooks)
with **Convex** as the database.

```
api/index.py      Vercel endpoints: /api/telegram, /api/cryptopay, /api/setup
bot/              the bot (aiogram 3): handlers, pricing, Nexa + CryptoBot clients
bot/db.py         calls the Convex functions over HTTPS
convex/schema.ts  database tables
convex/bot.ts     database functions (atomic, protected by BOT_SECRET)
```

## Setup (one time, about 15 minutes)

### 1. Get your keys
- **Bot token:** @BotFather → /newbot
- **Your Telegram ID:** @userinfobot
- **Nexa API key:** Nexa bot → 🔌 API → Generate API Key. Also top up your Nexa wallet, because every customer order is paid from it.
- **CryptoBot token:** @CryptoBot → Crypto Pay → Create App → API Token

### 2. Convex
1. Open dashboard.convex.dev and create a project (or use your existing one).
2. Go to **Settings → Environment Variables** and add `BOT_SECRET` = a long random password (e.g. 40 random letters and numbers).
3. Go to **Settings → URL & Deploy Key** and copy:
   - the **Deployment URL** (`https://xxxx.convex.cloud`)
   - a **Production Deploy Key** (`prod:...`)

### 3. Vercel
1. Upload this folder to a GitHub repo, then on Vercel: **Add New → Project → import the repo**.
2. Before deploying, open **Environment Variables** and add everything from `.env.example`:
   - `CONVEX_SECRET` = the **same** value as `BOT_SECRET` in Convex
   - `CONVEX_URL` and `CONVEX_DEPLOY_KEY` from step 2
   - `SETUP_KEY` = any secret word
3. Click **Deploy**. The build uploads the database functions to Convex automatically (`npx convex deploy`).

### 4. Connect Telegram & CryptoBot
1. Open `https://YOUR-PROJECT.vercel.app/api/setup?key=YOUR_SETUP_KEY` in your browser.
   You should see `"ok": true` and your bot's name.
2. Copy the `/api/cryptopay` URL that page shows. Then in @CryptoBot go to **Crypto Pay → My Apps → your app → Webhooks → Enable** and paste it.
3. Open your bot in Telegram and send `/start` 🎉. Send `/admin` to see the admin commands.

Open the setup link again whenever you change the domain or the bot token.

## Admin commands
| Command | What it does |
|---|---|
| `/stats` | Users, revenue, profit, delayed orders, Nexa balance |
| `/markup 30 0.10` | +30% and +0.10$ on every product |
| `/aproducts` | Cost → sell price, stock, short IDs |
| `/setprice c1f7b036 3.99` / `/delprice c1f7b036` | Set or remove a custom price for one product |
| `/addbal <user_id> 5` (or `-5`) | Adjust a customer's balance |
| `/user <id>` · `/ban` · `/unban` | Manage users |
| `/find <order>` · `/retry <order>` · `/refund <order>` | Manage orders |
| `/wreply <id> text` · `/wclose <id>` | Handle warranty requests |
| `/broadcast text` (or reply to a message) | Send a message to all users (best for up to about 1000 users per run) |

## How money stays safe
- Charging, refunding and top-up credits are single atomic Convex mutations.
- A CryptoBot payment is credited exactly once, even if the webhook arrives twice. Its signature is checked.
- Each "Confirm" button can only buy once (no double-tap purchases), and repeated Telegram updates are ignored.
- Nexa purchases use an Idempotency-Key. If Nexa clearly refuses an order, the customer is refunded automatically. If the outcome is unknown (network error), the order is marked *delayed* and you get `/retry` (which never charges twice) and `/refund` commands.

## Troubleshooting
- **Bot doesn't answer:** open `/api/setup?key=...` again and check **Vercel → Project → Logs**.
- **"unauthorized" in the logs:** `CONVEX_SECRET` (Vercel) and `BOT_SECRET` (Convex) are different.
- **Build fails at `convex deploy`:** `CONVEX_DEPLOY_KEY` is missing or wrong.
- **Products don't load:** the Nexa key is wrong, or Nexa's server is down (`/nexabal` shows the error).
