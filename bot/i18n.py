LANGS = {"en": "🇬🇧 English", "fr": "🇫🇷 Français", "ar": "🇸🇦 العربية"}

TEXTS = {
    "en": {
        "welcome": (
            "⚡ <b>Welcome back, {name}!</b>\n\n"
            "┌ 🛒 Instant digital products\n"
            "├ 💎 Crypto payments only\n"
            "└ ⚡ Delivered in seconds\n\n"
            "💰 Balance: <b>{balance} USDT</b>"
        ),
        "menu_title": (
            "🏪 <b>GOLD1N BOT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 Balance: <b>{balance} USDT</b>"
        ),
        "btn_products": "🛒  Browse Products",
        "btn_wallet":   "💳  My Wallet",
        "btn_orders":   "📦  My Orders",
        "btn_warranty": "🛡  Warranty",
        "btn_support":  "💬  Support",
        "btn_lang":     "🌍  Language",
        "btn_back":     "‹ Back",
        "btn_menu":     "🏪 GOLD1N BOT",
        "btn_refresh":  "🔄 Refresh",
        "btn_confirm":  "✅  Confirm & Pay",
        "btn_cancel":   "✖  Cancel",
        "btn_topup":    "➕  Top Up Now",
        "btn_custom":   "✏️  Custom Amount",
        "btn_pay":      "🔐  Pay with CryptoBot",
        "btn_check":    "✅  I Paid — Check",
        "btn_new_warranty": "🆕  New Request",
        "btn_contact":  "📨  Send Message",
        "products_title": (
            "🛒 <b>Products</b>  ·  Page {page} of {pages}\n"
            "🟢 In stock   🔴 Out of stock"
        ),
        "no_products":        "😔 No products available right now.\nCheck back soon!",
        "service_unavailable":"⚠️ Store temporarily unavailable.\nPlease try again in a moment.",
        "product_not_found":  "❌ Product no longer available.",
        "product_card": (
            "🏷 <b>{name}</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💵 Price:    <b>{price} USDT</b>\n"
            "📦 Stock:    <b>{stock} units</b>\n"
            "⚡ Delivery: <b>Instant</b>"
        ),
        "out_of_stock":  "🔴 <b>Out of stock</b> — check back soon.",
        "choose_qty":    "🔢 <b>Select quantity:</b>",
        "confirm_purchase": (
            "🧾 <b>Order Summary</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🏷 {name}\n"
            "🔢 Qty:      <b>{qty}</b>\n"
            "💵 Total:    <b>{total} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 Balance:  <b>{balance} USDT</b>"
        ),
        "processing":     "⏳ <b>Processing your order…</b>\nPlease wait a moment.",
        "please_wait":    "⏳ Your previous order is still being processed.",
        "not_enough_stock":"⚠️ Not enough stock. Please choose a smaller quantity.",
        "insufficient": (
            "❌ <b>Insufficient Balance</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💵 Total:    <b>{total} USDT</b>\n"
            "💰 Balance:  <b>{balance} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "👇 Top up your wallet to continue."
        ),
        "order_done": (
            "🎉 <b>Order Delivered!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🆔 <code>{id}</code>\n"
            "🏷 {name} × {qty}\n"
            "💵 Paid:     <b>{total} USDT</b>\n"
            "💰 Balance:  <b>{balance} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🔑 <b>Your items:</b>"
        ),
        "codes_in_file":        "📎 Your items are attached below.",
        "order_failed_refunded":"❌ Order <code>{id}</code> failed.\n<b>{total} USDT</b> refunded to your wallet.",
        "order_delayed":        "⚠️ Order <code>{id}</code> is delayed.\nOur team will deliver or refund shortly.",
        "wallet": (
            "💳 <b>My Wallet</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 Balance: <b>{balance} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Choose a top-up amount:"
        ),
        "enter_amount":   "✏️ Send the amount in USDT ({min} – {max}):",
        "invalid_amount": "❌ Invalid amount. Please send a number between {min} and {max}.",
        "invoice_created": (
            "🧾 Invoice: <b>{amount} USDT</b>\n\n"
            "Tap <b>Pay</b> and complete in @CryptoBot.\n"
            "Balance credited automatically. ⏳ Valid 1 hour."
        ),
        "invoice_error":   "⚠️ Could not create invoice. Please try again.",
        "payment_received":"✅ <b>Payment received!</b>\n+{amount} USDT added\n💰 Balance: <b>{balance} USDT</b>",
        "payment_pending": "⏳ Not confirmed yet. Finish in @CryptoBot then check again.",
        "payment_expired": "⌛ Invoice expired. Please create a new one.",
        "payment_already": "✅ This invoice was already credited.",
        "orders_title":    "📦 <b>Your Orders</b>\n\nTap any order to view details:",
        "no_orders":       "📭 No orders yet.\nVisit the store to get started!",
        "find_prompt":     "🔎 Send an order ID (e.g. <code>NX-AB12CD34</code>):",
        "order_not_found": "❌ Order not found.",
        "order_details": (
            "🧾 <b>Order Details</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🆔 <code>{id}</code>\n"
            "🏷 {name} × {qty}\n"
            "💵 Total:  <b>{total} USDT</b>\n"
            "📌 Status: {status}\n"
            "📅 {date}"
        ),
        "warranty_title": (
            "🛡 <b>Warranty Requests</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Have an issue with a product?\n"
            "Open a request and we'll fix it."
        ),
        "no_warranties":     "✅ No open warranty requests.",
        "warranty_item":     "#{id} · <code>{order}</code> · {status}",
        "warranty_ask_order":"🔢 Select an order or send its ID:",
        "warranty_bad_order":"❌ Order not found in your completed orders.",
        "warranty_exists":   "ℹ️ A request (#{id}) is already open for this order.",
        "warranty_ask_issue":"📝 Describe the issue (you can attach a screenshot):",
        "warranty_created":  "✅ Warranty <b>#{id}</b> created.\nWe'll reply here soon.",
        "warranty_reply":    "💬 <b>Reply to warranty #{id}:</b>\n\n{text}",
        "warranty_closed":   "✅ Warranty #{id} has been closed.",
        "support_text": (
            "💬 <b>Support</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Need help? Send us a message\n"
            "and include your order ID."
        ),
        "support_none":   "💬 Support not configured yet.",
        "choose_lang":    "🌐 <b>Choose your language:</b>",
        "lang_set":       "✅ Language updated!",
        "cancelled":      "✖️ Cancelled.",
        "refund_admin":   "↩️ Order <code>{id}</code> refunded: <b>+{total} USDT</b>.",
        "balance_adjusted":"💰 Balance adjusted: <b>{amount} USDT</b>\nNew balance: <b>{balance} USDT</b>",
        "st_processing": "🔄 Processing",
        "st_pending":    "⚠️ Delayed",
        "st_completed":  "✅ Completed",
        "st_refunded":   "↩️ Refunded",
        "st_failed":     "❌ Failed",
        "w_open":        "🟡 Open",
        "w_answered":    "💬 Answered",
        "w_closed":      "✅ Closed",
    },
    "fr": {
        "welcome": (
            "⚡ <b>Bon retour, {name} !</b>\n\n"
            "┌ 🛒 Produits numériques instantanés\n"
            "├ 💎 Paiement en crypto uniquement\n"
            "└ ⚡ Livraison en quelques secondes\n\n"
            "💰 Solde : <b>{balance} USDT</b>"
        ),
        "menu_title": (
            "🏪 <b>GOLD1N BOT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 Solde : <b>{balance} USDT</b>"
        ),
        "btn_products": "🛒  Voir les produits",
        "btn_wallet":   "💳  Mon portefeuille",
        "btn_orders":   "📦  Mes commandes",
        "btn_warranty": "🛡  Garantie",
        "btn_support":  "💬  Support",
        "btn_lang":     "🌍  Langue",
        "btn_back":     "‹ Retour",
        "btn_menu":     "🏪 GOLD1N BOT",
        "btn_refresh":  "🔄 Actualiser",
        "btn_confirm":  "✅  Confirmer et payer",
        "btn_cancel":   "✖  Annuler",
        "btn_topup":    "➕  Recharger maintenant",
        "btn_custom":   "✏️  Autre montant",
        "btn_pay":      "🔐  Payer avec CryptoBot",
        "btn_check":    "✅  J'ai payé — Vérifier",
        "btn_new_warranty": "🆕  Nouvelle demande",
        "btn_contact":  "📨  Envoyer un message",
        "products_title": (
            "🛒 <b>Produits</b>  ·  Page {page} sur {pages}\n"
            "🟢 En stock   🔴 Rupture"
        ),
        "no_products":        "😔 Aucun produit disponible.\nRevenez bientôt !",
        "service_unavailable":"⚠️ Boutique temporairement indisponible.\nRéessayez dans un moment.",
        "product_not_found":  "❌ Produit introuvable ou plus disponible.",
        "product_card": (
            "🏷 <b>{name}</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💵 Prix :      <b>{price} USDT</b>\n"
            "📦 Stock :     <b>{stock} unités</b>\n"
            "⚡ Livraison : <b>Instantanée</b>"
        ),
        "out_of_stock":  "🔴 <b>Rupture de stock</b> — revenez bientôt.",
        "choose_qty":    "🔢 <b>Choisissez la quantité :</b>",
        "confirm_purchase": (
            "🧾 <b>Récapitulatif</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🏷 {name}\n"
            "🔢 Quantité : <b>{qty}</b>\n"
            "💵 Total :    <b>{total} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 Solde :    <b>{balance} USDT</b>"
        ),
        "processing":     "⏳ <b>Traitement en cours…</b>\nVeuillez patienter.",
        "please_wait":    "⏳ Votre commande précédente est encore en cours.",
        "not_enough_stock":"⚠️ Stock insuffisant. Choisissez une quantité inférieure.",
        "insufficient": (
            "❌ <b>Solde insuffisant</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💵 Total requis : <b>{total} USDT</b>\n"
            "💰 Votre solde :  <b>{balance} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "👇 Rechargez votre portefeuille."
        ),
        "order_done": (
            "🎉 <b>Commande livrée !</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🆔 <code>{id}</code>\n"
            "🏷 {name} × {qty}\n"
            "💵 Payé :  <b>{total} USDT</b>\n"
            "💰 Solde : <b>{balance} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🔑 <b>Vos articles :</b>"
        ),
        "codes_in_file":        "📎 Vos articles sont dans le fichier joint.",
        "order_failed_refunded":"❌ Commande <code>{id}</code> échouée.\n<b>{total} USDT</b> remboursé.",
        "order_delayed":        "⚠️ Commande <code>{id}</code> retardée.\nLivraison ou remboursement en cours.",
        "wallet": (
            "💳 <b>Mon Portefeuille</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 Solde : <b>{balance} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Choisissez un montant :"
        ),
        "enter_amount":   "✏️ Envoyez le montant en USDT ({min} – {max}) :",
        "invalid_amount": "❌ Montant invalide. Envoyez un nombre entre {min} et {max}.",
        "invoice_created": (
            "🧾 Facture : <b>{amount} USDT</b>\n\n"
            "Appuyez sur <b>Payer</b> et finalisez dans @CryptoBot.\n"
            "Solde crédité automatiquement. ⏳ Valable 1 heure."
        ),
        "invoice_error":   "⚠️ Impossible de créer la facture. Réessayez.",
        "payment_received":"✅ <b>Paiement reçu !</b>\n+{amount} USDT ajouté\n💰 Solde : <b>{balance} USDT</b>",
        "payment_pending": "⏳ Pas encore confirmé. Terminez dans @CryptoBot puis vérifiez.",
        "payment_expired": "⌛ Facture expirée. Créez-en une nouvelle.",
        "payment_already": "✅ Cette facture a déjà été créditée.",
        "orders_title":    "📦 <b>Vos Commandes</b>\n\nAppuyez sur une commande pour voir les détails :",
        "no_orders":       "📭 Aucune commande pour l'instant.\nVisitez la boutique !",
        "find_prompt":     "🔎 Envoyez un ID de commande (ex. <code>NX-AB12CD34</code>) :",
        "order_not_found": "❌ Commande introuvable.",
        "order_details": (
            "🧾 <b>Détails de la commande</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🆔 <code>{id}</code>\n"
            "🏷 {name} × {qty}\n"
            "💵 Total :  <b>{total} USDT</b>\n"
            "📌 Statut : {status}\n"
            "📅 {date}"
        ),
        "warranty_title": (
            "🛡 <b>Garanties</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Un produit ne fonctionne pas ?\n"
            "Ouvrez une demande."
        ),
        "no_warranties":     "✅ Aucune demande de garantie ouverte.",
        "warranty_item":     "#{id} · <code>{order}</code> · {status}",
        "warranty_ask_order":"🔢 Choisissez une commande ou envoyez son ID :",
        "warranty_bad_order":"❌ Commande introuvable parmi vos commandes terminées.",
        "warranty_exists":   "ℹ️ Une demande (#{id}) est déjà ouverte pour cette commande.",
        "warranty_ask_issue":"📝 Décrivez le problème (vous pouvez joindre une capture) :",
        "warranty_created":  "✅ Garantie <b>#{id}</b> créée.\nNous répondrons ici bientôt.",
        "warranty_reply":    "💬 <b>Réponse à la garantie #{id} :</b>\n\n{text}",
        "warranty_closed":   "✅ Garantie #{id} clôturée.",
        "support_text": (
            "💬 <b>Support</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Besoin d'aide ? Envoyez-nous\n"
            "un message avec votre ID de commande."
        ),
        "support_none":   "💬 Support non configuré.",
        "choose_lang":    "🌐 <b>Choisissez votre langue :</b>",
        "lang_set":       "✅ Langue mise à jour !",
        "cancelled":      "✖️ Annulé.",
        "refund_admin":   "↩️ Commande <code>{id}</code> remboursée : <b>+{total} USDT</b>.",
        "balance_adjusted":"💰 Solde ajusté : <b>{amount} USDT</b>\nNouveau solde : <b>{balance} USDT</b>",
        "st_processing": "🔄 En cours",
        "st_pending":    "⚠️ Retardée",
        "st_completed":  "✅ Terminée",
        "st_refunded":   "↩️ Remboursée",
        "st_failed":     "❌ Échouée",
        "w_open":        "🟡 Ouverte",
        "w_answered":    "💬 Répondue",
        "w_closed":      "✅ Clôturée",
    },
    "ar": {
        "welcome": (
            "⚡ <b>أهلاً بعودتك، {name}!</b>\n\n"
            "┌ 🛒 منتجات رقمية فورية\n"
            "├ 💎 دفع بالعملات الرقمية فقط\n"
            "└ ⚡ تسليم في ثوانٍ\n\n"
            "💰 الرصيد: <b>{balance} USDT</b>"
        ),
        "menu_title": (
            "🏪 <b>GOLD1N BOT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 الرصيد: <b>{balance} USDT</b>"
        ),
        "btn_products": "🛒  تصفح المنتجات",
        "btn_wallet":   "💳  محفظتي",
        "btn_orders":   "📦  طلباتي",
        "btn_warranty": "🛡  الضمان",
        "btn_support":  "💬  الدعم",
        "btn_lang":     "🌍  اللغة",
        "btn_back":     "‹ رجوع",
        "btn_menu":     "🏪 GOLD1N BOT",
        "btn_refresh":  "🔄 تحديث",
        "btn_confirm":  "✅  تأكيد والدفع",
        "btn_cancel":   "✖  إلغاء",
        "btn_topup":    "➕  شحن الآن",
        "btn_custom":   "✏️  مبلغ آخر",
        "btn_pay":      "🔐  الدفع عبر CryptoBot",
        "btn_check":    "✅  دفعت — تحقق",
        "btn_new_warranty": "🆕  طلب جديد",
        "btn_contact":  "📨  إرسال رسالة",
        "products_title": (
            "🛒 <b>المنتجات</b>  ·  صفحة {page} من {pages}\n"
            "🟢 متوفر   🔴 غير متوفر"
        ),
        "no_products":        "😔 لا توجد منتجات حالياً.\nعد قريباً!",
        "service_unavailable":"⚠️ المتجر غير متاح مؤقتاً.\nحاول مرة أخرى بعد لحظة.",
        "product_not_found":  "❌ المنتج غير موجود أو لم يعد متاحاً.",
        "product_card": (
            "🏷 <b>{name}</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💵 السعر:     <b>{price} USDT</b>\n"
            "📦 المخزون:   <b>{stock} وحدة</b>\n"
            "⚡ التسليم:   <b>فوري</b>"
        ),
        "out_of_stock":  "🔴 <b>نفد المخزون</b> — عد قريباً.",
        "choose_qty":    "🔢 <b>اختر الكمية:</b>",
        "confirm_purchase": (
            "🧾 <b>ملخص الطلب</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🏷 {name}\n"
            "🔢 الكمية:    <b>{qty}</b>\n"
            "💵 الإجمالي: <b>{total} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 رصيدك:    <b>{balance} USDT</b>"
        ),
        "processing":     "⏳ <b>جارٍ معالجة طلبك…</b>\nيرجى الانتظار.",
        "please_wait":    "⏳ طلبك السابق لا يزال قيد المعالجة.",
        "not_enough_stock":"⚠️ المخزون غير كافٍ. اختر كمية أقل.",
        "insufficient": (
            "❌ <b>رصيد غير كافٍ</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💵 المطلوب:   <b>{total} USDT</b>\n"
            "💰 رصيدك:    <b>{balance} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "👇 اشحن محفظتك للمتابعة."
        ),
        "order_done": (
            "🎉 <b>تم تسليم طلبك!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🆔 <code>{id}</code>\n"
            "🏷 {name} × {qty}\n"
            "💵 المدفوع:   <b>{total} USDT</b>\n"
            "💰 الرصيد:    <b>{balance} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🔑 <b>منتجاتك:</b>"
        ),
        "codes_in_file":        "📎 منتجاتك في الملف المرفق.",
        "order_failed_refunded":"❌ فشل الطلب <code>{id}</code>.\nتم إرجاع <b>{total} USDT</b> إلى محفظتك.",
        "order_delayed":        "⚠️ الطلب <code>{id}</code> متأخر.\nسيتم التسليم أو الاسترداد قريباً.",
        "wallet": (
            "💳 <b>محفظتي</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 الرصيد: <b>{balance} USDT</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "اختر مبلغ الشحن:"
        ),
        "enter_amount":   "✏️ أرسل المبلغ بـ USDT ({min} – {max}):",
        "invalid_amount": "❌ مبلغ غير صالح. أرسل رقماً بين {min} و {max}.",
        "invoice_created": (
            "🧾 فاتورة: <b>{amount} USDT</b>\n\n"
            "اضغط <b>دفع</b> وأكمل الدفع في @CryptoBot.\n"
            "سيُضاف الرصيد تلقائياً. ⏳ صالحة ساعة."
        ),
        "invoice_error":   "⚠️ تعذّر إنشاء الفاتورة. حاول لاحقاً.",
        "payment_received":"✅ <b>تم استلام الدفع!</b>\n+{amount} USDT أُضيف\n💰 الرصيد: <b>{balance} USDT</b>",
        "payment_pending": "⏳ لم يتم التأكيد بعد. أكمل في @CryptoBot ثم تحقق.",
        "payment_expired": "⌛ انتهت صلاحية الفاتورة. أنشئ فاتورة جديدة.",
        "payment_already": "✅ تمت إضافة هذه الفاتورة مسبقاً.",
        "orders_title":    "📦 <b>طلباتك</b>\n\nاضغط على أي طلب لعرض التفاصيل:",
        "no_orders":       "📭 لا توجد طلبات بعد.\nتفضل بزيارة المتجر!",
        "find_prompt":     "🔎 أرسل رقم الطلب (مثال: <code>NX-AB12CD34</code>):",
        "order_not_found": "❌ الطلب غير موجود.",
        "order_details": (
            "🧾 <b>تفاصيل الطلب</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🆔 <code>{id}</code>\n"
            "🏷 {name} × {qty}\n"
            "💵 الإجمالي:  <b>{total} USDT</b>\n"
            "📌 الحالة:    {status}\n"
            "📅 {date}"
        ),
        "warranty_title": (
            "🛡 <b>طلبات الضمان</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "منتج لا يعمل؟\n"
            "افتح طلباً وسنحل المشكلة."
        ),
        "no_warranties":     "✅ لا توجد طلبات ضمان مفتوحة.",
        "warranty_item":     "#{id} · <code>{order}</code> · {status}",
        "warranty_ask_order":"🔢 اختر طلباً أو أرسل رقمه:",
        "warranty_bad_order":"❌ الطلب غير موجود ضمن طلباتك المكتملة.",
        "warranty_exists":   "ℹ️ يوجد طلب مفتوح مسبقاً (#{id}) لهذا الطلب.",
        "warranty_ask_issue":"📝 صف المشكلة (يمكنك إرفاق صورة):",
        "warranty_created":  "✅ تم إنشاء الضمان <b>#{id}</b>.\nسنرد عليك هنا قريباً.",
        "warranty_reply":    "💬 <b>رد على الضمان #{id}:</b>\n\n{text}",
        "warranty_closed":   "✅ تم إغلاق الضمان #{id}.",
        "support_text": (
            "💬 <b>الدعم</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "تحتاج مساعدة؟ أرسل لنا رسالة\n"
            "واذكر رقم طلبك."
        ),
        "support_none":   "💬 لم يتم إعداد الدعم بعد.",
        "choose_lang":    "🌐 <b>اختر لغتك:</b>",
        "lang_set":       "✅ تم تحديث اللغة!",
        "cancelled":      "✖️ تم الإلغاء.",
        "refund_admin":   "↩️ تم استرداد الطلب <code>{id}</code>: <b>+{total} USDT</b>.",
        "balance_adjusted":"💰 تم تعديل الرصيد: <b>{amount} USDT</b>\nالرصيد الجديد: <b>{balance} USDT</b>",
        "st_processing": "🔄 قيد المعالجة",
        "st_pending":    "⚠️ متأخر",
        "st_completed":  "✅ مكتمل",
        "st_refunded":   "↩️ مُسترد",
        "st_failed":     "❌ فشل",
        "w_open":        "🟡 مفتوح",
        "w_answered":    "💬 تم الرد",
        "w_closed":      "✅ مغلق",
    },
}

COMMANDS = {
    "en": [("start", "Start and open the menu"), ("menu", "Open the main menu"),
           ("products", "Browse products"), ("wallet", "My wallet & top up"),
           ("support", "Contact support"), ("warranty", "Warranty requests"),
           ("find", "Find an order"), ("lang", "Change language")],
    "fr": [("start", "Démarrer et ouvrir le menu"), ("menu", "Ouvrir le menu principal"),
           ("products", "Voir les produits"), ("wallet", "Portefeuille et recharge"),
           ("support", "Contacter le support"), ("warranty", "Demandes de garantie"),
           ("find", "Rechercher une commande"), ("lang", "Changer de langue")],
    "ar": [("start", "ابدأ وافتح القائمة"), ("menu", "فتح القائمة الرئيسية"),
           ("products", "تصفح المنتجات"), ("wallet", "المحفظة والشحن"),
           ("support", "الدعم"), ("warranty", "طلبات الضمان"),
           ("find", "البحث عن طلب"), ("lang", "تغيير اللغة")],
}


def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["en"]).get(key) or TEXTS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
