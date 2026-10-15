import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

const str = v.union(v.string(), v.null());

// Amounts are integer cents. Field names match the Python code.
export default defineSchema({
  users: defineTable({
    id: v.number(), // Telegram user id
    username: str,
    lang: v.string(),
    balance: v.number(),
    banned: v.boolean(),
    created_at: v.number(),
  }).index("by_tg", ["id"]),

  orders: defineTable({
    id: v.string(), // NX-XXXXXXXX
    user_id: v.number(),
    product_id: v.string(),
    product_name: v.string(),
    quantity: v.number(),
    total: v.number(),
    cost: v.number(),
    status: v.string(), // processing | pending | completed | refunded
    idem_key: v.string(),
    nexa_order_id: str,
    codes: str, // JSON array
    created_at: v.number(),
    updated_at: v.number(),
  })
    .index("by_oid", ["id"])
    .index("by_user", ["user_id", "created_at"])
    .index("by_status", ["status"]),

  invoices: defineTable({
    invoice_id: v.number(),
    user_id: v.number(),
    amount: v.number(),
    pay_url: str,
    status: v.string(), // pending | paid | expired
    created_at: v.number(),
  })
    .index("by_inv", ["invoice_id"])
    .index("by_status", ["status"]),

  transactions: defineTable({
    user_id: v.number(),
    amount: v.number(),
    kind: v.string(),
    ref: str,
    created_at: v.number(),
  }).index("by_user", ["user_id"]),

  price_overrides: defineTable({ product_id: v.string(), price: v.number() }).index("by_product", ["product_id"]),
  settings: defineTable({ key: v.string(), value: v.string() }).index("by_key", ["key"]),

  warranties: defineTable({
    id: v.number(),
    user_id: v.number(),
    order_id: v.string(),
    issue: v.string(),
    status: v.string(), // open | answered | closed
    reply: str,
    created_at: v.number(),
  })
    .index("by_wid", ["id"])
    .index("by_user", ["user_id"])
    .index("by_order", ["order_id"])
    .index("by_status", ["status"]),

  fsm: defineTable({ k: v.string(), state: str, data: v.string() }).index("by_k", ["k"]),
  claims: defineTable({ k: v.string(), created_at: v.number() }).index("by_k", ["k"]).index("by_created", ["created_at"]),
  counters: defineTable({ name: v.string(), value: v.number() }).index("by_name", ["name"]),
});
