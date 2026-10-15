// Database functions used by the Telegram bot (called over HTTPS from Vercel).
// Every function requires `secret` == BOT_SECRET (set in Convex dashboard -> Settings -> Environment Variables),
// so nobody else can call them. Mutations are atomic transactions.
import { v } from "convex/values";
import { mutation, query, MutationCtx, QueryCtx } from "./_generated/server";

const str = v.union(v.string(), v.null());
const S = { secret: v.string() };

function check(secret: string) {
  const expected = process.env.BOT_SECRET;
  if (!expected || secret !== expected) throw new Error("unauthorized");
}
const now = () => Math.floor(Date.now() / 1000);

// ---------- helpers ----------
const userDoc = (ctx: QueryCtx, id: number) =>
  ctx.db.query("users").withIndex("by_tg", (q) => q.eq("id", id)).unique();
const orderDoc = (ctx: QueryCtx, id: string) =>
  ctx.db.query("orders").withIndex("by_oid", (q) => q.eq("id", id.trim().toUpperCase())).unique();
const invoiceDoc = (ctx: QueryCtx, id: number) =>
  ctx.db.query("invoices").withIndex("by_inv", (q) => q.eq("invoice_id", id)).unique();
const fsmDoc = (ctx: QueryCtx, k: string) =>
  ctx.db.query("fsm").withIndex("by_k", (q) => q.eq("k", k)).unique();

async function doCredit(ctx: MutationCtx, uid: number, cents: number, kind: string, ref: string | null) {
  const u = await userDoc(ctx, uid);
  if (!u) return false;
  await ctx.db.patch(u._id, { balance: u.balance + cents });
  await ctx.db.insert("transactions", { user_id: uid, amount: cents, kind, ref, created_at: now() });
  return true;
}

// ---------- dedupe ----------
export const claim = mutation({
  args: { ...S, k: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const existing = await ctx.db.query("claims").withIndex("by_k", (q) => q.eq("k", a.k)).unique();
    if (existing) return false;
    await ctx.db.insert("claims", { k: a.k, created_at: now() });
    return true;
  },
});

export const cleanup = mutation({
  args: { ...S, before: v.number() },
  handler: async (ctx, a) => {
    check(a.secret);
    const old = await ctx.db.query("claims").withIndex("by_created", (q) => q.lt("created_at", a.before)).take(1000);
    for (const d of old) await ctx.db.delete(d._id);
    return old.length;
  },
});

// ---------- FSM ----------
export const fsmGet = query({
  args: { ...S, k: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    return await fsmDoc(ctx, a.k);
  },
});

export const fsmSetState = mutation({
  args: { ...S, k: v.string(), state: str },
  handler: async (ctx, a) => {
    check(a.secret);
    const d = await fsmDoc(ctx, a.k);
    if (d) await ctx.db.patch(d._id, { state: a.state });
    else await ctx.db.insert("fsm", { k: a.k, state: a.state, data: "{}" });
  },
});

export const fsmSetData = mutation({
  args: { ...S, k: v.string(), data: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const d = await fsmDoc(ctx, a.k);
    if (d) await ctx.db.patch(d._id, { data: a.data });
    else await ctx.db.insert("fsm", { k: a.k, state: null, data: a.data });
  },
});

// ---------- users ----------
export const getOrCreateUser = mutation({
  args: { ...S, id: v.number(), username: str, lang: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const u = await userDoc(ctx, a.id);
    if (u) {
      if (u.username !== a.username) await ctx.db.patch(u._id, { username: a.username });
      return { ...u, username: a.username };
    }
    const _id = await ctx.db.insert("users", {
      id: a.id, username: a.username, lang: a.lang, balance: 0, banned: false, created_at: now(),
    });
    return await ctx.db.get(_id);
  },
});

export const getUser = query({
  args: { ...S, id: v.number() },
  handler: async (ctx, a) => {
    check(a.secret);
    return await userDoc(ctx, a.id);
  },
});

export const setLang = mutation({
  args: { ...S, id: v.number(), lang: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const u = await userDoc(ctx, a.id);
    if (u) await ctx.db.patch(u._id, { lang: a.lang });
  },
});

export const setBanned = mutation({
  args: { ...S, id: v.number(), banned: v.boolean() },
  handler: async (ctx, a) => {
    check(a.secret);
    const u = await userDoc(ctx, a.id);
    if (!u) return false;
    await ctx.db.patch(u._id, { banned: a.banned });
    return true;
  },
});

