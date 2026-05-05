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

# Tous les users qui ont fait /start : chat_id -> chat_id
user_chat_ids = {}

# Derniers utilisateurs actifs par ordre d'arrivée (pour matching commande)
# telegram_username -> chat_id
username_to_chat_id = {}

# ============================================================
# COMMANDES BOT
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prenom = update.effective_user.first_name or "frérot"
    chat_id = update.effective_user.id
    # Stocker automatiquement le chat_id dès le /start
    user_chat_ids[chat_id] = chat_id
    username = update.effective_user.username
    if username:
        username_to_chat_id[username.lower()] = chat_id
        username_to_chat_id["@" + username.lower()] = chat_id
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
        adresse = data.get("adresse", "?")
        items = data.get("items", [])
        total = data.get("total", "?")
        dispo = data.get("dispo", "")
        needs_confirm = data.get("needs_confirm", False)
        telephone = data.get("telephone", "").strip().replace(" ", "").replace("-", "")

        pm_icons = {"paypal": "\U0001f17f\ufe0f PayPal", "virement": "\U0001f3e6 Virement", "especes": "\U0001f4b5 Esp\u00e8ces"}
        pm_label = pm_icons.get(payment, payment)
        items_text = "\n".join([f"  \u2022 {i.get('name','')} \u2014 {i.get('flavor','')} ({i.get('price','')} \u20ac)" for i in items])
        statut = "\u23f3 EN ATTENTE DE V\u00c9RIFICATION" if needs_confirm else "\u2705 CONFIRM\u00c9E"

        sep = "\u2501" * 30
        message = (
            f"\U0001f3ab *NOUVELLE COMMANDE \u2014 {statut}*\n"
            f"{sep}\n\n"
            f"\U0001f4cb *R\u00e9f\u00e9rence :* `{order_num}`\n"
            f"\U0001f4cd *Ville :* {city}\n"
            f"\U0001f4b3 *Paiement :* {pm_label}\n\n"
            f"\U0001f6d2 *Commande :*\n{items_text}\n\n"
            f"\U0001f4b0 *Total :* {total} \u20ac\n\n"
            f"\U0001f4ec *Livraison :*\n"
            f"  \u2022 T\u00e9l\u00e9phone : {telephone}\n"
            f"  \u2022 Adresse : {adresse}\n"
        )
        if dispo:
            message += f"  \u2022 Disponibilit\u00e9s : {dispo}\n"
        message += f"\n{sep}"

        bot_app = request.app["bot_app"]

        try:
            if needs_confirm:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "\u2705 Confirmer le paiement",
                        callback_data=f"confirm|{order_num}|{telephone}|{city}|{pm_label}|{adresse}|{total}"
                    )
                ]])
                await bot_app.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                await _send_pending_ticket_to_client(bot_app, telephone, order_num, city, pm_label, items_text, total, adresse)
            else:
                await bot_app.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=message,
                    parse_mode="Markdown"
                )
                await _send_ticket_to_client(bot_app, telephone, order_num, city, pm_label, items_text, total, adresse)
        except Exception as send_err:
            print(f"Erreur envoi owner: {send_err}")

        return web.json_response({"ok": True})
    except Exception as e:
        print(f"Ticket error: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def _send_pending_ticket_to_client(bot_app, telephone, order_num, city, pm_label, items_text, total, adresse):
    """Ticket en attente de confirmation envoyé au client dès la commande PayPal/Virement"""
    client_message = (
        f"⏳ *Commande reçue — en attente de confirmation*\n"
        f"{'━'*28}\n\n"
        f"📋 *Référence :* `{order_num}`\n"
        f"📍 *Ville :* {city}\n"
        f"💳 *Paiement :* {pm_label}\n\n"
        f"🛒 *Ta commande :*\n{items_text}\n\n"
        f"💰 *Total :* {total} €\n\n"
        f"📬 *Livraison à :* {adresse}\n\n"
        f"{'━'*28}\n"
        f"_Dès que ton paiement est confirmé, tu recevras un message. Merci !_ 🙏"
    )
    client_chat_id = phone_to_chat_id.get(telephone)
    if not client_chat_id:
        alt = "+33" + telephone[1:] if telephone.startswith("0") else telephone
        client_chat_id = phone_to_chat_id.get(alt)
    if client_chat_id:
        try:
            await bot_app.bot.send_message(chat_id=client_chat_id, text=client_message, parse_mode="Markdown")
        except Exception as e:
            print(f"Erreur ticket pending client: {e}")

async def _send_ticket_to_client(bot_app, telephone, order_num, city, pm_label, items_text, total, adresse):
    """Envoie le ticket au client via son numéro de téléphone (stocké lors du /start via partage contact)"""
    client_message = (
        f"🎫 *Ton ticket de commande*\n"
        f"{'━'*28}\n\n"
        f"📋 *Référence :* `{order_num}`\n"
        f"📍 *Ville :* {city}\n"
        f"💳 *Paiement :* {pm_label}\n\n"
        f"🛒 *Ta commande :*\n{items_text}\n\n"
        f"💰 *Total :* {total} €\n\n"
        f"📬 *Livraison à :* {adresse}\n\n"
        f"{'━'*28}\n"
        f"_On te contacte très prochainement pour organiser la livraison. Merci !_ 🙏"
    )
    # Chercher le chat_id via le numéro de téléphone
    client_chat_id = phone_to_chat_id.get(telephone)
    if not client_chat_id:
        alt = "+33" + telephone[1:] if telephone.startswith("0") else "0" + telephone.lstrip("+33")
        client_chat_id = phone_to_chat_id.get(alt)
    if client_chat_id:
        try:
            await bot_app.bot.send_message(chat_id=client_chat_id, text=client_message, parse_mode="Markdown")
            print(f"Ticket envoyé au client {telephone}")
        except Exception as e:
            print(f"Erreur envoi ticket client: {e}")
    else:
        print(f"Client introuvable pour numéro: {telephone} — il n'a peut-être pas fait /start et partagé son numéro")

async def _send_confirmation_to_client(bot_app, pseudo, order_num, city, pm_label, items_text, total, adresse):
    await _send_ticket_to_client(bot_app, pseudo, order_num, city, pm_label, items_text, total, adresse)


async def handle_confirm_callback(update, context):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split("|")
        _, order_num, telephone, city, pm_label, adresse, total = parts
        items_text = "—"
        await _send_ticket_to_client(context.application, telephone, order_num, city, pm_label, items_text, total, adresse)
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
