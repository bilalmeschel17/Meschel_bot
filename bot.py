import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from aiohttp import web
import json

BOT_TOKEN = os.environ.get("TOKEN")
# Ton chat ID Telegram — tu dois le récupérer en envoyant /start à @userinfobot
# Mets ton vrai ID ici après l'avoir récupéré
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID", "")
SITE_URL = "https://bilalmeschel17.github.io/puff-shop"
SUPPORT = "bilalmhl"

# Commandes confirmées en mémoire (order_num -> True)
confirmed_orders = set()

# Lien numéro de téléphone -> chat_id Telegram
phone_to_chat_id = {}

# ============================================================
# COMMANDES BOT
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import KeyboardButton, ReplyKeyboardMarkup
    prenom = update.effective_user.first_name or "frérot"
    texte = (
        f"Salut *{prenom}* 👊\n\n"
        "Bienvenue sur le shop 🛒\n\n"
        "🟣 *JNR 16K* — toutes les saveurs dispo\n"
        "🔴 *Razz Bar 60K* — toutes les saveurs dispo\n\n"
        "📱 *Partage ton numéro* pour recevoir ton ticket de commande directement ici 👇"
    )
    # Bouton pour partager le numéro
    reply_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Partager mon numéro", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=reply_kb)

async def produits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texte = (
        "📦 *Nos produits :*\n\n"
        "🟣 *JNR 16K* — 16 000 puffs, toutes saveurs — *10 €*\n"
        "🔴 *Razz Bar 60K* — 60 000 puffs, toutes saveurs — *15 €*\n\n"
        "👉 Commande sur le site !"
    )
    keyboard = [[InlineKeyboardButton("🛒 Commander", url=SITE_URL)]]
    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def monid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    await update.message.reply_text(
        f"🔑 Ton Chat ID : `{chat_id}`\n\nCopie ce numéro et mets-le dans Railway comme variable `OWNER_CHAT_ID`",
        parse_mode="Markdown"
    )

async def aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texte = (
        f"❓ *Aide*\n\nSupport : @{SUPPORT}\n\n"
        "/start — Accueil\n/produits — Produits\n/aide — Aide"
    )
    await update.message.reply_text(texte, parse_mode="Markdown")