export const allUserIds = query({
  args: { ...S },
  handler: async (ctx, a) => {
    check(a.secret);
    const users = await ctx.db.query("users").collect();
    return users.filter((u) => !u.banned).map((u) => u.id);
  },
});

export const credit = mutation({
  args: { ...S, id: v.number(), cents: v.number(), kind: v.string(), ref: str },
  handler: async (ctx, a) => {
    check(a.secret);
    return await doCredit(ctx, a.id, a.cents, a.kind, a.ref);
  },
});

export const debit = mutation({
  args: { ...S, id: v.number(), cents: v.number(), kind: v.string(), ref: str },
  handler: async (ctx, a) => {
    check(a.secret);
    const u = await userDoc(ctx, a.id);
    if (!u || u.balance < a.cents) return false;
    await ctx.db.patch(u._id, { balance: u.balance - a.cents });
    await ctx.db.insert("transactions", { user_id: a.id, amount: -a.cents, kind: a.kind, ref: a.ref, created_at: now() });
    return true;
  },
});

// ---------- orders ----------
export const createOrder = mutation({
  args: {
    ...S, id: v.string(), user_id: v.number(), product_id: v.string(), product_name: v.string(),
    quantity: v.number(), total: v.number(), cost: v.number(), idem_key: v.string(),
  },
  handler: async (ctx, a) => {
    check(a.secret);
    const { secret, ...o } = a;
    const t = now();
    await ctx.db.insert("orders", { ...o, status: "processing", nexa_order_id: null, codes: null, created_at: t, updated_at: t });
  },
});

export const getOrder = query({
  args: { ...S, id: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    return await orderDoc(ctx, a.id);
  },
});

export const userOrders = query({
  args: { ...S, user_id: v.number(), limit: v.number() },
  handler: async (ctx, a) => {
    check(a.secret);
    return await ctx.db.query("orders").withIndex("by_user", (q) => q.eq("user_id", a.user_id)).order("desc").take(a.limit);
  },
});

export const setOrderStatus = mutation({
  args: { ...S, id: v.string(), status: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const o = await orderDoc(ctx, a.id);
    if (o) await ctx.db.patch(o._id, { status: a.status, updated_at: now() });
  },
});

export const completeOrder = mutation({
  args: { ...S, id: v.string(), codes: v.string(), nexa_order_id: str },
  handler: async (ctx, a) => {
    check(a.secret);
    const o = await orderDoc(ctx, a.id);
    if (o) await ctx.db.patch(o._id, { status: "completed", codes: a.codes, nexa_order_id: a.nexa_order_id, updated_at: now() });
  },
});

export const refundOrder = mutation({
  args: { ...S, id: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const o = await orderDoc(ctx, a.id);
    if (!o || o.status === "refunded") return false;
    await ctx.db.patch(o._id, { status: "refunded", updated_at: now() });
    return await doCredit(ctx, o.user_id, o.total, "refund", o.id);
  },
});

// ---------- invoices ----------
export const addInvoice = mutation({
  args: { ...S, invoice_id: v.number(), user_id: v.number(), amount: v.number(), pay_url: str },
  handler: async (ctx, a) => {
    check(a.secret);
    const { secret, ...inv } = a;
    await ctx.db.insert("invoices", { ...inv, status: "pending", created_at: now() });
  },
});

export const getInvoice = query({
  args: { ...S, invoice_id: v.number() },
  handler: async (ctx, a) => {
    check(a.secret);
    return await invoiceDoc(ctx, a.invoice_id);
  },
});

export const setInvoiceStatus = mutation({
  args: { ...S, invoice_id: v.number(), status: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const inv = await invoiceDoc(ctx, a.invoice_id);
    if (inv && inv.status === "pending") await ctx.db.patch(inv._id, { status: a.status });
  },
});

// Credits the user exactly once, even if CryptoBot sends the webhook twice.
export const markInvoicePaid = mutation({
  args: { ...S, invoice_id: v.number() },
  handler: async (ctx, a) => {
    check(a.secret);
    const inv = await invoiceDoc(ctx, a.invoice_id);
    if (!inv || inv.status === "paid") return null;
    await ctx.db.patch(inv._id, { status: "paid" });
    await doCredit(ctx, inv.user_id, inv.amount, "topup", String(inv.invoice_id));
    return { ...inv, status: "paid" };
  },
});

// ---------- settings / pricing ----------
export const getSetting = query({
  args: { ...S, key: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const d = await ctx.db.query("settings").withIndex("by_key", (q) => q.eq("key", a.key)).unique();
    return d ? d.value : null;
  },
});

