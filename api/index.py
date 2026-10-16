"""Vercel entry point — all routes live here."""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bot"))

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route

import core
from config import PUBLIC_URL, SETUP_KEY, WEBHOOK_SECRET

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")

# ── helpers ──────────────────────────────────────────────────────────────────

def _auth(request: Request) -> bool:
    return request.query_params.get("key") == SETUP_KEY

def _bad():
    return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=403)

# ── telegram / cryptopay webhooks ────────────────────────────────────────────

async def telegram(request: Request):
    if request.headers.get("x-telegram-bot-api-secret-token") != WEBHOOK_SECRET:
        return JSONResponse({"ok": False}, status_code=403)
    try:
        await core.handle_telegram(await request.json())
    except Exception:
        log.exception("update failed")
    return JSONResponse({"ok": True})


# ── setup ─────────────────────────────────────────────────────────────────────

async def setup(request: Request):
    if not _auth(request):
        return _bad()
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    try:
        return JSONResponse(await core.setup(PUBLIC_URL or f"https://{host}"))
    except Exception as e:
        log.exception("setup failed")
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)

# ── stats ─────────────────────────────────────────────────────────────────────

async def stats_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        await db.connect()
        data = await db.stats()
        await db.close()
        rev, cost = data.get("revenue", 0), data.get("cost", 0)
        rev24, cost24 = data.get("revenue_24h", 0), data.get("cost_24h", 0)
        return JSONResponse({"ok": True,
            "users": data.get("users", 0), "orders": data.get("orders", 0),
            "orders_24h": data.get("orders_24h", 0),
            "revenue": round(rev / 100, 2), "revenue_24h": round(rev24 / 100, 2),
            "profit": round((rev - cost) / 100, 2), "profit_24h": round((rev24 - cost24) / 100, 2),
            "topups": round(data.get("topups", 0) / 100, 2),
            "balances": round(data.get("balances", 0) / 100, 2),
            "pending_orders": data.get("pending_orders", 0),
            "open_warranties": data.get("open_warranties", 0),
        })
    except Exception as e:
        log.exception("stats failed")
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)

# ── products + pricing ────────────────────────────────────────────────────────

async def products_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        from nexa_api import NexaClient
        from pricing import get_pricing, price_for
        from money import fmt
        await db.connect()
        nexa = NexaClient(NEXA_BASE_URL, NEXA_API_KEY)
        products = await nexa.products(force=True)
        pricing = await get_pricing()
        await nexa.close()
        await db.close()
        result = []
        for p in products:
            sell = price_for(p, pricing)
            cost_c = int(round(p["price"] * 100))
            result.append({
                "id": p["id"], "name": p["name"],
                "cost": p["price"], "sell": round(sell / 100, 2),
                "profit": round((sell - cost_c) / 100, 2),
                "stock": p.get("stock", 0), "in_stock": p.get("in_stock", False),
                "custom": p["id"] in pricing.overrides,
            })
        return JSONResponse({"ok": True, "products": result,
            "markup_percent": pricing.percent, "markup_fixed": round(pricing.fixed / 100, 2)})
    except Exception as e:
        log.exception("products failed")
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)


async def setprice_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        from money import to_cents
        body = await request.json()
        product_id, price_str = body.get("product_id", ""), str(body.get("price", ""))
        if not product_id or not price_str:
            return JSONResponse({"ok": False, "error": "missing fields"}, status_code=400)
        cents = to_cents(price_str)
        await db.connect()
        await db.set_override(product_id, cents)
        await db.close()
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)


async def delprice_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        body = await request.json()
        product_id = body.get("product_id", "")
        await db.connect()
        ok = await db.del_override(product_id)
        await db.close()
        return JSONResponse({"ok": ok})
    except Exception as e:
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)


async def setmarkup_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        body = await request.json()
        pct = float(body.get("percent", 30))
        fixed = float(body.get("fixed", 0))
        await db.connect()
        await db.set_setting("markup_percent", str(pct))
        await db.set_setting("markup_fixed", str(fixed))
        await db.close()
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)

# ── users ─────────────────────────────────────────────────────────────────────

