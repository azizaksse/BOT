"""Vercel entry point. Routes:
  POST /api/telegram   <- Telegram updates (webhook)
  POST /api/cryptopay  <- CryptoBot "invoice_paid" notifications
  GET  /api/setup?key=SETUP_KEY  <- run once after each deploy
  GET  /api/stats?key=SETUP_KEY  <- JSON stats for dashboard
  GET  /                         <- Admin dashboard
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bot"))

from starlette.applications import Starlette  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse, HTMLResponse  # noqa: E402
from starlette.routing import Route  # noqa: E402

import core  # noqa: E402
from config import PUBLIC_URL, SETUP_KEY, WEBHOOK_SECRET  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")


async def telegram(request: Request):
    if request.headers.get("x-telegram-bot-api-secret-token") != WEBHOOK_SECRET:
        return JSONResponse({"ok": False}, status_code=403)
    try:
        await core.handle_telegram(await request.json())
    except Exception:
        log.exception("update failed")
    return JSONResponse({"ok": True})


async def cryptopay(request: Request):
    body = await request.body()
    if not core.verify_cryptopay(body, request.headers.get("crypto-pay-api-signature", "")):
        return JSONResponse({"ok": False}, status_code=401)
    try:
        await core.handle_cryptopay(json.loads(body))
    except Exception:
        log.exception("cryptopay webhook failed")
        return JSONResponse({"ok": False}, status_code=500)
    return JSONResponse({"ok": True})


async def setup(request: Request):
    if request.query_params.get("key") != SETUP_KEY:
        return JSONResponse({"ok": False, "error": "wrong key"}, status_code=403)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    try:
        return JSONResponse(await core.setup(PUBLIC_URL or f"https://{host}"))
    except Exception as e:
        log.exception("setup failed")
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)


async def stats_api(request: Request):
    if request.query_params.get("key") != SETUP_KEY:
        return JSONResponse({"ok": False, "error": "wrong key"}, status_code=403)
    try:
        import db
        await db.connect()
        data = await db.stats()
        await db.close()
        profit = data.get("revenue", 0) - data.get("cost", 0)
        profit_24h = data.get("revenue_24h", 0) - data.get("cost_24h", 0)
        return JSONResponse({
            "ok": True,
            "users": data.get("users", 0),
            "orders": data.get("orders", 0),
            "orders_24h": data.get("orders_24h", 0),
            "revenue": round(data.get("revenue", 0) / 100, 2),
            "revenue_24h": round(data.get("revenue_24h", 0) / 100, 2),
            "profit": round(profit / 100, 2),
            "profit_24h": round(profit_24h / 100, 2),
            "topups": round(data.get("topups", 0) / 100, 2),
            "balances": round(data.get("balances", 0) / 100, 2),
            "pending_orders": data.get("pending_orders", 0),
            "open_warranties": data.get("open_warranties", 0),
        })
    except Exception as e:
        log.exception("stats failed")
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Bot Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#07070f;--s:#0f0f1a;--c:#161625;--b:#252540;--a:#7c6fff;--a2:#ff6584;--a3:#43e97b;--a4:#f7c948;--t:#eeeeff;--m:#8888aa}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--t);min-height:100vh}
/* LOGIN */
#login{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:1rem;background:radial-gradient(ellipse at 50% -10%,rgba(124,111,255,.18) 0%,transparent 65%)}
.lcard{background:var(--c);border:1px solid var(--b);border-radius:28px;padding:3rem 2.5rem;width:100%;max-width:380px;text-align:center;box-shadow:0 40px 80px rgba(0,0,0,.5),0 0 0 1px rgba(255,255,255,.04)}
.llogo{font-size:4rem;margin-bottom:1.2rem;display:inline-block;animation:bob 3s ease-in-out infinite}
@keyframes bob{0%,100%{transform:translateY(0) rotate(0deg)}50%{transform:translateY(-8px) rotate(-3deg)}}
.ltitle{font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,#7c6fff 0%,#ff6584 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.3rem}
.lsub{color:var(--m);font-size:.88rem;margin-bottom:2rem;line-height:1.5}
.linput{width:100%;padding:1rem 1.2rem;background:var(--s);border:1.5px solid var(--b);border-radius:14px;color:var(--t);font-size:1rem;font-family:'Inter',sans-serif;outline:none;transition:.25s;margin-bottom:.9rem;letter-spacing:.05em}
.linput:focus{border-color:var(--a);box-shadow:0 0 0 4px rgba(124,111,255,.15)}
.lbtn{width:100%;padding:1rem;background:linear-gradient(135deg,#7c6fff,#9b59f5);border:none;border-radius:14px;color:#fff;font-size:1rem;font-weight:700;cursor:pointer;transition:.25s;font-family:'Inter',sans-serif;letter-spacing:.02em}
.lbtn:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(124,111,255,.45)}
.lerr{color:#ff6584;font-size:.83rem;display:none;margin-top:.6rem}
/* TOPBAR */
#app{display:none}
.topbar{background:rgba(15,15,26,.85);border-bottom:1px solid var(--b);padding:.9rem 2rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:200;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)}
.tl{display:flex;align-items:center;gap:.8rem}
.ticon{font-size:1.6rem}
.ttitle{font-size:1.05rem;font-weight:800;background:linear-gradient(135deg,#7c6fff,#ff6584);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.tr{display:flex;align-items:center;gap:1.2rem}
.live{display:flex;align-items:center;gap:.5rem}
.dot{width:7px;height:7px;background:#43e97b;border-radius:50%;animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(67,233,123,.5)}50%{box-shadow:0 0 0 6px rgba(67,233,123,0)}}
.live-txt{font-size:.78rem;color:var(--m);font-weight:500}
.rbtn{padding:.5rem 1.1rem;background:var(--c);border:1px solid var(--b);border-radius:9px;color:var(--t);font-size:.8rem;font-weight:500;cursor:pointer;font-family:'Inter',sans-serif;transition:.2s}
.rbtn:hover{border-color:var(--a);color:var(--a)}
/* MAIN */
.main{padding:2rem;max-width:1400px;margin:0 auto}
.stitle{font-size:.72rem;font-weight:700;color:var(--m);text-transform:uppercase;letter-spacing:.12em;margin:1.8rem 0 1rem}
.stitle:first-child{margin-top:0}
/* ALERT */
.alert{display:none;align-items:center;gap:.7rem;padding:1rem 1.4rem;border-radius:14px;margin-bottom:1.5rem;font-size:.88rem;font-weight:600;background:rgba(247,201,72,.1);border:1px solid rgba(247,201,72,.25);color:#f7c948}
/* STATS GRID */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:1rem}
.sc{background:var(--c);border:1px solid var(--b);border-radius:20px;padding:1.4rem;position:relative;overflow:hidden;transition:.3s;cursor:default}
.sc::after{content:'';position:absolute;inset:0;opacity:0;background:radial-gradient(circle at 50% 0%,var(--ga,.4),transparent 70%);transition:.3s;pointer-events:none}
.sc:hover{transform:translateY(-4px);box-shadow:0 16px 40px rgba(0,0,0,.4);border-color:rgba(124,111,255,.3)}
.sc:hover::after{opacity:1}
.sc-bar{position:absolute;top:0;left:0;right:0;height:3px;background:var(--gc)}
.sc-icon{font-size:1.7rem;margin-bottom:.9rem}
.sc-label{font-size:.72rem;color:var(--m);font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.3rem}
.sc-val{font-size:1.9rem;font-weight:900;line-height:1.1}
.sc-sub{font-size:.76rem;color:var(--m);margin-top:.4rem}
/* TABLE */
.tw{background:var(--c);border:1px solid var(--b);border-radius:20px;overflow:hidden}
.th{padding:1.2rem 1.5rem;border-bottom:1px solid var(--b);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.8rem}
.th-title{font-weight:700;font-size:.92rem}
.si{padding:.55rem 1rem;background:var(--s);border:1.5px solid var(--b);border-radius:9px;color:var(--t);font-size:.83rem;font-family:'Inter',sans-serif;outline:none;width:200px;transition:.2s}
.si:focus{border-color:var(--a)}
.tscroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;min-width:580px}
th{padding:.75rem 1.2rem;text-align:left;font-size:.68rem;font-weight:700;color:var(--m);text-transform:uppercase;letter-spacing:.1em;border-bottom:1px solid var(--b)}
td{padding:.88rem 1.2rem;font-size:.86rem;border-bottom:1px solid rgba(255,255,255,.03)}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(124,111,255,.05)}
.ins{display:inline-flex;align-items:center;gap:.3rem;padding:.22rem .65rem;border-radius:7px;font-size:.72rem;font-weight:700}
.g{background:rgba(67,233,123,.12);color:#43e97b}
.r{background:rgba(255,101,132,.12);color:#ff6584}
.sp{font-weight:800;color:#9b8fff}
.pc{font-weight:700;color:#43e97b}
/* LOADING */
.ld{text-align:center;padding:4rem;color:var(--m)}
.spin{width:38px;height:38px;border:3px solid var(--b);border-top-color:var(--a);border-radius:50%;animation:sp .75s linear infinite;margin:0 auto 1rem}
@keyframes sp{to{transform:rotate(360deg)}}
@media(max-width:700px){.main{padding:1rem}.grid{grid-template-columns:1fr 1fr}.si{width:130px}td,th{padding:.6rem .8rem}}
</style>
</head>
<body>
<div id="login">
  <div class="lcard">
    <span class="llogo">🤖</span>
    <div class="ltitle">Admin Dashboard</div>
    <div class="lsub">Secure access to your bot analytics,<br/>products, and live stats</div>
    <input id="ki" class="linput" type="password" placeholder="🔑  Enter setup key" onkeydown="if(event.key==='Enter')go()"/>
    <button class="lbtn" onclick="go()">Access Dashboard →</button>
    <div id="lerr" class="lerr">❌ Wrong key — try again</div>
  </div>
</div>

<div id="app">
  <div class="topbar">
    <div class="tl">
      <div class="ticon">⚡</div>
      <div class="ttitle">@golde1nbot</div>
    </div>
    <div class="tr">
      <div class="live"><div class="dot"></div><div class="live-txt">Live</div></div>
      <button class="rbtn" onclick="loadAll()">↻ Refresh</button>
    </div>
  </div>

  <div class="main">
    <div id="al" class="alert">⚠️ <span id="alt"></span></div>
    <div class="stitle">Overview</div>
    <div class="grid" id="sg"><div class="ld"><div class="spin"></div>Loading…</div></div>
    <div class="stitle">Products & Prices</div>
    <div class="tw">
      <div class="th">
        <div class="th-title">🛍 All Products — Nexa API (40% markup)</div>
        <input class="si" type="text" id="srch" placeholder="🔍 Search product…" oninput="fp()"/>
      </div>
      <div class="tscroll"><div id="pt"><div class="ld"><div class="spin"></div>Loading products…</div></div></div>
    </div>
  </div>
</div>

<script>
let K='',M=40,P=[];
function go(){const k=document.getElementById('ki').value.trim();if(!k)return;K=k;loadAll();}
async function loadAll(){
  try{
    const r=await fetch('/api/stats?key='+encodeURIComponent(K));
    const d=await r.json();
    if(!d.ok){err();return;}
    document.getElementById('login').style.display='none';
    document.getElementById('app').style.display='block';
    renderStats(d);alerts(d);
  }catch(e){err();}
  loadP();
}
function err(){document.getElementById('lerr').style.display='block';document.getElementById('ki').value='';}
function renderStats(d){
  const cs=[
    {i:'👥',l:'Users',v:d.users,s:'Customers',gc:'linear-gradient(90deg,#7c6fff,#9b59f5)',ga:'rgba(124,111,255,.2)'},
    {i:'📦',l:'Orders',v:d.orders,s:d.orders_24h+' today',gc:'linear-gradient(90deg,#43e97b,#38f9d7)',ga:'rgba(67,233,123,.15)'},
    {i:'💰',l:'Revenue',v:'$'+d.revenue,s:'$'+d.revenue_24h+' today',gc:'linear-gradient(90deg,#f7c948,#ffd700)',ga:'rgba(247,201,72,.15)'},
    {i:'📈',l:'Net Profit',v:'$'+d.profit,s:'$'+d.profit_24h+' today',gc:'linear-gradient(90deg,#43e97b,#00c9a7)',ga:'rgba(67,233,123,.15)'},
    {i:'💳',l:'Top-ups',v:'$'+d.topups,s:'USDT received',gc:'linear-gradient(90deg,#fa709a,#fee140)',ga:'rgba(250,112,154,.15)'},
    {i:'🏦',l:'Balances',v:'$'+d.balances,s:'In wallets',gc:'linear-gradient(90deg,#a78bfa,#c084fc)',ga:'rgba(167,139,250,.15)'},
    {i:'⏳',l:'Pending',v:d.pending_orders,s:'Awaiting delivery',gc:d.pending_orders?'linear-gradient(90deg,#f7c948,#ffd700)':'linear-gradient(90deg,#43e97b,#38f9d7)',ga:d.pending_orders?'rgba(247,201,72,.15)':'rgba(67,233,123,.15)'},
    {i:'🛠',l:'Warranties',v:d.open_warranties,s:'Open tickets',gc:d.open_warranties?'linear-gradient(90deg,#ff6584,#ff9a9e)':'linear-gradient(90deg,#43e97b,#38f9d7)',ga:d.open_warranties?'rgba(255,101,132,.15)':'rgba(67,233,123,.15)'},
  ];
  document.getElementById('sg').innerHTML=cs.map(c=>`<div class="sc" style="--gc:${c.gc};--ga:${c.ga}"><div class="sc-bar"></div><div class="sc-icon">${c.i}</div><div class="sc-label">${c.l}</div><div class="sc-val">${c.v}</div><div class="sc-sub">${c.s}</div></div>`).join('');
}
function alerts(d){
  const a=[];
  if(d.pending_orders>0)a.push(d.pending_orders+' pending order(s)');
  if(d.open_warranties>0)a.push(d.open_warranties+' warranty request(s)');
  if(a.length){document.getElementById('al').style.display='flex';document.getElementById('alt').textContent=a.join(' · ');}
}
async function loadP(){
  try{
    const r=await fetch('http://186.241.26.133:3000/api/v1/products',{headers:{'X-API-Key':'psk_58e93241996cb3519ccd27992c60a92677403ff471fbe04f'}});
    const d=await r.json();
    P=(d.products||[]).sort((a,b)=>b.in_stock-a.in_stock||a.name.localeCompare(b.name));
  }catch(e){P=[];}
  rp(P);
}
function rp(list){
  if(!list.length){document.getElementById('pt').innerHTML='<div class="ld">No products.</div>';return;}
  const rows=list.map(p=>{
    const s=(p.price*(1+M/100)).toFixed(2),pr=(s-p.price).toFixed(2);
    const st=p.in_stock?`<span class="ins g">🟢 ${p.stock} in stock</span>`:`<span class="ins r">🔴 Out of stock</span>`;
    return`<tr><td><b>${p.name}</b></td><td>$${p.price}</td><td><span class="sp">$${s}</span></td><td><span class="pc">+$${pr}</span></td><td>${st}</td></tr>`;
  }).join('');
  document.getElementById('pt').innerHTML=`<table><thead><tr><th>Product</th><th>Nexa Cost</th><th>Your Price</th><th>Profit</th><th>Stock</th></tr></thead><tbody>${rows}</tbody></table>`;
}
function fp(){const q=document.getElementById('srch').value.toLowerCase();rp(P.filter(p=>p.name.toLowerCase().includes(q)));}
</script>
</body>
</html>"""


async def home(request: Request):
    return HTMLResponse(DASHBOARD_HTML)


app = Starlette(routes=[
    Route("/api/telegram", telegram, methods=["POST"]),
    Route("/api/cryptopay", cryptopay, methods=["POST"]),
    Route("/api/setup", setup, methods=["GET"]),
    Route("/api/stats", stats_api, methods=["GET"]),
    Route("/", home),
])