export const setSetting = mutation({
  args: { ...S, key: v.string(), value: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const d = await ctx.db.query("settings").withIndex("by_key", (q) => q.eq("key", a.key)).unique();
    if (d) await ctx.db.patch(d._id, { value: a.value });
    else await ctx.db.insert("settings", { key: a.key, value: a.value });
  },
});

export const getOverrides = query({
  args: { ...S },
  handler: async (ctx, a) => {
    check(a.secret);
    return await ctx.db.query("price_overrides").collect();
  },
});

export const setOverride = mutation({
  args: { ...S, product_id: v.string(), price: v.number() },
  handler: async (ctx, a) => {
    check(a.secret);
    const d = await ctx.db.query("price_overrides").withIndex("by_product", (q) => q.eq("product_id", a.product_id)).unique();
    if (d) await ctx.db.patch(d._id, { price: a.price });
    else await ctx.db.insert("price_overrides", { product_id: a.product_id, price: a.price });
  },
});

export const delOverride = mutation({
  args: { ...S, product_id: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const d = await ctx.db.query("price_overrides").withIndex("by_product", (q) => q.eq("product_id", a.product_id)).unique();
    if (!d) return false;
    await ctx.db.delete(d._id);
    return true;
  },
});

// ---------- warranties ----------
export const createWarranty = mutation({
  args: { ...S, user_id: v.number(), order_id: v.string(), issue: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const c = await ctx.db.query("counters").withIndex("by_name", (q) => q.eq("name", "warranty")).unique();
    const id = (c?.value ?? 0) + 1;
    if (c) await ctx.db.patch(c._id, { value: id });
    else await ctx.db.insert("counters", { name: "warranty", value: id });
    await ctx.db.insert("warranties", {
      id, user_id: a.user_id, order_id: a.order_id, issue: a.issue, status: "open", reply: null, created_at: now(),
    });
    return id;
  },
});

export const getWarranty = query({
  args: { ...S, id: v.number() },
  handler: async (ctx, a) => {
    check(a.secret);
    return await ctx.db.query("warranties").withIndex("by_wid", (q) => q.eq("id", a.id)).unique();
  },
});

export const userWarranties = query({
  args: { ...S, user_id: v.number(), limit: v.number() },
  handler: async (ctx, a) => {
    check(a.secret);
    return await ctx.db.query("warranties").withIndex("by_user", (q) => q.eq("user_id", a.user_id)).order("desc").take(a.limit);
  },
});

export const openWarrantyForOrder = query({
  args: { ...S, order_id: v.string() },
  handler: async (ctx, a) => {
    check(a.secret);
    const list = await ctx.db.query("warranties").withIndex("by_order", (q) => q.eq("order_id", a.order_id)).collect();
    return list.find((w) => w.status !== "closed") ?? null;
  },
});

export const updateWarranty = mutation({
  args: { ...S, id: v.number(), status: v.string(), reply: v.optional(v.string()) },
  handler: async (ctx, a) => {
    check(a.secret);
    const w = await ctx.db.query("warranties").withIndex("by_wid", (q) => q.eq("id", a.id)).unique();
    if (!w) return;
    await ctx.db.patch(w._id, a.reply === undefined ? { status: a.status } : { status: a.status, reply: a.reply });
  },
});

// ---------- stats ----------
export const stats = query({
  args: { ...S },
  handler: async (ctx, a) => {
    check(a.secret);
    const since = now() - 86400;
    const users = await ctx.db.query("users").collect();
    const done = await ctx.db.query("orders").withIndex("by_status", (q) => q.eq("status", "completed")).collect();
    const today = done.filter((o) => o.created_at >= since);
    const paid = await ctx.db.query("invoices").withIndex("by_status", (q) => q.eq("status", "paid")).collect();
    const pending = (await ctx.db.query("orders").withIndex("by_status", (q) => q.eq("status", "pending")).collect()).length
      + (await ctx.db.query("orders").withIndex("by_status", (q) => q.eq("status", "processing")).collect()).length;
    const wopen = await ctx.db.query("warranties").withIndex("by_status", (q) => q.eq("status", "open")).collect();
    const sum = (xs: number[]) => xs.reduce((s, x) => s + x, 0);
    return {
      users: users.length, balances: sum(users.map((u) => u.balance)),
      orders: done.length, revenue: sum(done.map((o) => o.total)), cost: sum(done.map((o) => o.cost)),
      orders_24h: today.length, revenue_24h: sum(today.map((o) => o.total)), cost_24h: sum(today.map((o) => o.cost)),
      topups: sum(paid.map((i) => i.amount)), pending_orders: pending, open_warranties: wopen.length,
    };
  },
});