async def user_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        uid = int(request.query_params.get("id", 0))
        if not uid:
            return JSONResponse({"ok": False, "error": "missing id"}, status_code=400)
        await db.connect()
        u = await db.get_user(uid)
        orders = await db.user_orders(uid, 10) if u else []
        await db.close()
        if not u:
            return JSONResponse({"ok": False, "error": "user not found"}, status_code=404)
        return JSONResponse({"ok": True, "user": {
            "id": u["id"], "username": u.get("username"),
            "lang": u.get("lang", "en"), "banned": u.get("banned", False),
            "balance": round(u.get("balance", 0) / 100, 2),
            "created_at": u.get("created_at"),
        }, "orders": [{"id": o["id"], "product_name": o["product_name"],
            "quantity": o["quantity"], "total": round(o["total"] / 100, 2),
            "status": o["status"], "created_at": o.get("created_at")} for o in orders]})
    except Exception as e:
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)


async def addbal_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        from money import to_cents
        body = await request.json()
        uid = int(body.get("user_id", 0))
        amount_str = str(body.get("amount", "0"))
        cents = to_cents(amount_str)
        await db.connect()
        if cents >= 0:
            ok = await db.credit(uid, cents, "admin_dash")
        else:
            ok = await db.debit(uid, -cents, "admin_dash")
        u = await db.get_user(uid) if ok else None
        await db.close()
        if not ok:
            return JSONResponse({"ok": False, "error": "failed (low balance or user not found)"})
        return JSONResponse({"ok": True, "new_balance": round(u["balance"] / 100, 2)})
    except Exception as e:
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)


async def ban_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        body = await request.json()
        uid = int(body.get("user_id", 0))
        banned = bool(body.get("banned", True))
        await db.connect()
        ok = await db.set_banned(uid, banned)
        await db.close()
        return JSONResponse({"ok": ok})
    except Exception as e:
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)

# ── orders ────────────────────────────────────────────────────────────────────

async def order_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        oid = request.query_params.get("id", "").strip()
        if not oid:
            return JSONResponse({"ok": False, "error": "missing id"}, status_code=400)
        await db.connect()
        o = await db.get_order(oid)
        await db.close()
        if not o:
            return JSONResponse({"ok": False, "error": "order not found"}, status_code=404)
        return JSONResponse({"ok": True, "order": {
            "id": o["id"], "user_id": o["user_id"],
            "product_name": o["product_name"], "quantity": o["quantity"],
            "total": round(o["total"] / 100, 2), "cost": round(o["cost"] / 100, 2),
            "status": o["status"], "nexa_order_id": o.get("nexa_order_id"),
            "created_at": o.get("created_at"),
        }})
    except Exception as e:
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)


async def refund_api(request: Request):
    if not _auth(request):
        return _bad()
    try:
        import db
        body = await request.json()
        oid = body.get("order_id", "").strip()
        await db.connect()
        ok = await db.refund_order(oid)
        await db.close()
        return JSONResponse({"ok": ok, "error": "already refunded" if not ok else None})
    except Exception as e:
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)

# ── dashboard HTML ────────────────────────────────────────────────────────────

