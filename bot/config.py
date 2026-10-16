import hashlib
import os

try:  # .env is only used for local tests; on Vercel use Project Settings -> Environment Variables
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


# --- Telegram ---
BOT_TOKEN = _required("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").lstrip("@")
TELEGRAM_API_BASE = os.getenv("TELEGRAM_API_BASE", "")  # leave empty (only for tests)

# --- Nexa supplier API ---
NEXA_BASE_URL = os.getenv("NEXA_BASE_URL", "http://186.241.26.133:3000/api/v1")
NEXA_API_KEY = _required("NEXA_API_KEY")

# --- Bastaha supplier API ---
BASTAHA_BASE_URL = os.getenv("BASTAHA_BASE_URL", "https://admin.bastaha.com/api/reseller")
BASTAHA_API_KEY = os.getenv("BASTAHA_API_KEY", "")


# --- Database (Convex) ---
CONVEX_URL = _required("CONVEX_URL")        # e.g. https://happy-animal-123.convex.cloud
CONVEX_SECRET = _required("CONVEX_SECRET")  # must equal BOT_SECRET in the Convex dashboard

# --- Web / security ---
SETUP_KEY = _required("SETUP_KEY")            # any secret word, used once to open /api/setup
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")  # optional, e.g. https://mybot.vercel.app
WEBHOOK_SECRET = hashlib.sha256(("tg-webhook:" + BOT_TOKEN).encode()).hexdigest()[:48]

# --- Shop settings ---
DEFAULT_MARKUP_PERCENT = float(os.getenv("DEFAULT_MARKUP_PERCENT", "30"))
DEFAULT_MARKUP_FIXED = float(os.getenv("DEFAULT_MARKUP_FIXED", "0"))
MIN_TOPUP = float(os.getenv("MIN_TOPUP", "1"))
MAX_TOPUP = float(os.getenv("MAX_TOPUP", "1000"))

# --- Binance Pay (merchant) ---
BINANCE_PAY_PARTNER_ID = os.getenv("BINANCE_PAY_PARTNER_ID", "")
BINANCE_PAY_PARTNER_KEY = os.getenv("BINANCE_PAY_PARTNER_KEY", "")

# --- BEP-20 / BSC ---
BSC_DEPOSIT_ADDRESS = os.getenv("BSC_DEPOSIT_ADDRESS", "")
# USDT-BEP20 contract on BSC mainnet
USDT_BEP20_CONTRACT = os.getenv("USDT_BEP20_CONTRACT", "0x55d398326f99059fF775485246999027B3197955")
# Free public BSC RPC
BSC_RPC_URL = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