# ============================================================
# WEBHOOK HTTP — reçoit les tickets depuis le site
# ============================================================


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
    contact = update.message.contact
    if contact:
        # Normaliser le numéro (enlever +33, espaces, etc.)
        phone = contact.phone_number.replace("+33", "0").replace(" ", "").replace("-", "")
        chat_id = update.effective_user.id
        phone_to_chat_id[phone] = chat_id
        # Aussi stocker les variantes courantes du numéro
        phone_to_chat_id[contact.phone_number] = chat_id
        prenom = update.effective_user.first_name or "toi"
        keyboard = [
            [InlineKeyboardButton("🛒 Passer commande", url=SITE_URL)],
            [InlineKeyboardButton("💬 Support", url=f"https://t.me/{SUPPORT}")],
        ]
        await update.message.reply_text(
            f"✅ Parfait *{prenom}* ! Ton numéro est enregistré.\n\nTu recevras ton ticket de commande ici après chaque achat. Clique ci-dessous pour commander 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Supprimer le clavier de partage
        await update.message.reply_text(".", reply_markup=ReplyKeyboardRemove())

async def handle_ticket(request):
    try:
        data = await request.json()
        order_num = data.get("order_num", "?")
        city = data.get("city", "?")
        payment = data.get("payment", "?")
        telegram = data.get("telegram", "?")
        adresse = data.get("adresse", "?")
        items = data.get("items", [])
        total = data.get("total", "?")
        dispo = data.get("dispo", "")
        needs_confirm = data.get("needs_confirm", False)  # PayPal/Virement = True

        pm_icons = {"paypal": "🅿️ PayPal", "virement": "🏦 Virement", "especes": "💵 Espèces"}
        pm_label = pm_icons.get(payment, payment)
        items_text = "\n".join([f"  • {i.get('name','')} — {i.get('flavor','')} ({i.get('price','')} €)" for i in items])

        # Statut selon méthode
        statut = "⏳ EN ATTENTE DE VÉRIFICATION" if needs_confirm else "✅ CONFIRMÉE"

        message = (
            f"🎫 *NOUVELLE COMMANDE — {statut}*\n"
            f"{'━'*30}\n\n"
            f"📋 *Référence :* `{order_num}`\n"
            f"📍 *Ville :* {city}\n"
            f"💳 *Paiement :* {pm_label}\n\n"
            f"🛒 *Commande :*\n{items_text}\n\n"
            f"💰 *Total :* {total} €\n\n"
            f"📬 *Livraison :*\n"
            f"  • Telegram : {telegram}\n"
            f"  • Adresse : {adresse}\n"
        )
        if dispo:
            message += f"  • Disponibilités : {dispo}\n"
        message += f"\n{'━'*30}"

        bot_app = request.app["bot_app"]
        client_pseudo = telegram.strip().lstrip("@")

        if OWNER_CHAT_ID:
            if needs_confirm:
                # Bouton inline pour confirmer le paiement
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "✅ Confirmer le paiement",
                        callback_data=f"confirm|{order_num}|{client_pseudo}|{city}|{pm_label}|{adresse}|{total}"
                    )
                ]])
                await bot_app.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            else:
                # Espèces : pas de vérif, on envoie direct sans bouton
                await bot_app.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=message,
                    parse_mode="Markdown"
                )
                # Notifier le client directement
                if client_pseudo:
                    await _send_confirmation_to_client(bot_app, client_pseudo, order_num, city, pm_label, items_text, total, adresse)

        return web.json_response({"ok": True})
    except Exception as e:
        print(f"Ticket error: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def _send_confirmation_to_client(bot_app, pseudo, order_num, city, pm_label, items_text, total, adresse):
    sep = "━" * 28
    client_message = (
        f"🎉 *Ta commande {order_num} est prête !*\n\n"
        f"Clique sur le bouton ci-dessous pour la consulter."
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "📦 Voir ma commande",
            url=f"{SITE_URL}#commandes"
        )
    ]])
    client_chat_id = phone_to_chat_id.get(pseudo)
    if not client_chat_id:
        alt = "+33" + pseudo[1:] if pseudo.startswith("0") else pseudo
        client_chat_id = phone_to_chat_id.get(alt)
    if client_chat_id:
        try:
            await bot_app.bot.send_message(
                chat_id=client_chat_id,
                text=client_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Client message error: {e}")
    else:
        print(f"Numéro non trouvé pour envoi confirmation: {pseudo}")


async def handle_confirm_callback(update, context):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split("|")
        _, order_num, pseudo, city, pm_label, adresse, total = parts
        items_text = "—"
        await _send_confirmation_to_client(context.application, pseudo, order_num, city, pm_label, items_text, total, adresse)
        # Marquer la commande comme confirmée
        confirmed_orders.add(order_num)
        await query.edit_message_text(
            text=query.message.text + f"\n\n✅ *Confirmation envoyée au client* (@{pseudo})",
            parse_mode="Markdown"
        )
    except Exception as e:
        await query.edit_message_text(text=f"Erreur : {e}")


async def handle_status(request):
    """Endpoint appelé par le site pour vérifier si une commande est confirmée"""
    try:
        order_num = request.match_info.get("order_num", "")
        confirmed = order_num in confirmed_orders
        return web.json_response({"confirmed": confirmed}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"confirmed": False, "error": str(e)}, status=500)

async def handle_health(request):
    return web.Response(text="OK")

# ============================================================
# MAIN — Lance bot + serveur HTTP en parallèle
# ============================================================
def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("produits", produits))
    app_bot.add_handler(CommandHandler("aide", aide))
    app_bot.add_handler(CommandHandler("monid", monid))
    app_bot.add_handler(CallbackQueryHandler(handle_confirm_callback, pattern=r"^confirm\|"))
    app_bot.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    # Serveur web
    web_app = web.Application()
    web_app["bot_app"] = app_bot
    web_app.router.add_post("/ticket", handle_ticket)
    web_app.router.add_get("/health", handle_health)
    web_app.router.add_get("/status/{order_num}", handle_status)

    port = int(os.environ.get("PORT", 8080))

    async def run():
        await app_bot.initialize()
        await app_bot.start()

        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"✅ Bot + serveur lancés sur port {port}")

        # Polling en arrière-plan
        await app_bot.updater.start_polling()
        await asyncio.Event().wait()

    asyncio.run(run())

if __name__ == "__main__":
    main()