DASH = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Bot Admin Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#07070f;--s:#0f0f1a;--c:#161625;--b:#252540;--a:#7c6fff;--a2:#ff6584;--a3:#43e97b;--a4:#f7c948;--t:#eeeeff;--m:#8888aa}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--t);min-height:100vh}
/* LOGIN */
#login{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:1rem;background:radial-gradient(ellipse at 50% -10%,rgba(124,111,255,.18),transparent 65%)}
.lc{background:var(--c);border:1px solid var(--b);border-radius:28px;padding:3rem 2.5rem;width:100%;max-width:380px;text-align:center;box-shadow:0 40px 80px rgba(0,0,0,.5)}
.ll{font-size:4rem;display:inline-block;animation:bob 3s ease-in-out infinite;margin-bottom:1.2rem}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
.lt{font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,#7c6fff,#ff6584);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.3rem}
.ls{color:var(--m);font-size:.88rem;margin-bottom:2rem}
.li{width:100%;padding:1rem 1.2rem;background:var(--s);border:1.5px solid var(--b);border-radius:14px;color:var(--t);font-size:1rem;font-family:'Inter',sans-serif;outline:none;transition:.25s;margin-bottom:.9rem}
.li:focus{border-color:var(--a);box-shadow:0 0 0 4px rgba(124,111,255,.15)}
.lb{width:100%;padding:1rem;background:linear-gradient(135deg,#7c6fff,#9b59f5);border:none;border-radius:14px;color:#fff;font-size:1rem;font-weight:700;cursor:pointer;transition:.25s;font-family:'Inter',sans-serif}
.lb:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(124,111,255,.45)}
.le{color:#ff6584;font-size:.83rem;display:none;margin-top:.6rem}
/* APP */
#app{display:none}
.topbar{background:rgba(15,15,26,.85);border-bottom:1px solid var(--b);padding:.9rem 2rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:200;backdrop-filter:blur(16px)}
.tl{display:flex;align-items:center;gap:.8rem}
.ttitle{font-size:1.05rem;font-weight:800;background:linear-gradient(135deg,#7c6fff,#ff6584);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.tr{display:flex;align-items:center;gap:1rem}
.live{display:flex;align-items:center;gap:.5rem}
.dot{width:7px;height:7px;background:#43e97b;border-radius:50%;animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(67,233,123,.5)}50%{box-shadow:0 0 0 6px rgba(67,233,123,0)}}
.lt2{font-size:.78rem;color:var(--m)}
.btn{padding:.5rem 1.1rem;background:var(--c);border:1px solid var(--b);border-radius:9px;color:var(--t);font-size:.8rem;font-weight:500;cursor:pointer;font-family:'Inter',sans-serif;transition:.2s}
.btn:hover{border-color:var(--a);color:var(--a)}
.btn-p{background:linear-gradient(135deg,#7c6fff,#9b59f5);border:none;color:#fff;font-weight:600}
.btn-p:hover{transform:translateY(-1px);box-shadow:0 6px 16px rgba(124,111,255,.4);color:#fff}
.btn-d{background:rgba(255,101,132,.1);border-color:rgba(255,101,132,.3);color:#ff6584}
.btn-d:hover{background:rgba(255,101,132,.2);color:#ff6584;border-color:#ff6584}
.btn-g{background:rgba(67,233,123,.1);border-color:rgba(67,233,123,.3);color:#43e97b}
.btn-g:hover{background:rgba(67,233,123,.2);color:#43e97b}
/* TABS */
.tabs{display:flex;gap:.3rem;padding:1.2rem 2rem 0;border-bottom:1px solid var(--b);background:var(--s)}
.tab{padding:.7rem 1.2rem;border-radius:10px 10px 0 0;font-size:.85rem;font-weight:600;cursor:pointer;transition:.2s;color:var(--m);border:1px solid transparent;border-bottom:none;margin-bottom:-1px}
.tab:hover{color:var(--t)}
.tab.active{background:var(--bg);color:var(--t);border-color:var(--b);border-bottom-color:var(--bg)}
/* CONTENT */
.content{display:none;padding:1.5rem 2rem;max-width:1400px;margin:0 auto}
.content.active{display:block}
/* STATS */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:1rem;margin-bottom:1.5rem}
.sc{background:var(--c);border:1px solid var(--b);border-radius:18px;padding:1.3rem;position:relative;overflow:hidden;transition:.3s}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--gc)}
.sc:hover{transform:translateY(-3px);box-shadow:0 14px 36px rgba(0,0,0,.4)}
.si{font-size:1.6rem;margin-bottom:.7rem}
.sl{font-size:.7rem;color:var(--m);font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.25rem}
.sv{font-size:1.8rem;font-weight:900;line-height:1.1}
.ss{font-size:.75rem;color:var(--m);margin-top:.3rem}
/* MARKUP BOX */
.markup-box{background:var(--c);border:1px solid var(--b);border-radius:16px;padding:1.2rem 1.5rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:1.5rem}
.markup-label{font-size:.85rem;font-weight:600;color:var(--m)}
.num-input{width:90px;padding:.55rem .8rem;background:var(--s);border:1.5px solid var(--b);border-radius:9px;color:var(--t);font-size:.9rem;font-family:'Inter',sans-serif;outline:none;transition:.2s}
.num-input:focus{border-color:var(--a)}
/* ALERT */
.alert{display:none;align-items:center;gap:.7rem;padding:.9rem 1.3rem;border-radius:12px;margin-bottom:1.2rem;font-size:.86rem;font-weight:600;background:rgba(247,201,72,.1);border:1px solid rgba(247,201,72,.25);color:#f7c948}
/* TOAST */
#toast{position:fixed;bottom:2rem;right:2rem;padding:.8rem 1.4rem;border-radius:12px;font-size:.88rem;font-weight:600;z-index:999;display:none;background:var(--c);border:1px solid var(--b);box-shadow:0 8px 24px rgba(0,0,0,.4);animation:slide .25s ease}
@keyframes slide{from{transform:translateY(10px);opacity:0}to{transform:translateY(0);opacity:1}}
/* TABLE */
.tw{background:var(--c);border:1px solid var(--b);border-radius:18px;overflow:hidden}
.th{padding:1.1rem 1.4rem;border-bottom:1px solid var(--b);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.8rem}
.th-t{font-weight:700;font-size:.9rem}
.si2{padding:.55rem 1rem;background:var(--s);border:1.5px solid var(--b);border-radius:9px;color:var(--t);font-size:.82rem;font-family:'Inter',sans-serif;outline:none;width:200px;transition:.2s}
.si2:focus{border-color:var(--a)}
.tscroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;min-width:560px}
th{padding:.7rem 1rem;text-align:left;font-size:.68rem;font-weight:700;color:var(--m);text-transform:uppercase;letter-spacing:.1em;border-bottom:1px solid var(--b)}
td{padding:.8rem 1rem;font-size:.84rem;border-bottom:1px solid rgba(255,255,255,.03)}
tr:last-child td{border:none}
tr:hover td{background:rgba(124,111,255,.04)}
.ins{display:inline-flex;align-items:center;gap:.3rem;padding:.2rem .55rem;border-radius:6px;font-size:.72rem;font-weight:700}
.g{background:rgba(67,233,123,.12);color:#43e97b}.r{background:rgba(255,101,132,.12);color:#ff6584}
.y{background:rgba(247,201,72,.12);color:#f7c948}.v{background:rgba(124,111,255,.12);color:#9b8fff}
.sp{font-weight:800;color:#9b8fff}.pc{color:#43e97b;font-weight:700}
/* SEARCH PANEL */
.search-panel{background:var(--c);border:1px solid var(--b);border-radius:16px;padding:1.2rem 1.5rem;margin-bottom:1.2rem;display:flex;gap:.8rem;flex-wrap:wrap;align-items:flex-end}
.field{display:flex;flex-direction:column;gap:.4rem;flex:1;min-width:160px}
.field label{font-size:.72rem;font-weight:700;color:var(--m);text-transform:uppercase;letter-spacing:.08em}
.field input{padding:.6rem 1rem;background:var(--s);border:1.5px solid var(--b);border-radius:9px;color:var(--t);font-size:.88rem;font-family:'Inter',sans-serif;outline:none;transition:.2s}
.field input:focus{border-color:var(--a)}
/* USER / ORDER CARD */
.info-card{background:var(--c);border:1px solid var(--b);border-radius:16px;padding:1.3rem 1.5rem;margin-bottom:1.2rem}
.info-row{display:flex;justify-content:space-between;align-items:center;padding:.45rem 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:.88rem}
.info-row:last-child{border:none}
.info-key{color:var(--m);font-weight:500;font-size:.8rem}
.info-val{font-weight:600}
.ld{text-align:center;padding:3rem;color:var(--m)}
.spin{width:34px;height:34px;border:3px solid var(--b);border-top-color:var(--a);border-radius:50%;animation:sp .75s linear infinite;margin:0 auto 1rem}
@keyframes sp{to{transform:rotate(360deg)}}
.section-gap{height:1.2rem}
@media(max-width:700px){.content{padding:1rem}.grid{grid-template-columns:1fr 1fr}.si2{width:130px}.tabs{padding:.8rem 1rem 0;overflow-x:auto}.tab{white-space:nowrap}}
</style>
</head>
<body>

<div id="login">
  <div class="lc">
    <span class="ll">⚡</span>
    <div class="lt">Admin Dashboard</div>
    <div class="ls">Manage your bot, prices, orders & users</div>
    <input id="ki" class="li" type="password" placeholder="🔑  Setup key" onkeydown="if(event.key==='Enter')go()"/>
    <button class="lb" onclick="go()">Access Dashboard →</button>
    <div id="le" class="le">❌ Wrong key</div>
  </div>
</div>

<div id="app">
  <div class="topbar">
    <div class="tl">
      <div class="ttitle">⚡ @golde1nbot Admin</div>
    </div>
    <div class="tr">
      <div class="live"><div class="dot"></div><div class="lt2">Live</div></div>
      <button class="btn" onclick="reload()">↻ Refresh</button>
    </div>
  </div>

  <div class="tabs">
    <div class="tab active" onclick="switchTab('stats',this)">📊 Overview</div>
    <div class="tab" onclick="switchTab('products',this)">🛒 Products</div>
    <div class="tab" onclick="switchTab('orders',this)">📦 Orders</div>
    <div class="tab" onclick="switchTab('users',this)">👥 Users</div>
  </div>

  <!-- STATS TAB -->
  <div id="tab-stats" class="content active">
    <div id="al" class="alert">⚠️ <span id="alt"></span></div>
    <div class="grid" id="sg"><div class="ld"><div class="spin"></div>Loading…</div></div>
  </div>

  <!-- PRODUCTS TAB -->
  <div id="tab-products" class="content">
    <div class="markup-box">
      <div class="markup-label">🎚 Global Markup</div>
      <div class="field" style="flex:0">
        <label>Percent %</label>
        <input class="num-input" type="number" id="mpct" value="40" min="0" max="500"/>
      </div>
      <div class="field" style="flex:0">
        <label>Fixed $</label>
        <input class="num-input" type="number" id="mfix" value="0" min="0" step="0.01"/>
      </div>
      <button class="btn btn-p" onclick="saveMarkup()">💾 Save Markup</button>
    </div>
    <div class="tw">
      <div class="th">
        <div class="th-t">🛒 All Products</div>
        <input class="si2" type="text" id="psrch" placeholder="🔍 Search…" oninput="fprod()"/>
      </div>
      <div class="tscroll"><div id="ptbl"><div class="ld"><div class="spin"></div>Loading…</div></div></div>
    </div>
  </div>

  <!-- ORDERS TAB -->
  <div id="tab-orders" class="content">
    <div class="search-panel">
      <div class="field">
        <label>Order ID</label>
        <input type="text" id="oid" placeholder="NX-AB12CD34" onkeydown="if(event.key==='Enter')findOrder()"/>
      </div>
      <button class="btn btn-p" onclick="findOrder()">🔍 Find Order</button>
    </div>
    <div id="order-result"></div>
  </div>

  <!-- USERS TAB -->
  <div id="tab-users" class="content">
    <div class="search-panel">
      <div class="field">
        <label>Telegram User ID</label>
        <input type="number" id="uid" placeholder="2111540031" onkeydown="if(event.key==='Enter')findUser()"/>
      </div>
      <button class="btn btn-p" onclick="findUser()">🔍 Find User</button>
    </div>
    <div id="user-result"></div>
  </div>
</div>

<div id="toast"></div>

<script>
let K='',allP=[],curMarkup={percent:40,fixed:0};

function go(){const k=document.getElementById('ki').value.trim();if(!k)return;K=k;loadAll();}

async function loadAll(){
  try{
    const r=await fetch('/api/stats?key='+enc(K));
    const d=await r.json();
    if(!d.ok){document.getElementById('le').style.display='block';document.getElementById('ki').value='';return;}
    document.getElementById('login').style.display='none';
    document.getElementById('app').style.display='block';
    renderStats(d);checkAlerts(d);
  }catch(e){document.getElementById('le').style.display='block';}
  loadProducts();
}

function reload(){loadAll();}
function enc(s){return encodeURIComponent(s);}

function switchTab(id,el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.content').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('tab-'+id).classList.add('active');
}

function toast(msg,type='ok'){
  const t=document.getElementById('toast');
  t.textContent=msg;
  t.style.display='block';
  t.style.color=type==='ok'?'#43e97b':type==='err'?'#ff6584':'#f7c948';
  t.style.borderColor=type==='ok'?'rgba(67,233,123,.3)':type==='err'?'rgba(255,101,132,.3)':'rgba(247,201,72,.3)';
  setTimeout(()=>{t.style.display='none';},3000);
}

// ── STATS ─────────────────────────────────────────────
function renderStats(d){
  const cs=[
    {i:'👥',l:'Users',v:d.users,s:'Customers',gc:'linear-gradient(90deg,#7c6fff,#9b59f5)'},
    {i:'📦',l:'Orders',v:d.orders,s:d.orders_24h+' today',gc:'linear-gradient(90deg,#43e97b,#38f9d7)'},
    {i:'💰',l:'Revenue',v:'$'+d.revenue,s:'$'+d.revenue_24h+' today',gc:'linear-gradient(90deg,#f7c948,#ffd700)'},
    {i:'📈',l:'Net Profit',v:'$'+d.profit,s:'$'+d.profit_24h+' today',gc:'linear-gradient(90deg,#43e97b,#00c9a7)'},
    {i:'💳',l:'Top-ups',v:'$'+d.topups,s:'USDT received',gc:'linear-gradient(90deg,#fa709a,#fee140)'},
    {i:'🏦',l:'Balances',v:'$'+d.balances,s:'In wallets',gc:'linear-gradient(90deg,#a78bfa,#c084fc)'},
    {i:'⏳',l:'Pending',v:d.pending_orders,s:'Need delivery',gc:d.pending_orders?'linear-gradient(90deg,#f7c948,#ffd700)':'linear-gradient(90deg,#43e97b,#38f9d7)'},
    {i:'🛠',l:'Warranties',v:d.open_warranties,s:'Open tickets',gc:d.open_warranties?'linear-gradient(90deg,#ff6584,#ff9a9e)':'linear-gradient(90deg,#43e97b,#38f9d7)'},
  ];
  document.getElementById('sg').innerHTML=cs.map(c=>`<div class="sc" style="--gc:${c.gc}"><div class="si">${c.i}</div><div class="sl">${c.l}</div><div class="sv">${c.v}</div><div class="ss">${c.s}</div></div>`).join('');
}
function checkAlerts(d){
  const a=[];
  if(d.pending_orders>0)a.push(d.pending_orders+' pending order(s)');
  if(d.open_warranties>0)a.push(d.open_warranties+' warranty request(s)');
  const el=document.getElementById('al');
  if(a.length){el.style.display='flex';document.getElementById('alt').textContent=a.join(' · ');}
  else el.style.display='none';
}

// ── PRODUCTS ──────────────────────────────────────────
async function loadProducts(){
  try{
    const r=await fetch('/api/admin/products?key='+enc(K));
    const d=await r.json();
    if(!d.ok)return;
    allP=d.products||[];
    curMarkup={percent:d.markup_percent,fixed:d.markup_fixed};
    document.getElementById('mpct').value=curMarkup.percent;
    document.getElementById('mfix').value=curMarkup.fixed;
    renderProducts(allP);
  }catch(e){}
}
function renderProducts(list){
  if(!list.length){document.getElementById('ptbl').innerHTML='<div class="ld">No products.</div>';return;}
  const rows=list.map(p=>{
    const stock=p.in_stock?`<span class="ins g">✅ ${p.stock}</span>`:`<span class="ins r">❌ Out</span>`;
    const custom=p.custom?'⭐ ':'';
    return`<tr>
      <td><b>${p.name}</b></td>
      <td>$${p.cost}</td>
      <td><span class="sp">$${p.sell}</span></td>
      <td><span class="pc">+$${p.profit}</span></td>
      <td>${stock}</td>
      <td>
        <input type="number" value="${p.sell}" id="pr_${p.id}" style="width:80px;padding:.35rem .5rem;background:var(--s);border:1px solid var(--b);border-radius:7px;color:var(--t);font-size:.82rem;font-family:'Inter',sans-serif;outline:none" step="0.01" min="0"/>
        <button class="btn btn-p" style="padding:.35rem .7rem;font-size:.75rem;margin-left:4px" onclick="setP('${p.id}')">Set</button>
        ${p.custom?`<button class="btn btn-d" style="padding:.35rem .7rem;font-size:.75rem;margin-left:2px" onclick="delP('${p.id}')">Reset</button>`:''}
      </td>
    </tr>`;
  }).join('');
  document.getElementById('ptbl').innerHTML=`<table><thead><tr><th>Product</th><th>Cost</th><th>Sell</th><th>Profit</th><th>Stock</th><th>Custom Price</th></tr></thead><tbody>${rows}</tbody></table>`;
}
function fprod(){const q=document.getElementById('psrch').value.toLowerCase();renderProducts(allP.filter(p=>p.name.toLowerCase().includes(q)));}
async function setP(id){
  const val=document.getElementById('pr_'+id).value;
  const r=await fetch('/api/admin/setprice?key='+enc(K),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:id,price:val})});
  const d=await r.json();
  if(d.ok){toast('✅ Price updated!');loadProducts();}else toast('❌ '+d.error,'err');
}
async function delP(id){
  const r=await fetch('/api/admin/delprice?key='+enc(K),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:id})});
  const d=await r.json();
  if(d.ok){toast('✅ Custom price removed');loadProducts();}else toast('❌ Failed','err');
}
async function saveMarkup(){
  const pct=parseFloat(document.getElementById('mpct').value)||0;
  const fix=parseFloat(document.getElementById('mfix').value)||0;
  const r=await fetch('/api/admin/setmarkup?key='+enc(K),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({percent:pct,fixed:fix})});
  const d=await r.json();
  if(d.ok){toast('✅ Markup saved! Refresh to see updated prices.');curMarkup={percent:pct,fixed:fix};}else toast('❌ '+d.error,'err');
}

// ── ORDERS ────────────────────────────────────────────
async function findOrder(){
  const oid=document.getElementById('oid').value.trim();
  if(!oid)return;
  document.getElementById('order-result').innerHTML='<div class="ld"><div class="spin"></div>Searching…</div>';
  try{
    const r=await fetch('/api/admin/order?key='+enc(K)+'&id='+enc(oid));
    const d=await r.json();
    if(!d.ok){document.getElementById('order-result').innerHTML=`<div class="ld">❌ ${d.error}</div>`;return;}
    const o=d.order;
    const statusCls={'completed':'g','refunded':'v','processing':'y','pending':'y','failed':'r'}[o.status]||'y';
    document.getElementById('order-result').innerHTML=`
      <div class="info-card">
        <div class="info-row"><span class="info-key">Order ID</span><span class="info-val"><code>${o.id}</code></span></div>
        <div class="info-row"><span class="info-key">User ID</span><span class="info-val">${o.user_id}</span></div>
        <div class="info-row"><span class="info-key">Product</span><span class="info-val">${o.product_name} × ${o.quantity}</span></div>
        <div class="info-row"><span class="info-key">Total</span><span class="info-val">$${o.total}</span></div>
        <div class="info-row"><span class="info-key">Cost</span><span class="info-val">$${o.cost}</span></div>
        <div class="info-row"><span class="info-key">Profit</span><span class="info-val pc">+$${(o.total-o.cost).toFixed(2)}</span></div>
        <div class="info-row"><span class="info-key">Status</span><span class="info-val"><span class="ins ${statusCls}">${o.status}</span></span></div>
        <div class="info-row"><span class="info-key">Nexa ID</span><span class="info-val">${o.nexa_order_id||'—'}</span></div>
        <div class="section-gap"></div>
        ${o.status!=='refunded'?`<button class="btn btn-d" onclick="refundOrder('${o.id}')">↩️ Refund to wallet</button>`:'<span class="ins v">Already refunded</span>'}
      </div>`;
  }catch(e){document.getElementById('order-result').innerHTML='<div class="ld">❌ Error</div>';}
}
async function refundOrder(oid){
  if(!confirm('Refund order '+oid+'?'))return;
  const r=await fetch('/api/admin/refund?key='+enc(K),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({order_id:oid})});
  const d=await r.json();
  if(d.ok){toast('✅ Refunded!');findOrder();}else toast('❌ '+(d.error||'Failed'),'err');
}

// ── USERS ─────────────────────────────────────────────
async function findUser(){
  const uid=document.getElementById('uid').value.trim();
  if(!uid)return;
  document.getElementById('user-result').innerHTML='<div class="ld"><div class="spin"></div>Searching…</div>';
  try{
    const r=await fetch('/api/admin/user?key='+enc(K)+'&id='+enc(uid));
    const d=await r.json();
    if(!d.ok){document.getElementById('user-result').innerHTML=`<div class="ld">❌ ${d.error}</div>`;return;}
    const u=d.user;
    const orders=d.orders||[];
    const orows=orders.map(o=>{
      const sc={'completed':'g','refunded':'v','failed':'r','processing':'y','pending':'y'}[o.status]||'y';
      return`<tr><td><code>${o.id}</code></td><td>${o.product_name} × ${o.quantity}</td><td>$${o.total}</td><td><span class="ins ${sc}">${o.status}</span></td></tr>`;
    }).join('');
    document.getElementById('user-result').innerHTML=`
      <div class="info-card">
        <div class="info-row"><span class="info-key">User ID</span><span class="info-val"><code>${u.id}</code></span></div>
        <div class="info-row"><span class="info-key">Username</span><span class="info-val">@${u.username||'—'}</span></div>
        <div class="info-row"><span class="info-key">Language</span><span class="info-val">${u.lang}</span></div>
        <div class="info-row"><span class="info-key">Balance</span><span class="info-val sp">$${u.balance}</span></div>
        <div class="info-row"><span class="info-key">Status</span><span class="info-val"><span class="ins ${u.banned?'r':'g'}">${u.banned?'🚫 Banned':'✅ Active'}</span></span></div>
        <div class="section-gap"></div>
        <div style="display:flex;gap:.6rem;flex-wrap:wrap;align-items:center">
          <input type="number" id="bal_amt" placeholder="Amount ($)" step="0.01" style="width:130px;padding:.5rem .8rem;background:var(--s);border:1.5px solid var(--b);border-radius:9px;color:var(--t);font-size:.85rem;font-family:'Inter',sans-serif;outline:none"/>
          <button class="btn btn-g" onclick="adjustBal(${u.id})">💰 Adjust Balance</button>
          <button class="btn ${u.banned?'btn-g':'btn-d'}" onclick="toggleBan(${u.id},${!u.banned})">${u.banned?'✅ Unban':'🚫 Ban'}</button>
        </div>
      </div>
      ${orders.length?`<div class="tw"><div class="th"><div class="th-t">Recent Orders</div></div><div class="tscroll"><table><thead><tr><th>Order ID</th><th>Product</th><th>Total</th><th>Status</th></tr></thead><tbody>${orows}</tbody></table></div></div>`:''}`;
  }catch(e){document.getElementById('user-result').innerHTML='<div class="ld">❌ Error</div>';}
}
async function adjustBal(uid){
  const amt=document.getElementById('bal_amt').value;
  if(!amt)return;
  const r=await fetch('/api/admin/addbal?key='+enc(K),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid,amount:amt})});
  const d=await r.json();
  if(d.ok){toast('✅ Balance updated! New: $'+d.new_balance);findUser();}else toast('❌ '+(d.error||'Failed'),'err');
}
async function toggleBan(uid,ban){
  const r=await fetch('/api/admin/ban?key='+enc(K),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid,banned:ban})});
  const d=await r.json();
  if(d.ok){toast(ban?'🚫 User banned':'✅ User unbanned');findUser();}else toast('❌ Failed','err');
}
</script>
</body>
</html>"""


async def home(request: Request):
    return HTMLResponse(DASH)


app = Starlette(routes=[
    Route("/api/telegram",          telegram,       methods=["POST"]),
    Route("/api/setup",             setup,          methods=["GET"]),
    Route("/api/stats",             stats_api,      methods=["GET"]),
    Route("/api/admin/products",    products_api,   methods=["GET"]),
    Route("/api/admin/setprice",    setprice_api,   methods=["POST"]),
    Route("/api/admin/delprice",    delprice_api,   methods=["POST"]),
    Route("/api/admin/setmarkup",   setmarkup_api,  methods=["POST"]),
    Route("/api/admin/user",        user_api,       methods=["GET"]),
    Route("/api/admin/addbal",      addbal_api,     methods=["POST"]),
    Route("/api/admin/ban",         ban_api,        methods=["POST"]),
    Route("/api/admin/order",       order_api,      methods=["GET"]),
    Route("/api/admin/refund",      refund_api,     methods=["POST"]),
    Route("/",                      home),
])
