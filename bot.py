import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web
import json

BOT_TOKEN = os.environ.get("TOKEN")
# Ton chat ID Telegram — tu dois le récupérer en envoyant /start à @userinfobot
# Mets ton vrai ID ici après l'avoir récupéré
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID", "")
SITE_URL = "https://bilalmeschel17.github.io/puff-shop"
SUPPORT = "bilalmhl"

# ============================================================
# COMMANDES BOT
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prenom = update.effective_user.first_name or "frérot"
    texte = (
        f"Salut *{prenom}* 👊\n\n"
        "Bienvenue sur le shop 🛒\n\n"
        "🟣 *JNR 16K* — toutes les saveurs dispo\n"
        "🔴 *Razz Bar 60K* — toutes les saveurs dispo\n\n"
        "Clique sur le bouton ci-dessous pour passer commande 👇"
    )
    keyboard = [
        [InlineKeyboardButton("🛒 Passer commande", url=SITE_URL)],
        [InlineKeyboardButton("💬 Support", url=f"https://t.me/{SUPPORT}")],
    ]
    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

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

        # Emojis par méthode
        pm_icons = {"paypal": "🅿️ PayPal", "virement": "🏦 Virement", "especes": "💵 Espèces"}
        pm_label = pm_icons.get(payment, payment)

        # Construire le recap articles
        items_text = "\n".join([f"  • {i.get('name','')} — {i.get('flavor','')} ({i.get('price','')} €)" for i in items])

        message = (
            f"🎫 *NOUVELLE COMMANDE*\n"
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

        # Envoyer au propriétaire
        if OWNER_CHAT_ID:
            await bot_app.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=message,
                parse_mode="Markdown"
            )

        # Envoyer le récap au client via son pseudo Telegram
        client_pseudo = data.get("telegram", "").strip().lstrip("@")
        if client_pseudo:
            client_message = (
                f"✅ *Commande confirmée !*\n"
                f"{'━'*28}\n\n"
                f"📋 *Référence :* `{order_num}`\n"
                f"📍 *Ville :* {city}\n"
                f"💳 *Paiement :* {pm_label}\n\n"
                f"🛒 *Votre commande :*\n{items_text}\n\n"
                f"💰 *Total :* {total} €\n\n"
                f"📬 *Livraison à :* {adresse}\n\n"
                f"{'━'*28}\n"
                f"_On vous contacte très prochainement pour organiser la livraison. Merci de votre confiance !_ 🙏"
            )
            try:
                await bot_app.bot.send_message(
                    chat_id=f"@{client_pseudo}",
                    text=client_message,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Client message error: {e}")

        return web.json_response({"ok": True})
    except Exception as e:
        print(f"Ticket error: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)

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

    # Serveur web
    web_app = web.Application()
    web_app["bot_app"] = app_bot
    web_app.router.add_post("/ticket", handle_ticket)
    web_app.router.add_get("/health", handle_health)

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
