import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ============================================================
# CONFIG — mets ton token ici après avoir créé le bot sur @BotFather
# ============================================================
BOT_TOKEN = os.environ.get("TOKEN")  # Lu depuis la variable d'environnement Railway

# Lien vers ton site de commande
# ➡️ Mets ici l'URL de ton site une fois déployé sur GitHub Pages
SITE_URL = "https://TON_USERNAME.github.io/puff-shop"

# Ton pseudo Telegram pour le support
SUPPORT = "@bilalmhl"  # ← Remplace par ton vrai pseudo si différent

# ============================================================
# /start — Message d'accueil
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    prenom = user.first_name if user.first_name else "frérot"

    texte = (
        f"Salut *{prenom}* 👊\n\n"
        "Bienvenue sur le shop 🛒\n\n"
        "🟣 *JNR 16K* — toutes les saveurs dispo\n"
        "🔴 *Razz Bar 60K* — toutes les saveurs dispo\n\n"
        "Clique sur le bouton ci-dessous pour passer commande 👇"
    )

    keyboard = [
        [InlineKeyboardButton("🛒 Passer commande", url=SITE_URL)],
        [InlineKeyboardButton("💬 Support", url=f"https://t.me/{SUPPORT.replace('@', '')}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=reply_markup)


# ============================================================
# /produits — Liste des produits
# ============================================================
async def produits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texte = (
        "📦 *Nos produits disponibles :*\n\n"
        "🟣 *JNR 16K*\n"
        "Toutes les saveurs disponibles\n"
        "_(précise ta saveur lors de la commande)_\n\n"
        "🔴 *Razz Bar 60K*\n"
        "Toutes les saveurs disponibles\n"
        "_(précise ta saveur lors de la commande)_\n\n"
        "👉 Commande sur le site pour voir les prix et dispo !"
    )

    keyboard = [[InlineKeyboardButton("🛒 Commander maintenant", url=SITE_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=reply_markup)


# ============================================================
# /aide — Aide
# ============================================================
async def aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texte = (
        "❓ *Besoin d'aide ?*\n\n"
        f"Contacte le support direct : {SUPPORT}\n\n"
        "Commandes disponibles :\n"
        "/start — Accueil\n"
        "/produits — Voir les produits\n"
        "/aide — Aide"
    )
    await update.message.reply_text(texte, parse_mode="Markdown")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("produits", produits))
    app.add_handler(CommandHandler("aide", aide))

    print("✅ Bot lancé...")
    app.run_polling()
