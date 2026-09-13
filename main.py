"""
╔══════════════════════════════════════════════════╗
║       HIND DEALS BOT v3.0  —  main.py           ║
║  Extended from bot.py with paginated start menu  ║
║  • Dynamic paginated /start service browse       ║
║  • Auto-reflect admin add/remove/toggle          ║
║  • Out-of-stock badges kept visible              ║
║  • All bot.py systems preserved unchanged        ║
╚══════════════════════════════════════════════════╝
"""

import asyncio
import logging
import sqlite3
import random
import string
import os
import re
import qrcode
from io import BytesIO
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    Message, CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ══════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════
BOT_TOKEN          = "8738071957:AAFswpTbZJXBAcufUdSDfSgHzGO-2P0hBRQ"
OWNER_ID           = 8733687681           # Only owner can add/remove admins
CHANNEL_USERNAME   = "HIIND_DEALS_OFFICIAL"
UPI_ID             = "12749702@axl"
DB_NAME            = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hind_deals_mini.db")

REFERRAL_REWARD        = 5    # ₹ credited to referrer
WELCOME_BONUS          = 2    # ₹ credited to new user on first referral join
REFERRAL_UNLOCK_COUNT  = 10   # referrals needed to unlock wallet spending

# ── Payment Gateway (iPey.shop / UPI gateway panel) ─
GATEWAY_BASE_DEFAULT  = "https://ipey.shop"
GATEWAY_TIMEOUT       = 25      # seconds per API call
GATEWAY_POLL_SECONDS  = 15      # auto-verify interval
GATEWAY_EXPIRY_MIN    = 30      # pending payment expires after this

# ── QR / Auto-approval ─────────────────────────────
QR_VALID_MIN   = 10     # ek QR itne minute valid rehta hai (regenerate nahi hota)
AUTO_APPROVAL  = False  # ❌ auto approval OFF — har payment admin manually approve karega

# ── Pagination constants ───────────────────────────
START_MENU_PER_PAGE  = 11   # services shown per page on /start browse menu
STOCK_ADMIN_PER_PAGE = 10   # services shown per page in admin stock/service panels

if not CHANNEL_USERNAME.startswith("@"):
    CHANNEL_USERNAME = "@" + CHANNEL_USERNAME

# ══════════════════════════════════════════════════
#  LOGGING & CORE
# ══════════════════════════════════════════════════
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

# ══════════════════════════════════════════════════
#  DEFAULT PRODUCTS (used to seed DB on first run)
# ══════════════════════════════════════════════════
DEFAULT_PRODUCTS = {
    "netflix":        {"display_name": "Netflix Premium",          "keywords": ["netflix","nf","netflix premium"],                "description": "🎞️ Unlimited Movies & Series\n• 4K Ultra HD Quality\n• Multiple Screens\n• Netflix Originals Access",                    "prices": {"1 Month": 120, "3 Months": 329, "6 Months": 599, "1 Year": 1099}, "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "youtube":        {"display_name": "YouTube Premium",          "keywords": ["youtube","yt","youtube premium"],                "description": "🎵 No Ads on YouTube\n• Background Play\n• Video Downloads\n• YouTube Music Included",                              "prices": {"1 Month": 19,  "3 Months": 58,  "6 Months": 115, "1 Year": 219},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "youtubefamily":  {"display_name": "YouTube Family",           "keywords": ["youtube family","yt family"],                   "description": "👨‍👩‍👧 YouTube Family\n• Premium For Multiple Members\n• Ad-Free Videos\n• Separate Accounts",                           "prices": {"1 Month": 59,  "3 Months": 149, "6 Months": 269, "1 Year": 499},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "spotify":        {"display_name": "Spotify Premium",          "keywords": ["spotify","sp","spotify premium"],               "description": "🎶 Ad-Free Music\n• Offline Downloads\n• Unlimited Skips\n• High Audio Quality",                                      "prices": {"1 Month": 39,  "3 Months": 89,  "6 Months": 149, "1 Year": 249},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "jiohotstar":     {"display_name": "JioHotstar Premium",       "keywords": ["jiohotstar","hotstar","jio hotstar"],           "description": "📺 Live IPL & Sports\n• Latest Movies & Shows\n• Ad-Free Streaming\n• 4K Support",                                    "prices": {"1 Month": 39,  "3 Months": 90,  "6 Months": 160, "1 Year": 409},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "amazon":         {"display_name": "Amazon Prime Video",       "keywords": ["amazon","prime","amazon prime"],                "description": "🍿 Prime Movies & Web Series\n• Fast Delivery Benefits\n• Prime Music Included",                                       "prices": {"1 Month": 50,  "3 Months": 99,  "6 Months": 129, "1 Year": 249},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "sony":           {"display_name": "Sony LIV Premium",         "keywords": ["sony","sonyliv","sony liv"],                   "description": "🎬 WWE, UEFA & Sports\n• Sony TV Shows Early Access\n• Ad-Free Streaming",                                           "prices": {"1 Month": 49,  "3 Months": 109, "6 Months": 179, "1 Year": 259},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "zee5":           {"display_name": "ZEE5 Premium",             "keywords": ["zee5","zee","z5"],                             "description": "📡 Hindi & South Movies\n• TV Shows Before TV\n• Originals & Web Series",                                           "prices": {"1 Month": 39,  "3 Months": 89,  "6 Months": 149, "1 Year": 210},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "hoichoi":        {"display_name": "Hoichoi Premium",          "keywords": ["hoichoi","bengali"],                           "description": "❤️ Bengali Movies & Series\n• Exclusive Originals\n• HD Streaming",                                                "prices": {"1 Month": 49,  "3 Months": 99,  "6 Months": 169, "1 Year": 279},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "altbalaji":      {"display_name": "ALTBalaji Premium",        "keywords": ["altbalaji","alt balaji","alt"],                "description": "🎥 Indian Web Series\n• Exclusive Drama Content\n• HD Streaming",                                                    "prices": {"1 Month": 35,  "3 Months": 79,  "6 Months": 129, "1 Year": 219},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "discovery":      {"display_name": "Discovery+ Premium",       "keywords": ["discovery","discovery plus"],                  "description": "🌟 Discovery & Animal Planet\n• Science & Reality Shows\n• Ad-Free Viewing",                                          "prices": {"1 Month": 35,  "3 Months": 79,  "6 Months": 129, "1 Year": 219},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "lionsgate":      {"display_name": "Lionsgate Play",           "keywords": ["lionsgate","lions gate"],                      "description": "🎭 Hollywood Movies & Series\n• Premium English Content\n• HD Streaming",                                           "prices": {"1 Month": 39,  "3 Months": 89,  "6 Months": 149, "1 Year": 249},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "mxplayer":       {"display_name": "MX Player Gold",           "keywords": ["mx","mx player","mxplayer"],                   "description": "📱 Ad-Free Movies\n• Premium MX Originals\n• Live TV Access",                                                      "prices": {"1 Month": 29,  "3 Months": 69,  "6 Months": 119, "1 Year": 199},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "chaupal":        {"display_name": "Chaupal Premium",          "keywords": ["chaupal","punjabi"],                           "description": "🎦 Punjabi Movies & Shows\n• Regional Content\n• Exclusive Originals",                                            "prices": {"1 Month": 39,  "3 Months": 89,  "6 Months": 149, "1 Year": 249},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "applemusic":     {"display_name": "Apple Music",              "keywords": ["apple music","apple"],                         "description": "🎧 High Quality Audio\n• Millions of Songs\n• Offline Music\n• Dolby Atmos",                                         "prices": {"1 Month": 49,  "3 Months": 109, "6 Months": 189, "1 Year": 299},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "gaana":          {"display_name": "Gaana Plus",               "keywords": ["gaana","gaana plus"],                          "description": "📻 Ad-Free Songs\n• HD Music Quality\n• Unlimited Downloads",                                                       "prices": {"1 Month": 25,  "3 Months": 59,  "6 Months": 99,  "1 Year": 179},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "wynk":           {"display_name": "Wynk Music Premium",       "keywords": ["wynk","wynk music"],                           "description": "🎼 Caller Tunes\n• Offline Music\n• Ad-Free Streaming",                                                          "prices": {"1 Month": 19,  "3 Months": 49,  "6 Months": 89,  "1 Year": 149},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "chatgpt":        {"display_name": "ChatGPT Plus",             "keywords": ["chatgpt","gpt","chat gpt","chatgpt plus"],     "description": "🤖 Faster Responses\n• Advanced AI Access\n• Better Writing & Coding\n• GPT-4 Access",                              "prices": {"1 Month": 149, "3 Months": 399, "6 Months": 699, "1 Year": 1299}, "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "gemini":         {"display_name": "Gemini Premium + 2TB",     "keywords": ["gemini","google gemini"],                      "description": "🍃 Gemini AI Access\n• 2TB Google Storage\n• AI Writing & Research",                                              "prices": {"1 Month": 39,  "3 Months": 109, "6 Months": 149, "1 Year": 179},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "claudeai":       {"display_name": "Claude AI Pro",            "keywords": ["claude","claude ai","claude pro"],             "description": "🧠 Smart AI Answers\n• Long File Analysis\n• Coding & Writing Help",                                             "prices": {"1 Month": 149, "3 Months": 399, "6 Months": 699, "1 Year": 1199}, "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "blackbox":       {"display_name": "Blackbox AI Premium",      "keywords": ["blackbox","blackbox ai"],                      "description": "⚡ Coding AI Assistant\n• Error Fixing\n• Code Generation",                                                       "prices": {"1 Month": 69,  "3 Months": 150, "6 Months": 269, "1 Year": 449},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "canva":          {"display_name": "Canva Pro",                "keywords": ["canva","canva pro"],                           "description": "🎨 Premium Templates\n• AI Design Tools\n• Background Remover\n• Unlimited Exports",                               "prices": {"1 Month": 39,  "3 Months": 109, "6 Months": 149, "1 Year": 179},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "picsart":        {"display_name": "PicsArt Premium",          "keywords": ["picsart","picsart premium"],                   "description": "🖌️ Premium Editing Tools\n• AI Photo Effects\n• No Watermark",                                                    "prices": {"1 Month": 60,  "3 Months": 119, "6 Months": 169, "1 Year": 210},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "remini":         {"display_name": "Remini Premium",           "keywords": ["remini","remini premium"],                     "description": "✨ AI Photo Enhance\n• Blur Fix\n• Face Enhancement\n• HD Quality",                                             "prices": {"1 Month": 49,  "3 Months": 119, "6 Months": 199, "1 Year": 349},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "capcut":         {"display_name": "CapCut Pro",               "keywords": ["capcut","capcut pro"],                         "description": "🎬 Premium Video Effects\n• No Watermark\n• AI Editing Tools",                                                  "prices": {"1 Month": 49,  "3 Months": 109, "6 Months": 189, "1 Year": 329},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "kinemaster":     {"display_name": "KineMaster Premium",       "keywords": ["kinemaster","km","kine master"],               "description": "🎥 Pro Video Editing\n• No Watermark\n• Premium Assets",                                                         "prices": {"1 Month": 39,  "3 Months": 99,  "6 Months": 169, "1 Year": 299},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "lightroom":      {"display_name": "Lightroom Premium",        "keywords": ["lightroom","adobe lightroom"],                 "description": "📷 Professional Photo Editing\n• Premium Filters\n• Cloud Backup",                                               "prices": {"1 Month": 49,  "3 Months": 119, "6 Months": 199, "1 Year": 349},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "adobeexpress":   {"display_name": "Adobe Express Premium",    "keywords": ["adobe express","spark"],                       "description": "🎨 Premium Templates\n• AI Design Features\n• Brand Kit Access",                                                "prices": {"1 Month": 59,  "3 Months": 149, "6 Months": 249, "1 Year": 399},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "grammarly":      {"display_name": "Grammarly Premium",        "keywords": ["grammarly","grammerly"],                       "description": "📝 Grammar Correction\n• AI Writing Help\n• Plagiarism Check",                                                "prices": {"1 Month": 59,  "3 Months": 139, "6 Months": 249, "1 Year": 399},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "duolingo":       {"display_name": "Duolingo Super",           "keywords": ["duolingo","duolingo super"],                   "description": "📚 Ad-Free Learning\n• Unlimited Hearts\n• Offline Lessons",                                                  "prices": {"1 Month": 69,  "3 Months": 149, "6 Months": 249, "1 Year": 399},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "tradingview":    {"display_name": "TradingView Premium",      "keywords": ["tradingview","trading view"],                  "description": "📈 Advanced Trading Charts\n• Multiple Indicators\n• Real-Time Market Data",                                     "prices": {"1 Month": 149, "3 Months": 399, "6 Months": 699, "1 Year": 1299}, "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "microsoft365":   {"display_name": "Microsoft 365",            "keywords": ["microsoft","office 365","microsoft 365"],      "description": "☁️ Word, Excel & PowerPoint\n• 1TB OneDrive Storage\n• Premium Office Apps",                                    "prices": {"1 Month": 79,  "3 Months": 199, "6 Months": 349, "1 Year": 599},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "googleone":      {"display_name": "Google One Premium",       "keywords": ["google one","google drive premium"],           "description": "💾 Extra Google Storage\n• Backup Photos & Files\n• VPN Benefits",                                            "prices": {"1 Month": 39,  "3 Months": 99,  "6 Months": 169, "1 Year": 299},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "dropbox":        {"display_name": "Dropbox Premium",          "keywords": ["dropbox","dropbox premium"],                   "description": "📂 Large Cloud Storage\n• File Backup\n• Fast File Sharing",                                                "prices": {"1 Month": 69,  "3 Months": 169, "6 Months": 299, "1 Year": 549},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "googleworkspace":{"display_name": "Google Workspace",         "keywords": ["google workspace","gsuite"],                   "description": "📧 Professional Gmail\n• Business Tools\n• Cloud Collaboration",                                             "prices": {"1 Month": 99,  "3 Months": 249, "6 Months": 449, "1 Year": 799},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "telegrampremium":{"display_name": "Telegram Premium",         "keywords": ["telegram premium","tg premium"],               "description": "📲 Faster Downloads\n• Large Upload Limit\n• Premium Emojis\n• No Ads",                                        "prices": {"1 Month": 39,  "3 Months": 99,  "6 Months": 179, "1 Year": 299},  "stock": {"1 Month": 100, "3 Months": 50, "6 Months": 30, "1 Year": 20}},
    "discord":        {"display_name": "Discord Nitro",            "keywords": ["discord","nitro","discord nitro"],             "description": "💬 HD Streaming\n• Custom Emojis\n• Bigger Upload Size",                                                     "prices": {"1 Month": 79,  "3 Months": 199, "6 Months": 349, "1 Year": 649},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "xbox":           {"display_name": "Xbox Game Pass",           "keywords": ["xbox","game pass","xbox game pass"],           "description": "🎮 Hundreds of Games\n• Online Multiplayer\n• Cloud Gaming",                                               "prices": {"1 Month": 99,  "3 Months": 249, "6 Months": 449, "1 Year": 799},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "playstation":    {"display_name": "PlayStation Plus",         "keywords": ["playstation","ps plus","ps+"],                 "description": "🎮 Online Multiplayer\n• Free Monthly Games\n• Cloud Saves",                                               "prices": {"1 Month": 119, "3 Months": 299, "6 Months": 549, "1 Year": 999},  "stock": {"1 Month": 50,  "3 Months": 30, "6 Months": 20, "1 Year": 10}},
    "steam":          {"display_name": "Steam Wallet Codes",       "keywords": ["steam","steam wallet"],                        "description": "🕹️ Buy Games Easily\n• In-Game Purchases\n• DLC & Premium Access",                                          "prices": {"100 Code": 89, "250 Code": 219, "500 Code": 439, "1000 Code": 879}, "stock": {"100 Code": 50, "250 Code": 30, "500 Code": 20, "1000 Code": 10}},

    # ── NEW SERVICES ───────────────────────────────────────────────────────────────────
    "hindtv": {
        "display_name": "HIND DEALS TV",
        "keywords": ["mini app","miniapp","hind tv","hindtv","hind deals tv","fifa","movie","movies","live","streaming app","tv app"],
        "description": (
            "📺 <b>HIND DEALS TV — Premium Mini App</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎬 Watch Live Sports, Movies & Shows\n"
            "⚽ FIFA Live Matches\n"
            "📱 Works on all devices\n"
            "🔒 Ad-free, buffer-free experience\n"
            "👤 Access linked to your account\n\n"
            "✅ Instant activation after payment"
        ),
        "prices": {"Silver 🥈 1 Month": 59, "Gold 🥇 3 Months": 150, "Platinum 💎 6 Months": 199, "Diamond 💠 1 Year": 299},
        "stock":  {"Silver 🥈 1 Month": 999, "Gold 🥇 3 Months": 999, "Platinum 💎 6 Months": 999, "Diamond 💠 1 Year": 999},
    },
    "pwcourses": {
        "display_name": "Physics Wallah (PW) Courses",
        "keywords": ["pw","physics wallah","pw courses","physics","wallah","pw batch","pw pass"],
        "description": (
            "📚 <b>Physics Wallah — PW Courses</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎓 Top-Ranked JEE/NEET Courses\n"
            "📖 Full Batch Access\n"
            "🎥 HD Video Lectures\n"
            "📝 Notes & DPP Included\n"
            "🏆 Study from India's Best Teachers"
        ),
        "prices": {"1 Month": 99, "3 Months": 249, "6 Months": 449, "1 Year": 799},
        "stock":  {"1 Month": 50, "3 Months": 30,  "6 Months": 20,  "1 Year": 10},
    },
    "coupons": {
        "display_name": "Premium Offer Coupons",
        "keywords": ["coupon","coupons","swiggy","zomato","flipkart","amazon","meesho","myntra","pizza hut","offer","discount","deals coupon"],
        "description": (
            "🎟️ <b>Premium Offer Coupons</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🍔 Swiggy & Zomato Coupons\n"
            "🛍️ Flipkart & Amazon Deals\n"
            "👗 Meesho & Myntra Offers\n"
            "🍕 Pizza Hut Special Codes\n"
            "💸 Save Big on Every Order!"
        ),
        "prices": {"Swiggy/Zomato": 29, "Flipkart/Amazon": 39, "Meesho/Myntra": 29, "All Platforms Bundle": 99},
        "stock":  {"Swiggy/Zomato": 100, "Flipkart/Amazon": 100, "Meesho/Myntra": 100, "All Platforms Bundle": 50},
    },
    "virtualnumber": {
        "display_name": "Virtual Number",
        "keywords": ["virtual number","virtual","vn","temp number","otp number","virtual sim","number","whatsapp","whatsapp account","telegram account","wa account","tg account"],
        "description": (
            "📞 <b>Virtual Number Service</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🌍 Numbers from Multiple Countries\n"
            "📲 Receive OTP Instantly\n"
            "💬 WhatsApp & Telegram Account Setup\n"
            "✅ For Testing / App Registration\n"
            "🔒 Private & Secure\n"
            "⚡ Instant Delivery"
        ),
        "prices": {"1 Number (India)": 19, "1 Number (US/UK)": 39, "5 Numbers Bundle": 89, "10 Numbers Bundle": 149},
        "stock":  {"1 Number (India)": 200, "1 Number (US/UK)": 100, "5 Numbers Bundle": 50, "10 Numbers Bundle": 30},
    },
}

# In-memory cache loaded from DB at startup and after admin changes
PRODUCTS: dict = {}

# ══════════════════════════════════════════════════
#  STATES
# ══════════════════════════════════════════════════
class OrderState(StatesGroup):
    waiting_for_screenshot = State()
    waiting_for_review     = State()

class AdminState(StatesGroup):
    waiting_for_user_id      = State()
    waiting_for_broadcast    = State()
    waiting_for_stock_update = State()
    waiting_for_ban_reason   = State()

class ServiceAddState(StatesGroup):
    name        = State()
    description = State()
    keywords    = State()
    durations   = State()
    prices      = State()
    stocks      = State()

class ServiceEditState(StatesGroup):
    choose_field = State()
    new_value    = State()

class AdminManageState(StatesGroup):
    waiting_add_id   = State()
    waiting_add_role = State()
    waiting_remove   = State()

class EditSettingState(StatesGroup):
    waiting_value = State()   # admin is typing new value for a setting key

class GatewayState(StatesGroup):
    waiting_amount = State()
    waiting_token  = State()
    waiting_base   = State()
    waiting_min    = State()

class QRState(StatesGroup):
    waiting_amount = State()   # user ne "qr" / "/qr" likha, amount poocha ja raha hai

class DepositState(StatesGroup):
    waiting_for_screenshot = State()

class WalletAdminState(StatesGroup):
    waiting_add    = State()   # admin gives balance
    waiting_deduct = State()   # admin takes balance
    waiting_check  = State()   # admin checks a user's balance

class BroadcastState(StatesGroup):
    waiting_content = State()
    waiting_confirm = State()

# ══════════════════════════════════════════════════
#  DATABASE — INIT & HELPERS
# ══════════════════════════════════════════════════
def db():
    """Return a fresh SQLite connection."""
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = db()
    c = conn.cursor()

    # ── Users ──────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id          INTEGER PRIMARY KEY,
        username         TEXT    DEFAULT '',
        first_name       TEXT    DEFAULT '',
        join_date        TEXT,
        last_active      TEXT,
        is_banned        INTEGER DEFAULT 0,
        ban_reason       TEXT    DEFAULT '',
        total_orders     INTEGER DEFAULT 0,
        total_spent      INTEGER DEFAULT 0,
        wallet_balance   REAL    DEFAULT 0,
        referral_code    TEXT    UNIQUE,
        referred_by      INTEGER DEFAULT NULL,
        referral_count   INTEGER DEFAULT 0,
        wallet_unlocked  INTEGER DEFAULT 1
    )""")

    # ── Orders ─────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        order_id       TEXT    PRIMARY KEY,
        user_id        INTEGER,
        product_name   TEXT,
        duration       TEXT,
        amount         INTEGER,
        wallet_used    REAL    DEFAULT 0,
        status         TEXT,
        order_date     TEXT,
        delivery_date  TEXT    DEFAULT '',
        rating         INTEGER DEFAULT 0,
        review         TEXT    DEFAULT ''
    )""")

    # ── Admins ─────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS admins (
        user_id    INTEGER PRIMARY KEY,
        role       TEXT    DEFAULT 'admin',
        added_by   INTEGER,
        added_date TEXT
    )""")

    # ── Services ───────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS services (
        service_key   TEXT PRIMARY KEY,
        display_name  TEXT,
        description   TEXT,
        keywords      TEXT,
        is_active     INTEGER DEFAULT 1
    )""")

    # ── Service prices + stock ──────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS service_prices (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        service_key TEXT,
        duration    TEXT,
        price       INTEGER,
        stock       INTEGER DEFAULT 0
    )""")

    # ── Wallet logs ────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS wallet_logs (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id  INTEGER,
        amount   REAL,
        type     TEXT,
        reason   TEXT,
        date     TEXT
    )""")

    # ── Referrals ──────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS referrals (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        date        TEXT,
        rewarded    INTEGER DEFAULT 0
    )""")

    # ── Bot Settings (admin-editable messages & config) ─
    c.execute("""CREATE TABLE IF NOT EXISTS bot_settings (
        key        TEXT PRIMARY KEY,
        value      TEXT,
        updated_at TEXT
    )""")

    # ── Mini App Subscriptions ──────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS mini_app_subscriptions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        plan        TEXT,
        order_id    TEXT,
        start_date  TEXT,
        expiry_date TEXT,
        is_active   INTEGER DEFAULT 1
    )""")

    # ── Auto-Reply Log (one-time welcome reply) ────
    c.execute("""CREATE TABLE IF NOT EXISTS auto_reply_log (
        user_id  INTEGER PRIMARY KEY,
        sent_at  TEXT
    )""")

    # ── Deposits (wallet top-up requests) ──────────
    c.execute("""CREATE TABLE IF NOT EXISTS gw_payments (
        order_id    TEXT PRIMARY KEY,
        user_id     INTEGER,
        amount      REAL,
        purpose     TEXT,
        ref_id      TEXT,
        pay_url     TEXT,
        status      TEXT,
        settled     INTEGER DEFAULT 0,
        created_at  TEXT,
        updated_at  TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS deposits (
        deposit_id  TEXT PRIMARY KEY,
        user_id     INTEGER,
        amount      INTEGER,
        status      TEXT    DEFAULT 'pending',
        created_at  TEXT,
        updated_at  TEXT    DEFAULT ''
    )""")

    # ── Migrations for older databases ─────────────
    try:
        c.execute("ALTER TABLE admins ADD COLUMN can_wallet INTEGER DEFAULT 0")
    except Exception:
        pass
    # Wallet spending is open for every user
    c.execute("UPDATE users SET wallet_unlocked=1 WHERE wallet_unlocked=0")
    # Owner + full admins get wallet permission by default
    c.execute("UPDATE admins SET can_wallet=1 WHERE role IN ('owner','admin')")

    conn.commit()
    conn.close()

    # Insert owner into admins if not present
    _ensure_owner()
    # Seed default products if DB is empty
    _seed_products()
    # Load products into memory
    reload_products()

def _ensure_owner():
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR IGNORE INTO admins (user_id, role, added_by, added_date) VALUES (?,?,?,?)",
              (OWNER_ID, "owner", OWNER_ID, now))
    conn.commit()
    conn.close()

def _seed_products():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM services")
    count = c.fetchone()[0]
    if count == 0:
        for key, data in DEFAULT_PRODUCTS.items():
            c.execute("INSERT OR IGNORE INTO services (service_key, display_name, description, keywords, is_active) VALUES (?,?,?,?,1)",
                      (key, data["display_name"], data["description"], ",".join(data["keywords"])))
            for dur, price in data["prices"].items():
                stock = data["stock"].get(dur, 0)
                c.execute("INSERT INTO service_prices (service_key, duration, price, stock) VALUES (?,?,?,?)",
                          (key, dur, price, stock))
    conn.commit()
    conn.close()

def reload_products():
    """Reload in-memory PRODUCTS dict from DB."""
    global PRODUCTS
    PRODUCTS = {}
    conn = db()
    c = conn.cursor()
    c.execute("SELECT service_key, display_name, description, keywords FROM services WHERE is_active=1")
    services = c.fetchall()
    for sk, dname, desc, kw in services:
        keywords = [k.strip().lower() for k in kw.split(",") if k.strip()]
        c.execute("SELECT duration, price, stock FROM service_prices WHERE service_key=? ORDER BY price", (sk,))
        rows = c.fetchall()
        prices = {}
        stock  = {}
        for dur, price, st in rows:
            prices[dur] = price
            stock[dur]  = st
        PRODUCTS[sk] = {
            "display_name": dname,
            "description":  desc,
            "keywords":     keywords,
            "prices":       prices,
            "stock":        stock,
        }
    conn.close()

# ──────────────────────────────────────────────────
#  Admin helpers
# ──────────────────────────────────────────────────
def get_admin_role(user_id: int) -> str | None:
    """Returns role string or None if not admin."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT role FROM admins WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def is_admin(user_id: int) -> bool:
    return get_admin_role(user_id) is not None

def is_delivery_admin(user_id: int) -> bool:
    role = get_admin_role(user_id)
    return role in ("owner", "super_admin", "admin", "delivery_admin")

def can_manage_services(user_id: int) -> bool:
    role = get_admin_role(user_id)
    return role in ("owner", "super_admin", "admin")

def can_manage_wallet(user_id: int) -> bool:
    """Owner always; other admins only if given wallet permission."""
    if user_id == OWNER_ID:
        return True
    conn = db()
    c = conn.cursor()
    c.execute("SELECT role, COALESCE(can_wallet,0) FROM admins WHERE user_id=?", (user_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return False
    return r[0] == "owner" or r[1] == 1

def set_wallet_perm(user_id: int, allowed: bool):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE admins SET can_wallet=? WHERE user_id=?", (1 if allowed else 0, user_id))
    conn.commit()
    conn.close()

def get_admins_with_perm():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT user_id, role, COALESCE(can_wallet,0) FROM admins ORDER BY added_date")
    r = c.fetchall()
    conn.close()
    return r

def get_all_admins():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT user_id, role, added_date FROM admins ORDER BY added_date")
    rows = c.fetchall()
    conn.close()
    return rows

# ──────────────────────────────────────────────────
#  Bot Settings helpers  (admin-editable messages)
# ──────────────────────────────────────────────────
# Keys used in bot_settings table:
#   welcome_msg         – /start welcome text
#   payment_pending_msg – message sent after screenshot
#   offline_msg         – one-time auto-reply to new users
#   mini_app_url        – Telegram Mini App URL (WebApp)
#   mini_app_desc       – HIND DEALS TV description override
#   review_link         – community / reviews channel link

DEFAULT_SETTINGS = {
    "welcome_msg": "",    # Empty = use hardcoded WELCOME_MSG; set from admin panel to override
    "payment_pending_msg": (
        "⏳ <b>Shukriya aapke payment ka!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📸 Screenshot successfully received.\n"
        "🔍 Admin abhi verify kar raha hai.\n\n"
        "⏱️ <b>Estimated wait: 5–15 minutes</b>\n\n"
        "📩 Support ke liye: @HIND_DEALS\n"
        "📢 Reviews: https://t.me/HIND_DEALS_REVIEWS\n\n"
        "🙏 <i>Thank you for your patience!</i>"
    ),
    "offline_msg": (
        "👋 <b>Thank you very much for messaging HIND DEALS!</b>\n\n"
        "😊 Aapka message mil gaya hai.\n"
        "⚠️ Owner abhi offline hai.\n\n"
        "⏱️ Thoda wait kariye — owner aapko soon reply karega.\n\n"
        "📢 Community: https://t.me/HIND_DEALS_REVIEWS\n"
        "💬 Support: @HIND_DEALS"
    ),
    "gw_enabled":     "0",                      # 1 = auto payment gateway ON
    "gw_base":        GATEWAY_BASE_DEFAULT,     # gateway panel base url
    "gw_token":       "",                       # merchant user_token / api key
    "gw_min":         "10",                     # min auto-deposit amount
    "mini_app_url":   "",   # Set from admin panel — Telegram WebApp link
    "review_link":    "https://t.me/HIND_DEALS_REVIEWS",
}

def get_setting(key: str, default: str = "") -> str:
    conn = db()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return DEFAULT_SETTINGS.get(key, default)

def set_setting(key: str, value: str):
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR REPLACE INTO bot_settings (key, value, updated_at) VALUES (?,?,?)",
              (key, value, now))
    conn.commit()
    conn.close()

def get_all_settings() -> dict:
    conn = db()
    c = conn.cursor()
    c.execute("SELECT key, value FROM bot_settings")
    rows = {r[0]: r[1] for r in c.fetchall()}
    conn.close()
    merged = dict(DEFAULT_SETTINGS)
    merged.update(rows)
    return merged

# ──────────────────────────────────────────────────
#  Mini App Subscription helpers
# ──────────────────────────────────────────────────
HINDTV_PLAN_DAYS = {
    "Silver 🥈 1 Month":       30,
    "Gold 🥇 3 Months":       90,
    "Platinum 💎 6 Months":  180,
    "Diamond 💠 1 Year":     365,
}

def activate_mini_app_sub(user_id: int, plan: str, order_id: str):
    """Activate (or extend) a HIND DEALS TV subscription for a user."""
    days = HINDTV_PLAN_DAYS.get(plan, 30)
    conn = db()
    c = conn.cursor()
    now = datetime.now()
    # Deactivate old subscriptions
    c.execute("UPDATE mini_app_subscriptions SET is_active=0 WHERE user_id=?", (user_id,))
    from datetime import timedelta
    expiry = (now + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""INSERT INTO mini_app_subscriptions
                 (user_id, plan, order_id, start_date, expiry_date, is_active)
                 VALUES (?,?,?,?,?,1)""",
              (user_id, plan, order_id, now.strftime("%Y-%m-%d %H:%M:%S"), expiry))
    conn.commit()
    conn.close()

def get_mini_app_sub(user_id: int):
    """Returns (plan, expiry_date) if active, else None."""
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""SELECT plan, expiry_date FROM mini_app_subscriptions
                 WHERE user_id=? AND is_active=1 AND expiry_date > ?
                 ORDER BY expiry_date DESC LIMIT 1""", (user_id, now))
    row = c.fetchone()
    conn.close()
    return row  # (plan, expiry_date) or None

def get_all_active_subs(limit=50):
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""SELECT m.user_id, u.username, m.plan, m.expiry_date
                 FROM mini_app_subscriptions m
                 LEFT JOIN users u ON u.user_id = m.user_id
                 WHERE m.is_active=1 AND m.expiry_date > ?
                 ORDER BY m.expiry_date DESC LIMIT ?""", (now, limit))
    rows = c.fetchall()
    conn.close()
    return rows

# ──────────────────────────────────────────────────
#  Deposit helpers  (wallet top-up)
# ──────────────────────────────────────────────────
def generate_deposit_id(user_id: int) -> str:
    return f"DEP{user_id}{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

def save_deposit(deposit_id: str, user_id: int, amount: int):
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO deposits (deposit_id, user_id, amount, status, created_at) VALUES (?,?,?,?,?)",
              (deposit_id, user_id, amount, "pending", now))
    conn.commit()
    conn.close()

def get_deposit(deposit_id: str):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM deposits WHERE deposit_id=?", (deposit_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_deposit_status(deposit_id: str, status: str):
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE deposits SET status=?, updated_at=? WHERE deposit_id=?", (status, now, deposit_id))
    conn.commit()
    conn.close()

# ──────────────────────────────────────────────────
#  Auto-reply helpers  (one-time offline message)
# ──────────────────────────────────────────────────
def has_auto_replied(user_id: int) -> bool:
    conn = db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM auto_reply_log WHERE user_id=?", (user_id,))
    r = c.fetchone()
    conn.close()
    return r is not None

def mark_auto_replied(user_id: int):
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR IGNORE INTO auto_reply_log (user_id, sent_at) VALUES (?,?)", (user_id, now))
    conn.commit()
    conn.close()

# ──────────────────────────────────────────────────
#  User helpers
# ──────────────────────────────────────────────────
def _gen_ref_code(user_id: int) -> str:
    return f"ref{user_id}"

def update_user(user_id: int, username: str, name: str):
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ref_code = _gen_ref_code(user_id)
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if c.fetchone():
        c.execute("UPDATE users SET username=?, first_name=?, last_active=? WHERE user_id=?",
                  (username or "", name or "", now, user_id))
    else:
        c.execute("""INSERT INTO users
            (user_id, username, first_name, join_date, last_active, referral_code)
            VALUES (?,?,?,?,?,?)""",
            (user_id, username or "", name or "", now, now, ref_code))
    conn.commit()
    conn.close()

def is_user_banned(user_id: int) -> bool:
    conn = db()
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    conn.close()
    return bool(r and r[0] == 1)

def get_ban_reason(user_id: int) -> str:
    conn = db()
    c = conn.cursor()
    c.execute("SELECT ban_reason FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else ""

def ban_user(uid: int, reason: str):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=1, ban_reason=? WHERE user_id=?", (reason, uid))
    conn.commit()
    conn.close()

def unban_user(uid: int):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=0, ban_reason='' WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()

def get_user_full(uid: int):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    u = c.fetchone()
    c.execute("""SELECT order_id, product_name, duration, amount, status
                 FROM orders WHERE user_id=? ORDER BY order_date DESC LIMIT 10""", (uid,))
    o = c.fetchall()
    conn.close()
    return u, o


# ══════════════════════════════════════════════════
#  PAYMENT GATEWAY (auto UPI — iPey.shop style panel)
# ══════════════════════════════════════════════════
def gw_enabled() -> bool:
    if not AUTO_APPROVAL:
        return False   # auto approval band hai
    return get_setting("gw_enabled", "0") == "1" and bool(get_setting("gw_token", "").strip())

def gw_base() -> str:
    return (get_setting("gw_base", GATEWAY_BASE_DEFAULT) or GATEWAY_BASE_DEFAULT).rstrip("/")

def gw_token() -> str:
    return get_setting("gw_token", "").strip()

def gw_min() -> int:
    try:
        return max(1, int(float(get_setting("gw_min", "10"))))
    except Exception:
        return 10

def gw_new_id(user_id: int) -> str:
    return f"GW{user_id}{int(datetime.now().timestamp())}{random.randint(10, 99)}"

def gw_save(order_id: str, user_id: int, amount: float, purpose: str, ref_id: str, pay_url: str):
    conn = db(); c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""INSERT OR REPLACE INTO gw_payments
                 (order_id,user_id,amount,purpose,ref_id,pay_url,status,settled,created_at,updated_at)
                 VALUES (?,?,?,?,?,?,?,0,?,?)""",
              (order_id, user_id, amount, purpose, ref_id, pay_url, "pending", now, now))
    conn.commit(); conn.close()

def gw_get(order_id: str):
    conn = db(); c = conn.cursor()
    c.execute("SELECT order_id,user_id,amount,purpose,ref_id,pay_url,status,settled FROM gw_payments WHERE order_id=?",
              (order_id,))
    r = c.fetchone(); conn.close()
    return r

def gw_set_status(order_id: str, status: str, settled: int | None = None):
    conn = db(); c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if settled is None:
        c.execute("UPDATE gw_payments SET status=?, updated_at=? WHERE order_id=?", (status, now, order_id))
    else:
        c.execute("UPDATE gw_payments SET status=?, settled=?, updated_at=? WHERE order_id=?",
                  (status, settled, now, order_id))
    conn.commit(); conn.close()

def gw_pending_rows():
    conn = db(); c = conn.cursor()
    c.execute("""SELECT order_id,user_id,amount,purpose,ref_id,pay_url,status,settled,created_at
                 FROM gw_payments WHERE status='pending' AND settled=0 ORDER BY created_at DESC LIMIT 100""")
    rows = c.fetchall(); conn.close()
    return rows

def gw_stats():
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM gw_payments WHERE status='success'")
    ok = c.fetchone()
    c.execute("SELECT COUNT(*) FROM gw_payments WHERE status='pending'")
    pend = c.fetchone()[0]
    conn.close()
    return ok[0], ok[1], pend

async def _gw_post(path: str, payload: dict) -> dict:
    """POST form-data to the gateway panel. Never raises — returns dict."""
    import aiohttp
    url = f"{gw_base()}{path}"
    form = aiohttp.FormData()
    for k, v in payload.items():
        form.add_field(k, str(v))
    try:
        timeout = aiohttp.ClientTimeout(total=GATEWAY_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.post(url, data=form) as resp:
                raw = await resp.text()
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = None
                if not isinstance(data, dict):
                    detail = raw.strip()[:180] or "blank response (token galat ya account inactive)"
                    return {"status": False, "message": f"HTTP {resp.status}: {detail}"}
                return data
    except Exception as e:
        return {"status": False, "message": f"Network error: {e}"}

def _truthy(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "success", "yes", "ok")

async def gw_create_order(amount: float, order_id: str, mobile: str = "9999999999", remark: str = "wallet"):
    """Creates a payment order. Returns (ok, payment_url, message)."""
    if not gw_enabled():
        return False, "", "Gateway band hai (admin ne token set nahi kiya)."
    data = await _gw_post("/api/create-order", {
        "customer_mobile": mobile,
        "user_token":      gw_token(),
        "amount":          int(amount),
        "order_id":        order_id,
        "redirect_url":    get_setting("review_link", "https://t.me/HIND_DEALS"),
        "remark1":         remark,
        "remark2":         "hind-deals-bot",
    })
    if _truthy(data.get("status")):
        d = data.get("result") or data.get("data") or {}
        url = ""
        if isinstance(d, dict):
            url = d.get("payment_url") or d.get("paymentUrl") or d.get("url") or ""
        url = url or data.get("payment_url") or ""
        if url:
            return True, url, "ok"
        return False, "", "Gateway ne payment link nahi diya."
    return False, "", str(data.get("message") or data.get("msg") or "Gateway error")

async def gw_check_status(order_id: str):
    """Returns (state, message) where state in success|pending|failed."""
    if not gw_enabled():
        return "pending", "Gateway band hai."
    data = await _gw_post("/api/check-order-status", {
        "user_token": gw_token(),
        "order_id":   order_id,
    })
    if not _truthy(data.get("status")):
        return "pending", str(data.get("message") or "Abhi payment nahi mila.")
    res = data.get("result") or data.get("data") or {}
    if isinstance(res, dict):
        txn = str(res.get("txnStatus") or res.get("status") or res.get("payment_status") or "").upper()
    else:
        txn = str(res).upper()
    if txn in ("SUCCESS", "COMPLETED", "PAID", "TRUE"):
        return "success", "paid"
    if txn in ("FAILED", "FAILURE", "CANCELLED", "EXPIRED"):
        return "failed", txn
    return "pending", txn or "PENDING"

async def gw_settle(order_id: str) -> bool:
    """Credits wallet / approves order exactly once. Returns True if settled now."""
    if not AUTO_APPROVAL:
        return False   # auto approval band — admin manually approve karega
    row = gw_get(order_id)
    if not row:
        return False
    oid, uid, amount, purpose, ref_id, pay_url, status, settled = row
    if settled:
        return False
    gw_set_status(oid, "success", 1)
    amount = float(amount)

    if purpose.startswith("order:"):
        shop_oid = purpose.split(":", 1)[1]
        credit_wallet(uid, amount, f"Online payment {oid}")
        debit_wallet(uid, amount, f"Purchase {shop_oid} (online)")
        try:
            update_order_status(shop_oid, "approved")
            add_order_spent(uid, amount)
        except Exception:
            pass
        conn = db(); c = conn.cursor()
        c.execute("SELECT product_key, duration FROM orders WHERE order_id=?", (shop_oid,))
        r = c.fetchone()
        c.execute("SELECT user_id FROM admins")
        admins_list = [x[0] for x in c.fetchall()]
        conn.close()
        pkey, dur = (r[0], r[1]) if r else ("", "")
        try:
            decrement_stock(pkey, dur)
        except Exception:
            pass
        pname = PRODUCTS.get(pkey, {}).get("display_name", pkey)
        for adm in admins_list:
            try:
                await bot.send_message(
                    adm,
                    f"⚡ <b>ONLINE PAYMENT RECEIVED — DELIVERY REQUIRED</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Order: <code>{shop_oid}</code>\n"
                    f"User: <code>{uid}</code>\n"
                    f"Product: {pname}\nDuration: {dur}\n"
                    f"Amount: ₹{amount:.0f} (auto verified ✅)\n\n"
                    f"No screenshot needed — payment gateway confirmed.",
                    parse_mode="HTML",
                    reply_markup=deliver_kb(shop_oid, uid, int(amount))
                )
            except Exception:
                pass
        try:
            await bot.send_message(
                uid,
                f"✅ <b>Payment Successful!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Order ID: <code>{shop_oid}</code>\n"
                f"Amount: ₹{amount:.0f}\n\n"
                f"Admin thodi der me deliver karega. Dhanyavaad! 🙏",
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        credit_wallet(uid, amount, f"Auto deposit {oid}")
        bal, _ = get_wallet(uid)
        try:
            await bot.send_message(
                uid,
                f"✅ <b>Wallet Recharge Successful!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"➕ Added: <b>₹{amount:.0f}</b>\n"
                f"💰 New Balance: <b>₹{bal:.2f}</b>\n\n"
                f"Ab aap wallet se direct buy kar sakte hain 🛒",
                parse_mode="HTML"
            )
        except Exception:
            pass
    return True

async def gw_poller():
    """Background auto-verifier — credits wallet without user pressing anything."""
    await asyncio.sleep(10)
    while True:
        try:
            if gw_enabled():
                for row in gw_pending_rows():
                    oid, uid, amount, purpose, ref_id, pay_url, status, settled, created = row
                    try:
                        age = (datetime.now() - datetime.strptime(created, "%Y-%m-%d %H:%M:%S")).total_seconds()
                    except Exception:
                        age = 0
                    if age > GATEWAY_EXPIRY_MIN * 60:
                        gw_set_status(oid, "expired")
                        continue
                    state, _msg = await gw_check_status(oid)
                    if state == "success":
                        await gw_settle(oid)
                    elif state == "failed":
                        gw_set_status(oid, "failed")
                    await asyncio.sleep(0.4)
        except Exception as e:
            logging.warning(f"gw_poller: {e}")
        await asyncio.sleep(GATEWAY_POLL_SECONDS)

def gw_pay_kb(order_id: str, pay_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💳 PAY NOW (UPI)", url=pay_url)
    b.button(text="🔄 CHECK PAYMENT", callback_data=f"gwchk_{order_id}")
    b.button(text="❌ CANCEL", callback_data=f"gwcan_{order_id}")
    b.adjust(1)
    return b.as_markup()

def gw_admin_kb() -> InlineKeyboardMarkup:
    on = gw_enabled()
    b = InlineKeyboardBuilder()
    b.button(text=("🔴 TURN OFF" if on else "🟢 TURN ON"), callback_data="gwadm_toggle")
    b.button(text="🔑 SET API TOKEN",  callback_data="gwadm_token")
    b.button(text="🌐 SET PANEL URL",  callback_data="gwadm_base")
    b.button(text="💵 SET MIN AMOUNT", callback_data="gwadm_min")
    b.button(text="🧪 TEST GATEWAY",   callback_data="gwadm_test")
    b.button(text="📋 PENDING PAYMENTS", callback_data="gwadm_pending")
    b.button(text="🔙 BACK", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()

# ──────────────────────────────────────────────────
#  Wallet helpers
# ──────────────────────────────────────────────────
def get_wallet(user_id: int) -> tuple[float, int]:
    """Returns (balance, wallet_unlocked)."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT wallet_balance, wallet_unlocked FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    conn.close()
    return (r[0] if r else 0, r[1] if r else 0)

def credit_wallet(user_id: int, amount: float, reason: str):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE users SET wallet_balance = wallet_balance + ? WHERE user_id=?", (amount, user_id))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO wallet_logs (user_id, amount, type, reason, date) VALUES (?,?,?,?,?)",
              (user_id, amount, "credit", reason, now))
    conn.commit()
    conn.close()

def debit_wallet(user_id: int, amount: float, reason: str) -> bool:
    """Returns True if debit successful."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT wallet_balance FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    if not r or r[0] < amount:
        conn.close()
        return False
    c.execute("UPDATE users SET wallet_balance = wallet_balance - ? WHERE user_id=?", (amount, user_id))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO wallet_logs (user_id, amount, type, reason, date) VALUES (?,?,?,?,?)",
              (user_id, amount, "debit", reason, now))
    conn.commit()
    conn.close()
    return True

def get_wallet_history(user_id: int, limit: int = 10):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT amount, type, reason, date FROM wallet_logs WHERE user_id=? ORDER BY date DESC LIMIT ?",
              (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def _check_wallet_unlock(user_id: int):
    """Unlock wallet if user has reached referral threshold."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT referral_count, wallet_unlocked FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    if r and r[0] >= REFERRAL_UNLOCK_COUNT and r[1] == 0:
        c.execute("UPDATE users SET wallet_unlocked=1 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        return True   # just unlocked
    conn.close()
    return False

# ──────────────────────────────────────────────────
#  Referral helpers
# ──────────────────────────────────────────────────
def get_referral_info(user_id: int):
    """Returns (referral_code, referral_count, wallet_unlocked)."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT referral_code, referral_count, wallet_unlocked FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    conn.close()
    return r if r else (_gen_ref_code(user_id), 0, 0)

def get_referred_by(user_id: int) -> int | None:
    conn = db()
    c = conn.cursor()
    c.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

def set_referred_by(user_id: int, referrer_id: int):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE users SET referred_by=? WHERE user_id=? AND referred_by IS NULL", (referrer_id, user_id))
    conn.commit()
    conn.close()

def record_referral(referrer_id: int, referred_id: int) -> bool:
    """Returns True if this is a new valid referral (not already recorded)."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id FROM referrals WHERE referred_id=?", (referred_id,))
    if c.fetchone():
        conn.close()
        return False   # already referred
    if referrer_id == referred_id:
        conn.close()
        return False   # self-referral
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO referrals (referrer_id, referred_id, date) VALUES (?,?,?)",
              (referrer_id, referred_id, now))
    conn.commit()
    conn.close()
    return True

def complete_referral_reward(referrer_id: int, referred_id: int):
    """Credits rewards and marks referral as rewarded. Call after channel join confirmed."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id, rewarded FROM referrals WHERE referrer_id=? AND referred_id=?",
              (referrer_id, referred_id))
    row = c.fetchone()
    if not row or row[1] == 1:
        conn.close()
        return
    c.execute("UPDATE referrals SET rewarded=1 WHERE id=?", (row[0],))
    # Increment referrer count
    c.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?", (referrer_id,))
    conn.commit()
    conn.close()
    # Credit wallet rewards
    credit_wallet(referrer_id, REFERRAL_REWARD, f"Referral reward — user {referred_id} joined")
    credit_wallet(referred_id, WELCOME_BONUS,   "Welcome bonus for joining via referral")
    # Check if referrer unlocked wallet
    _check_wallet_unlock(referrer_id)

def get_top_referrers(limit: int = 10):
    conn = db()
    c = conn.cursor()
    c.execute("""SELECT u.user_id, u.username, u.referral_count
                 FROM users u ORDER BY u.referral_count DESC LIMIT ?""", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ──────────────────────────────────────────────────
#  Order helpers
# ──────────────────────────────────────────────────
def generate_order_id(user_id: int) -> str:
    return f"HD{user_id}{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

def save_order(order_id, user_id, product, duration, amount, wallet_used=0):
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""INSERT INTO orders
        (order_id, user_id, product_name, duration, amount, wallet_used, status, order_date)
        VALUES (?,?,?,?,?,?,?,?)""",
        (order_id, user_id, product, duration, amount, wallet_used, "pending", now))
    conn.commit()
    conn.close()

def update_order_status(order_id, status):
    conn = db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE orders SET status=?, delivery_date=? WHERE order_id=?", (status, now, order_id))
    conn.commit()
    conn.close()

def update_rating(order_id, rating, review):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE orders SET rating=?, review=? WHERE order_id=?", (rating, review, order_id))
    conn.commit()
    conn.close()

def get_order(order_id):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))
    r = c.fetchone()
    conn.close()
    return r

def get_user_orders(user_id):
    conn = db()
    c = conn.cursor()
    c.execute("""SELECT order_id, product_name, duration, amount, status
                 FROM orders WHERE user_id=? ORDER BY order_date DESC""", (user_id,))
    r = c.fetchall()
    conn.close()
    return r

def get_pending():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT order_id, user_id, product_name, duration, amount FROM orders WHERE status='pending'")
    r = c.fetchall()
    conn.close()
    return r

def add_order_spent(user_id, amount):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE users SET total_orders=total_orders+1, total_spent=total_spent+? WHERE user_id=?",
              (amount, user_id))
    conn.commit()
    conn.close()

# ──────────────────────────────────────────────────
#  Analytics helpers
# ──────────────────────────────────────────────────
def get_stats():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='delivered'")
    delivered = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='delivered'")
    revenue = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM referrals WHERE rewarded=1")
    referrals = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(wallet_used),0) FROM orders")
    wallet_used = c.fetchone()[0]
    conn.close()
    return users, total, pending, delivered, revenue, referrals, wallet_used

def get_top_services(limit=5):
    conn = db()
    c = conn.cursor()
    c.execute("""SELECT product_name, COUNT(*), COALESCE(SUM(amount),0)
                 FROM orders WHERE status='delivered'
                 GROUP BY product_name ORDER BY COUNT(*) DESC LIMIT ?""", (limit,))
    r = c.fetchall()
    conn.close()
    return r

def get_daily_sales():
    conn = db()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM orders WHERE status='delivered' AND order_date LIKE ?",
              (f"{today}%",))
    r = c.fetchone()
    conn.close()
    return r

# ──────────────────────────────────────────────────
#  Stock helper (DB-backed)
# ──────────────────────────────────────────────────
def update_stock_db(service_key, duration, new_stock):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE service_prices SET stock=? WHERE service_key=? AND duration=?",
              (new_stock, service_key, duration))
    conn.commit()
    conn.close()
    reload_products()

def decrement_stock(service_key, duration):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE service_prices SET stock = MAX(0, stock-1) WHERE service_key=? AND duration=?",
              (service_key, duration))
    conn.commit()
    conn.close()
    reload_products()

# ──────────────────────────────────────────────────
#  QR helper
# ──────────────────────────────────────────────────
def _upi_link(amount) -> str:
    from urllib.parse import quote
    try:
        amt = float(amount)
    except Exception:
        amt = 0.0
    pa = quote(str(UPI_ID).strip(), safe="@.-_")
    return (f"upi://pay?pa={pa}&pn={quote('HIND DEALS')}"
            f"&am={amt:.2f}&cu=INR&tn={quote('HIND DEALS Payment')}")

_QR_PNG_CACHE: dict = {}      # amount -> (png_bytes, expires_ts)
_ACTIVE_QR: dict = {}         # user_id -> {amount, dep_id, expires}

def _now_ts() -> float:
    return datetime.now().timestamp()

def active_qr(user_id: int, amount=None):
    """Return the user's still-valid QR record, else None."""
    rec = _ACTIVE_QR.get(user_id)
    if not rec:
        return None
    if _now_ts() >= rec["expires"]:
        _ACTIVE_QR.pop(user_id, None)
        return None
    if amount is not None and int(rec["amount"]) != int(amount):
        return None
    return rec

def remember_qr(user_id: int, amount: int, dep_id: str) -> dict:
    rec = {"amount": int(amount), "dep_id": dep_id,
           "expires": _now_ts() + QR_VALID_MIN * 60}
    _ACTIVE_QR[user_id] = rec
    return rec

def qr_valid_line(rec: dict) -> str:
    left = max(0, int((rec["expires"] - _now_ts()) // 60) + 1)
    till = datetime.fromtimestamp(rec["expires"]).strftime("%I:%M %p")
    return f"⏳ Ye QR <b>{left} min</b> tak valid hai (till {till}) — dobara generate karne ki zaroorat nahi."

def generate_qr(amount):
    """Return PNG bytes of the UPI QR (cached for QR_VALID_MIN minutes)."""
    key = f"{float(amount):.2f}"
    hit = _QR_PNG_CACHE.get(key)
    if hit and _now_ts() < hit[1]:
        return hit[0]
    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10, border=4
        )
        qr.add_data(_upi_link(amount))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        try:
            img = img.convert("RGB")
        except Exception:
            pass
        bio = BytesIO()
        img.save(bio, format="PNG")
        data = bio.getvalue()
        if not data:
            return None
        _QR_PNG_CACHE[key] = (data, _now_ts() + QR_VALID_MIN * 60)
        return data
    except Exception as e:
        logging.exception("QR generation failed: %s", e)
        return None

async def send_payment_qr(target, amount, caption, reply_markup=None):
    """Send QR photo with retries; always falls back to a text payment message."""
    png = generate_qr(amount)
    if png:
        for attempt in range(3):
            try:
                return await target.answer_photo(
                    photo=types.BufferedInputFile(png, filename="qr.png"),
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.warning("QR send failed (try %s): %s", attempt + 1, e)
                await asyncio.sleep(1.5)
    # Fallback — never leave the user without payment details
    link = _upi_link(amount)
    try:
        return await target.answer(
            caption + f"\n\n⚠️ QR image load nahi hui.\n"
                      f"UPI ID par direct pay karein: <code>{UPI_ID}</code>\n"
                      f"Ya ye link apne UPI app me kholein:\n<code>{link}</code>",
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.exception("QR fallback send failed: %s", e)
        return None

# ──────────────────────────────────────────────────
#  Force-join helper
# ──────────────────────────────────────────────────
async def is_joined(user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return False

# ══════════════════════════════════════════════════
#  STATIC MESSAGES
# ══════════════════════════════════════════════════
WELCOME_MSG = """✨ <b>WELCOME TO HIND DEALS BOT</b> ✨
Your trusted destination for Premium OTT, AI Tools, Cloud Storage &amp; Digital Subscriptions at unbeatable prices 🚀

🎬 <b>OTT &amp; MOVIE STREAMING PREMIUM</b>
• 📺 JioHotstar Premium
• 🎞️ Netflix Premium
• 🍿 Amazon Prime Video
• 🎬 Sony LIV Premium
• 📡 ZEE5 Premium
• ❤️ Hoichoi Premium
• 🎥 ALTBalaji Premium
• 🌟 Discovery+ Premium
• 🎭 Lionsgate Play
• 📱 MX Player Gold
• 🎦 Chaupal Premium
• 🎶 Spotify Premium
• 🎵 YouTube Premium
• 👨‍👩‍👧 YouTube Family
• 🎧 Apple Music
• 📻 Gaana Plus
• 🎼 Wynk Music Premium

🤖 <b>AI TOOLS &amp; PRODUCTIVITY PREMIUM</b>
• 🤖 ChatGPT Plus
• 🍃 Gemini Premium + 2TB
• 🧠 Claude AI Pro
• ⚡ Blackbox AI
• 🎨 Canva Pro
• 🖌️ PicsArt Premium
• ✨ Remini Premium
• 🎬 CapCut Pro
• 🎥 KineMaster Premium
• 📷 Lightroom Premium
• 🎨 Adobe Express Premium
• 📝 Grammarly Premium
• 📚 Duolingo Super
• 📈 TradingView Premium
• ☁️ Microsoft 365
• 💾 Google One Premium
• 📂 Dropbox Premium

📱 <b>GOOGLE &amp; OTHER PREMIUM SERVICES</b>
• ☁️ Google One Storage
• ▶️ YouTube Premium
• 📧 Google Workspace
• 📲 Telegram Premium
• 💬 Discord Nitro
• 🎮 Xbox Game Pass
• 🎮 PlayStation Plus
• 🕹️ Steam Wallet Codes

🆕 <b>EXCLUSIVE SERVICES</b>
• 📺 HIND DEALS TV — Mini App (Live Sports, Movies, FIFA Live)
• 📚 Physics Wallah (PW) Courses — JEE/NEET
• 🎟️ Premium Offer Coupons — Swiggy, Zomato, Flipkart &amp; More
• 📞 Virtual Numbers — WhatsApp &amp; Telegram Accounts, India &amp; International

🔥 <b>WHY CHOOSE HIND DEALS?</b>
⚡ Instant Delivery
🔒 100% Trusted &amp; Safe
💸 Best Market Prices
🛠️ Friendly Support Anytime
✅ Genuine Premium Access
🚀 Fast Response &amp; Smooth Service

👑 <b>JOIN HIND DEALS TODAY</b> 👑
Best Premium Services at Lowest Prices 💯

📢 Reviews &amp; Community: https://t.me/HIND_DEALS_REVIEWS
💬 Support &amp; Orders: @HIND_DEALS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Use /help for more clarification"""

HELP_MSG = """❓ <b>HELP & SUPPORT GUIDE</b> ❓

📌 <b>HOW TO BUY:</b>
1️⃣ Type service name (Netflix, Spotify, ChatGPT…)
2️⃣ Select duration
3️⃣ Confirm & proceed to payment
4️⃣ Scan QR → Pay → Click "I HAVE PAID"
5️⃣ Send payment screenshot
6️⃣ Admin verifies → Service delivered ⚡

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>WALLET SYSTEM:</b>
• Earn ₹{rr} for each successful referral
• New users get ₹{wb} welcome bonus
• Wallet unlocks after {ru} referrals
• Use wallet at checkout to reduce payment

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 <b>COMMANDS:</b>
/start   → Main menu
/help    → This guide
/orders  → Your order history
/wallet  → Wallet & balance
/referral→ Referral link & stats
/contact → Contact support
/rules   → Refund & rules policy
/cancel  → Cancel current operation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Short forms work! NF=Netflix YT=YouTube GPT=ChatGPT""".format(
    rr=REFERRAL_REWARD, wb=WELCOME_BONUS, ru=REFERRAL_UNLOCK_COUNT
)

PAYMENT_CONFIRMED_MSG = """✅ <b>Dear Customer,</b>
🎉 <b>Your payment has been successfully confirmed!</b>
💎 Thank you for choosing <b>HIND DEALS</b>
⚡ Your service/order is now being processed instantly.
📩 For support & updates contact: @HIND_DEALS_BOT
🔥 Trusted Premium Services at Best Prices"""


RULES_MSG = """📜 <b>HIND DEALS — RULES & REFUND POLICY</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚖️ <b>GENERAL RULES:</b>

1️⃣ Payment karne ke baad screenshot bhejiye — bina screenshot ke order process nahi hoga.
2️⃣ Ek baar service deliver ho jane ke baad koi refund nahi milega.
3️⃣ Kisi bhi service ke liye genuine screenshots hi bhejein — fake ya edited screenshots strictly banned.
4️⃣ Support ke liye sirf @HIND_DEALS ya @HIND_DEALS_BOT se contact karein.
5️⃣ Abusive/spam behavior strictly prohibited hai — account ban ho sakta hai.
6️⃣ Ye saari services digital hain — sharing/reselling allowed nahi hai.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💸 <b>REFUND POLICY (Applicable on All Services):</b>

✅ <b>100% Full Refund:</b>
• Agar hum aapko service provide nahi kar paye (hamare side se issue ho), to aapko <b>100% pura paisa refund</b> kiya jayega — bina kisi deduction ke.

⚠️ <b>82% Partial Refund (18% Deduction):</b>
• Agar aapke phone ya device mein koi technical issue ho jiske wajah se service kaam nahi kar rahi, to <b>18% service/processing fee katke</b> baaki <b>82% refund</b> diya jayega.

❌ <b>No Refund:</b>
• Service successfully deliver ho jane ke baad.
• Galat information dene par (wrong email, wrong ID, etc.).
• Service ka misuse ya policy violation ke case mein.
• Coupon ya virtual number use ho jane ke baad.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>Refund Kaise Claim Karein?</b>
Refund ke liye @HIND_DEALS ko message karein apna Order ID ke saath.

📢 Reviews: https://t.me/HIND_DEALS_REVIEWS
💬 Support: @HIND_DEALS"""

REFUND_MSG = """💸 <b>REFUND POLICY — HIND DEALS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <b>100% Full Refund:</b>
Agar hum aapko service provide <b>nahi kar paye</b> (hamare side se koi issue), to aapko <b>pura 100% paisa wapas</b> kar diya jayega — zero deduction.

⚠️ <b>82% Partial Refund (18% deduction):</b>
Agar aapke <b>phone/device mein issue</b> hone ki wajah se service kaam nahi kar rahi, to <b>18% cut karke 82% refund</b> diya jayega.

❌ <b>Refund Nahi Milega Agar:</b>
• Service successfully deliver ho chuki ho
• Wrong details di gayi hon
• Coupon ya virtual number use ho chuka ho
• Policy violation/misuse ke case mein

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📩 Refund claim karne ke liye apna <b>Order ID</b> ke saath contact karein: @HIND_DEALS

📜 Poori policy dekhne ke liye: /rules"""

# ── Start-menu intro block (shown below service pagination) ──
START_INTRO_MSG = """🔥 <b>HIND DEALS PREMIUM SERVICES</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ Instant Delivery
💎 Trusted Premium Services
💚 Wallet &amp; Referral System

📢 Reviews:
https://t.me/HIND_DEALS_REVIEWS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Type any service name to buy • /help for guide"""

# ══════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════
def main_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🛒 BUY NOW",    callback_data="buy_now")
    b.button(text="💰 WALLET",     callback_data="wallet_view")
    b.button(text="🤝 REFERRAL",   callback_data="ref_view")
    b.button(text="📦 MY ORDERS",  callback_data="my_orders")
    b.button(text="📞 SUPPORT",    callback_data="contact")
    b.adjust(1)
    return b.as_markup()

# ══════════════════════════════════════════════════
#  BROWSE SCREEN — paginated service picker
#  (opened only when user taps BUY NOW)
# ══════════════════════════════════════════════════

def _get_active_service_keys() -> list[str]:
    """Always reads live from DB — returns active service keys alphabetically."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT service_key FROM services WHERE is_active=1 ORDER BY display_name")
    keys = [row[0] for row in c.fetchall()]
    conn.close()
    return keys

def _service_has_any_stock(service_key: str) -> bool:
    """True if at least one duration still has stock > 0."""
    p = PRODUCTS.get(service_key, {})
    return any(v > 0 for v in p.get("stock", {}).values())

def browse_text(page: int = 0) -> str:
    """Header text for the paginated services browse screen."""
    keys        = _get_active_service_keys()
    total       = len(keys)
    total_pages = max(1, (total + START_MENU_PER_PAGE - 1) // START_MENU_PER_PAGE)
    cur         = max(0, min(page, total_pages - 1)) + 1
    return (
        f"📦 <b>SERVICES</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 <b>Select a service to buy:</b>\n\n"
        f"<i>📄 Page {cur} of {total_pages}</i>"
    )

def browse_kb(page: int = 0) -> InlineKeyboardMarkup:
    """
    Keyboard for the paginated services browse screen.
    Contains ONLY:
      • Service buttons (2 per row, START_MENU_PER_PAGE per page)
      • ⬅️ Previous  📄 X/Y  Next ➡️  navigation row
      • 🔙 Back To Menu  (returns user to welcome screen)

    No action buttons here — they live on the welcome screen.
    Reads services live from DB so admin changes appear instantly.
    Out-of-stock services remain visible with ❌ badge.
    """
    keys        = _get_active_service_keys()
    total       = len(keys)
    total_pages = max(1, (total + START_MENU_PER_PAGE - 1) // START_MENU_PER_PAGE)
    page        = max(0, min(page, total_pages - 1))

    start_i = page * START_MENU_PER_PAGE
    end_i   = min(start_i + START_MENU_PER_PAGE, total)

    rows: list[list[InlineKeyboardButton]] = []

    # ── Service grid (2 per row) ────────────────────
    svc_buttons: list[InlineKeyboardButton] = []
    for key in keys[start_i:end_i]:
        p      = PRODUCTS.get(key, {})
        dname  = p.get("display_name", key)
        in_stk = _service_has_any_stock(key)
        label  = f"✅ {dname}" if in_stk else f"❌ {dname}"
        style  = "success" if in_stk else "danger"
        svc_buttons.append(InlineKeyboardButton(
            text=label, callback_data=f"browse_{key}", style=style
        ))
    for i in range(0, len(svc_buttons), 2):
        rows.append(svc_buttons[i : i + 2])

    # ── Pagination row ──────────────────────────────
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Previous",
            callback_data=f"startpg_{page - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"📄 {page + 1} / {total_pages}",
        callback_data="startpg_noop"
    ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Next ➡️",
            callback_data=f"startpg_{page + 1}"
        ))
    rows.append(nav)

    # ── Back button ─────────────────────────────────
    rows.append([InlineKeyboardButton(
        text="🔙 Back To Menu",
        callback_data="back"
    )])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def welcome_kb(joined: bool = True) -> InlineKeyboardMarkup:
    """
    Keyboard for the /start welcome screen.
    Contains ONLY the five action buttons.
    For non-joined users, shows join prompt instead.
    """
    if joined:
        b = InlineKeyboardBuilder()
        b.button(text="🛒 BUY NOW",    callback_data="buy_now")
        b.button(text="💰 WALLET",     callback_data="wallet_view")
        b.button(text="🤝 REFERRAL",   callback_data="ref_view")
        b.button(text="📦 MY ORDERS",  callback_data="my_orders")
        b.button(text="📞 SUPPORT",    callback_data="contact")
        b.adjust(1)
        return b.as_markup()
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📢 Join Channel",
                url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
            )],
            [InlineKeyboardButton(
                text="✅ Maine Join Kar Liya - Check Karo",
                callback_data="check_join"
            )],
        ])

async def send_start_screen(target, joined: bool = True):
    """
    Send the welcome screen — welcome_msg (from settings or WELCOME_MSG fallback) + welcome_kb().
    One message. No pagination here; pagination is opened by BUY NOW.
    target can be Message or CallbackQuery.
    """
    kb   = welcome_kb(joined=joined)
    text = get_setting("welcome_msg") or WELCOME_MSG
    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        try:
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await target.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()

async def send_browse_screen(target, page: int = 0):
    """
    Send or edit-in-place the paginated services browse screen.
    Called by buy_now (new message) and startpg_ (edit in-place).
    target can be Message or CallbackQuery.
    """
    text = browse_text(page)
    kb   = browse_kb(page)
    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        try:
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await target.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()


def join_kb():
    """Standalone join prompt used in non-start contexts (e.g. auto-detect gate)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton(text="✅ Maine Join Kar Liya - Check Karo", callback_data="check_join")]
    ])

def duration_kb(product_key, prices, stock):
    b = InlineKeyboardBuilder()
    for dur, price in prices.items():
        s = stock.get(dur, 0)
        if s > 0:
            b.button(text=f"📺 {dur} — ₹{price}", callback_data=f"dur_{product_key}_{dur}_{price}")
        else:
            b.button(text=f"❌ {dur} — OUT OF STOCK", callback_data="sold_out")
    b.button(text="🔙 BACK", callback_data="back")
    b.adjust(1)
    return b.as_markup()

def confirm_kb(product_key, dur, amt):
    b = InlineKeyboardBuilder()
    b.button(text="✅ YES, PROCEED",  callback_data=f"yes_{product_key}_{dur}_{amt}")
    b.button(text="❌ CANCEL",        callback_data="no")
    b.adjust(2)
    return b.as_markup()

def payment_method_kb(product_key, dur, amt, bal):
    """Payment options: wallet (full / partial) and UPI QR — always both shown."""
    b = InlineKeyboardBuilder()
    if bal >= amt and amt > 0:
        b.button(text=f"💚 PAY WITH WALLET (₹{amt})",
                 callback_data=f"wuse_{product_key}_{dur}_{amt}")
    elif bal > 0:
        b.button(text=f"💚 WALLET ₹{bal:.0f} + QR ₹{amt - int(bal)}",
                 callback_data=f"wuse_{product_key}_{dur}_{amt}")
    else:
        b.button(text="💚 WALLET (₹0 — add money)", callback_data="wallet_empty")
    if gw_enabled():
        b.button(text=f"⚡ PAY ONLINE — AUTO (₹{amt})",
                 callback_data=f"gwbuy_{product_key}_{dur}_{amt}")
    b.button(text=f"📷 PAY WITH QR / UPI (₹{amt})",
             callback_data=f"wskip_{product_key}_{dur}_{amt}")
    b.button(text="❌ CANCEL", callback_data="no")
    b.adjust(1)
    return b.as_markup()

# Backwards-compatible alias
def wallet_confirm_kb(product_key, dur, amt, wallet_amt):
    return payment_method_kb(product_key, dur, amt, wallet_amt)

def paid_kb(product_key, dur, amt, oid):
    b = InlineKeyboardBuilder()
    b.button(text="💚 I HAVE PAID", callback_data=f"paid_{product_key}_{dur}_{amt}_{oid}")
    b.button(text="📞 SUPPORT",     callback_data="contact")
    b.adjust(1)
    return b.as_markup()

def rating_kb(oid):
    b = InlineKeyboardBuilder()
    for i in range(1, 6):
        b.button(text=f"⭐{i}", callback_data=f"rate_{oid}_{i}")
    b.button(text="⏭️ SKIP", callback_data=f"skip_{oid}")
    b.adjust(5)
    return b.as_markup()

def admin_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📦 PENDING ORDERS",    callback_data="admin_pending")
    b.button(text="📈 ANALYTICS",         callback_data="admin_analytics")
    b.button(text="🏆 TOP SERVICES",      callback_data="admin_top")
    b.button(text="👥 TOP REFERRERS",     callback_data="admin_referrers")
    b.button(text="👤 USER KUNDALI",      callback_data="admin_kundali")
    b.button(text="🚫 BAN / UNBAN",       callback_data="admin_ban")
    b.button(text="💳 WALLET MGMT",       callback_data="admin_wallet")
    b.button(text="⚡ PAYMENT GATEWAY",   callback_data="admin_gateway")
    b.button(text="📢 BROADCAST",         callback_data="admin_broadcast")
    b.button(text="📦 STOCK MGMT",        callback_data="admin_stock")
    b.button(text="🛠️ SERVICES MGMT",    callback_data="admin_services")
    b.button(text="📺 MINI APP SUBS",     callback_data="admin_minisubs")
    b.button(text="✏️ EDIT MESSAGES",    callback_data="admin_settings")
    b.button(text="👮 ADMIN MGMT",        callback_data="admin_admins")
    b.button(text="🔙 BACK",              callback_data="back")
    b.adjust(1)
    return b.as_markup()

def settings_kb() -> InlineKeyboardMarkup:
    """Admin: choose which bot message/setting to edit."""
    b = InlineKeyboardBuilder()
    b.button(text="🏠 Welcome Message",        callback_data="editset_welcome_msg")
    b.button(text="⏳ Payment Pending Message", callback_data="editset_payment_pending_msg")
    b.button(text="💤 Offline Auto-Reply",      callback_data="editset_offline_msg")
    b.button(text="📺 Mini App URL",            callback_data="editset_mini_app_url")
    b.button(text="🔗 Review Link",             callback_data="editset_review_link")
    b.button(text="🔙 BACK",                   callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()

def minisubs_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📋 View Active Subs",     callback_data="minisubs_list")
    b.button(text="🔍 Check User Sub",       callback_data="minisubs_check")
    b.button(text="❌ Revoke User Sub",      callback_data="minisubs_revoke")
    b.button(text="🔙 BACK",                callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()

PRODUCTS_PER_PAGE = STOCK_ADMIN_PER_PAGE   # alias used by stock_kb / services_mgmt_kb

def stock_kb(page=0):
    keys = list(PRODUCTS.keys())
    b = InlineKeyboardBuilder()
    start = page * PRODUCTS_PER_PAGE
    end   = min(start + PRODUCTS_PER_PAGE, len(keys))
    for i in range(start, end):
        key = keys[i]
        b.button(text=PRODUCTS[key]["display_name"], callback_data=f"stk_{key}")
    b.adjust(2)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"stkpg_{page-1}"))
    if end < len(keys):
        nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"stkpg_{page+1}"))
    if nav:
        b.row(*nav)
    b.button(text="🔙 BACK", callback_data="admin_back")
    return b.as_markup()

def services_mgmt_kb(page=0):
    """List all services (active + inactive) for admin management."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT service_key, display_name, is_active FROM services ORDER BY display_name")
    all_svcs = c.fetchall()
    conn.close()
    b = InlineKeyboardBuilder()
    start = page * PRODUCTS_PER_PAGE
    end   = min(start + PRODUCTS_PER_PAGE, len(all_svcs))
    for sk, dname, active in all_svcs[start:end]:
        prefix = "✅" if active else "🚫"
        b.button(text=f"{prefix} {dname}", callback_data=f"svc_{sk}")
    b.adjust(1)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"svcpg_{page-1}"))
    if end < len(all_svcs):
        nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"svcpg_{page+1}"))
    if nav:
        b.row(*nav)
    b.button(text="➕ Add New Service", callback_data="svc_add")
    b.button(text="🔙 BACK",           callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()

def wallet_mgmt_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ ADD BALANCE (GIVE)",   callback_data="wadm_add")
    b.button(text="➖ DEDUCT BALANCE (TAKE)", callback_data="wadm_deduct")
    b.button(text="🔍 CHECK USER WALLET",    callback_data="wadm_check")
    b.button(text="🏆 TOP WALLETS",          callback_data="wadm_top")
    b.button(text="🧾 RECENT WALLET LOGS",   callback_data="wadm_logs")
    b.button(text="🔙 BACK",                 callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()

def wallet_perm_kb() -> InlineKeyboardMarkup:
    """Owner toggles wallet give/take permission per admin."""
    b = InlineKeyboardBuilder()
    for auid, role, perm in get_admins_with_perm():
        if role == "owner":
            b.button(text=f"👑 {auid} — owner (always)", callback_data="wperm_noop")
        else:
            mark = "✅ HAS" if perm else "🚫 NO"
            b.button(text=f"{mark} wallet — {auid} ({role})", callback_data=f"wperm_{auid}")
    b.button(text="🔙 BACK", callback_data="admin_admins")
    b.adjust(1)
    return b.as_markup()

def broadcast_audience_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👥 ALL USERS",            callback_data="bcaud_all")
    b.button(text="🛒 BUYERS ONLY",          callback_data="bcaud_buyers")
    b.button(text="🕊️ NEVER BOUGHT",         callback_data="bcaud_nonbuyers")
    b.button(text="🔥 ACTIVE (7 DAYS)",      callback_data="bcaud_active")
    b.button(text="💚 WALLET BALANCE > 0",   callback_data="bcaud_wallet")
    b.button(text="📺 MINI APP SUBSCRIBERS", callback_data="bcaud_subs")
    b.button(text="🔙 BACK",                 callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()

def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🚀 SEND NOW",  callback_data="bc_send")
    b.button(text="❌ CANCEL",    callback_data="bc_cancel")
    b.adjust(2)
    return b.as_markup()

def service_detail_kb(service_key, is_active):
    b = InlineKeyboardBuilder()
    toggle_text = "🚫 Disable" if is_active else "✅ Enable"
    toggle_cb   = f"svctoggle_{service_key}"
    b.button(text="✏️ Edit Name",        callback_data=f"svcedit_name_{service_key}")
    b.button(text="📝 Edit Description", callback_data=f"svcedit_desc_{service_key}")
    b.button(text="🔑 Edit Keywords",    callback_data=f"svcedit_kw_{service_key}")
    b.button(text="💰 Edit Prices",      callback_data=f"svcedit_prices_{service_key}")
    b.button(text="📦 Edit Stock",       callback_data=f"svcedit_stock_{service_key}")
    b.button(text=toggle_text,        callback_data=toggle_cb)
    b.button(text="🗑️ Delete",       callback_data=f"svcdel_{service_key}")
    b.button(text="🔙 BACK",          callback_data="admin_services")
    b.adjust(2)
    return b.as_markup()

def deliver_kb(order_id, user_id, amount):
    b = InlineKeyboardBuilder()
    b.button(text="✅ DELIVERED",     callback_data=f"deliver_{order_id}_{user_id}_{amount}")
    b.button(text="❌ NOT DELIVERED", callback_data="not_delivered")
    b.adjust(2)
    return b.as_markup()

def approve_kb(oid, amount, uid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ APPROVE", callback_data=f"approve_{oid}_{amount}_{uid}"),
        InlineKeyboardButton(text="❌ REJECT",  callback_data=f"reject_{oid}_{uid}"),
    ]])

# ══════════════════════════════════════════════════
#  PAYMENT REVIEW CARD (manual admin approval)
# ══════════════════════════════════════════════════
PAY_METHOD_QR = "QR / UPI (Scan & Pay)"

def _fmt_username(user) -> str:
    return f"@{user.username}" if getattr(user, "username", None) else "—"

def _fmt_name(user) -> str:
    name = (getattr(user, "full_name", None) or "").strip()
    return name if name else "—"

def payment_review_card(user, amount, ref_id, *, purpose,
                        product_name=None, duration=None,
                        method=PAY_METHOD_QR, ref_label="Order ID") -> str:
    """Professional approval card shown to admins when a screenshot arrives."""
    lines = [
        "🧾 <b>PAYMENT VERIFICATION REQUIRED</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        "👤 <b>BUYER DETAILS</b>",
        f"• Name: <b>{_fmt_name(user)}</b>",
        f"• Username: {_fmt_username(user)}",
        f"• Buyer ID: <code>{user.id}</code>",
        "",
        "💳 <b>PAYMENT DETAILS</b>",
        f"• Method: <b>{method}</b>",
        f"• Amount: <b>₹{amount}</b>",
        f"• {ref_label}: <code>{ref_id}</code>",
        "",
        "🎯 <b>PURPOSE</b>",
    ]
    if product_name:
        lines.append(f"• Product: <b>{product_name}</b>")
        if duration:
            lines.append(f"• Plan / Duration: <b>{duration}</b>")
    else:
        lines.append(f"• <b>WALLET TOP-UP</b> — approve karne par ₹{amount} wallet mein add hoga")
    lines += [
        "",
        "📸 Screenshot upar attach hai — verify karke decide kijiye.",
        "━━━━━━━━━━━━━━━━━━━━",
        "⚠️ Auto approval OFF — manual admin decision required.",
    ]
    return "\n".join(lines)

def payment_decision_kb(oid, amount, uid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ APPROVE PAYMENT", callback_data=f"approve_{oid}_{amount}_{uid}"),
        InlineKeyboardButton(text="❌ DECLINE PAYMENT", callback_data=f"reject_{oid}_{uid}"),
    ]])

def deposit_decision_kb(dep_id, amount, uid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ APPROVE TOP-UP", callback_data=f"dep_approve_{dep_id}_{amount}_{uid}"),
        InlineKeyboardButton(text="❌ DECLINE TOP-UP", callback_data=f"dep_reject_{dep_id}_{uid}"),
    ]])

def admin_ids() -> list:
    conn = db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return ids

def admin_mgmt_kb():
    b = InlineKeyboardBuilder()
    b.button(text="💳 WALLET PERMISSIONS", callback_data="admins_perms")
    b.button(text="➕ Add Admin",    callback_data="admins_add")
    b.button(text="➖ Remove Admin", callback_data="admins_remove")
    b.button(text="📋 List Admins",  callback_data="admins_list")
    b.button(text="🔙 BACK",        callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()

def role_select_kb(target_id: int):
    b = InlineKeyboardBuilder()
    for role in ("super_admin", "admin", "delivery_admin"):
        b.button(text=role.replace("_", " ").title(),
                 callback_data=f"setrole_{target_id}_{role}")
    b.button(text="❌ Cancel", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()

# ══════════════════════════════════════════════════
#  PRODUCT DISPLAY HELPER
# ══════════════════════════════════════════════════
async def show_product_menu(target, product_key: str):
    """target can be Message or CallbackQuery."""
    p = PRODUCTS[product_key]
    desc = f"🔥 <b>{p['display_name']} DEALS</b>\n━━━━━━━━━━━━━━━━━━━━\n{p['description']}\n\n💰 <b>Available Plans:</b>\n"
    for d, pr in p["prices"].items():
        st = p["stock"].get(d, 0)
        label = "✅ In Stock" if st > 0 else "❌ OUT OF STOCK"
        desc += f"▬ {d} → ₹{pr} ({label})\n"
    desc += "\n📌 <b>Select duration:</b>"
    kb = duration_kb(product_key, p["prices"], p["stock"])
    if isinstance(target, Message):
        await target.answer(desc, parse_mode="HTML", reply_markup=kb)
    else:  # CallbackQuery
        await target.message.answer(desc, parse_mode="HTML", reply_markup=kb)
        await target.answer()

# ══════════════════════════════════════════════════
#  SERVICE DETECTION (word-boundary, no spam)
# ══════════════════════════════════════════════════
def detect_service(text: str) -> str | None:
    """
    Returns service key if any keyword matches — else None (silent).
    Uses whole-word regex matching to avoid false positives.
    Only short common codes (2-3 chars) use exact equality.
    """
    t = text.lower().strip()
    for key, data in PRODUCTS.items():
        for kw in data["keywords"]:
            kw = kw.lower()
            if len(kw) <= 3:
                # Short code: require exact word boundary
                if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", t):
                    return key
            else:
                if kw in t:
                    return key
    return None

# ══════════════════════════════════════════════════
#  COMMAND HANDLERS
# ══════════════════════════════════════════════════
@dp.message(Command("start"))
async def start_cmd(msg: Message, state: FSMContext):
    uid  = msg.from_user.id
    args = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else ""
    update_user(uid, msg.from_user.username, msg.from_user.first_name)
    await state.clear()

    # ── Referral processing via deep link ──────────
    if args.startswith("ref") and args[3:].isdigit():
        referrer_id = int(args[3:])
        if referrer_id != uid and get_referred_by(uid) is None:
            set_referred_by(uid, referrer_id)
            await state.update_data(pending_referrer=referrer_id)

    # ── Ban check ──────────────────────────────────
    if is_user_banned(uid):
        reason = get_ban_reason(uid)
        await msg.answer(
            f"🚫 <b>You have been banned.</b>\n\nReason: {reason}\n\nContact: @HIND_DEALS",
            parse_mode="HTML"
        )
        return

    # ── Admin gets welcome screen directly ────────
    if is_admin(uid):
        await send_start_screen(msg, joined=True)
        return

    # ── Force join ────────────────────────────────
    if not await is_joined(uid):
        # Show welcome message with join buttons instead of action buttons
        await send_start_screen(msg, joined=False)
    else:
        # Complete any pending referral now that user has joined
        data = await state.get_data()
        rid  = data.get("pending_referrer")
        if rid:
            await _process_referral(uid, rid)
            await state.update_data(pending_referrer=None)
        await send_start_screen(msg, joined=True)

@dp.message(Command("help"))
async def help_cmd(msg: Message):
    await msg.answer(HELP_MSG, parse_mode="HTML", reply_markup=main_kb())

@dp.message(Command("orders"))
async def orders_cmd(msg: Message):
    uid    = msg.from_user.id
    orders = get_user_orders(uid)
    if not orders:
        await msg.answer("📭 <b>No orders found.</b>\n\nType a service name to buy!", parse_mode="HTML", reply_markup=main_kb())
        return
    text = "📦 <b>YOUR ORDERS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for o in orders:
        em = "✅" if o[4]=="delivered" else ("⏳" if o[4]=="pending" else "❌")
        text += f"{em} <code>{o[0]}</code> — {o[1]} ({o[2]}) — ₹{o[3]}\n"
    await msg.answer(text, parse_mode="HTML", reply_markup=main_kb())

@dp.message(Command("order"))
async def order_cmd(msg: Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("⚠️ Usage: <code>/order ORDER_ID</code>", parse_mode="HTML")
        return
    o = get_order(parts[1])
    if not o:
        await msg.answer("❌ <b>Order not found</b>", parse_mode="HTML")
        return
    em   = "✅" if o[6]=="delivered" else ("⏳" if o[6]=="pending" else "❌")
    text = (f"📦 <b>ORDER DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 <code>{o[0]}</code>\n🛍️ {o[2]}\n⏱️ {o[3]}\n"
            f"💰 ₹{o[4]}")
    if o[5]:
        text += f"  (💚 Wallet used: ₹{o[5]:.0f})"
    text += f"\n📊 {em} {o[6].upper()}\n📅 {o[7]}"
    if o[9] > 0:
        text += f"\n⭐ {'⭐'*o[9]}"
        if o[10]:
            text += f"\n📝 <i>{o[10]}</i>"
    await msg.answer(text, parse_mode="HTML", reply_markup=main_kb())

@dp.message(Command("cancel"))
async def cancel_cmd(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("✅ <b>Cancelled.</b> Type a service name to continue!", parse_mode="HTML", reply_markup=main_kb())

@dp.message(Command("contact"))
async def contact_cmd(msg: Message):
    review = get_setting("review_link", "https://t.me/HIND_DEALS_REVIEWS")
    await msg.answer(
        "📞 <b>Contact Support</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Message directly: @HIND_DEALS\n\n"
        f"📢 Reviews: {review}",
        parse_mode="HTML", reply_markup=main_kb()
    )

@dp.message(Command("rules"))
async def rules_cmd(msg: Message):
    await msg.answer(RULES_MSG, parse_mode="HTML", reply_markup=main_kb())

@dp.message(Command("myapp"))
async def myapp_cmd(msg: Message):
    """User checks their HIND DEALS TV subscription status."""
    uid = msg.from_user.id
    update_user(uid, msg.from_user.username, msg.from_user.first_name)
    sub = get_mini_app_sub(uid)
    if not sub:
        b = InlineKeyboardBuilder()
        b.button(text="📺 Buy HIND DEALS TV", callback_data="browse_hindtv")
        b.button(text="🔙 Back", callback_data="back")
        b.adjust(1)
        await msg.answer(
            "📺 <b>HIND DEALS TV</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "❌ <b>No active subscription found.</b>\n\n"
            "Subscribe to access Live Sports, Movies, FIFA and more!",
            parse_mode="HTML", reply_markup=b.as_markup()
        )
        return
    plan, expiry = sub
    mini_url = get_setting("mini_app_url")
    rows = []
    if mini_url:
        rows.append([InlineKeyboardButton(
            text="▶️ Open HIND DEALS TV",
            web_app=types.WebAppInfo(url=mini_url)
        )])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="back")])
    await msg.answer(
        f"📺 <b>HIND DEALS TV — Active Subscription</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Plan: <b>{plan}</b>\n"
        f"📅 Expires: <b>{expiry[:10]}</b>\n\n"
        f"{'▶️ Tap button below to open Mini App.' if mini_url else '⏳ Mini App link coming soon — contact @HIND_DEALS'}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@dp.message(Command("wallet"))
async def wallet_cmd(msg: Message):
    uid = msg.from_user.id
    update_user(uid, msg.from_user.username, msg.from_user.first_name)
    await _show_wallet(msg, uid)

@dp.message(Command("referral"))
async def referral_cmd(msg: Message):
    uid = msg.from_user.id
    update_user(uid, msg.from_user.username, msg.from_user.first_name)
    await _show_referral(msg, uid)

@dp.message(Command("admin"))
async def admin_cmd(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ <b>Unauthorized</b>", parse_mode="HTML")
        return
    await _send_admin_panel(msg)

# Only owner can manage admins
@dp.message(Command("addadmin"))
async def addadmin_cmd(msg: Message, state: FSMContext):
    if msg.from_user.id != OWNER_ID:
        await msg.answer("⛔ <b>Only owner can add admins.</b>", parse_mode="HTML")
        return
    await msg.answer("👤 <b>Send the user ID to add as admin:</b>", parse_mode="HTML")
    await state.set_state(AdminManageState.waiting_add_id)

@dp.message(Command("removeadmin"))
async def removeadmin_cmd(msg: Message, state: FSMContext):
    if msg.from_user.id != OWNER_ID:
        await msg.answer("⛔ <b>Only owner can remove admins.</b>", parse_mode="HTML")
        return
    await msg.answer("👤 <b>Send the admin user ID to remove:</b>", parse_mode="HTML")
    await state.set_state(AdminManageState.waiting_remove)

@dp.message(Command("admins"))
async def admins_cmd(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ <b>Unauthorized</b>", parse_mode="HTML")
        return
    rows = get_all_admins()
    text = "👮 <b>ADMIN LIST</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for uid_, role, date in rows:
        text += f"🔹 <code>{uid_}</code> — <b>{role}</b> — {date}\n"
    await msg.answer(text, parse_mode="HTML")

# ══════════════════════════════════════════════════
#  QR DEPOSIT  ( /qr  |  "qr"  |  "qr 100" )
# ══════════════════════════════════════════════════
async def send_qr_deposit(msg: Message, amount) -> None:
    """Send (or re-use) a wallet-deposit QR that stays valid for QR_VALID_MIN minutes."""
    uid = msg.from_user.id
    try:
        amount = int(float(amount))
    except Exception:
        amount = 0
    if amount <= 0:
        await msg.answer("❌ <b>Amount galat hai.</b>\n\nJaise: <code>qr 100</code>", parse_mode="HTML")
        return

    rec = active_qr(uid, amount)
    if rec:
        await msg.answer(
            f"✅ <b>₹{amount} ka QR pehle se active hai</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{qr_valid_line(rec)}\n\n"
            f"🆔 Deposit ID: <code>{rec['dep_id']}</code>\n"
            f"UPI: <code>{UPI_ID}</code>\n\n"
            f"Upar bheja hua wahi QR scan kijiye. Expire hone ke baad naya QR milega.",
            parse_mode="HTML")
        return

    dep_id = generate_deposit_id(uid)
    save_deposit(dep_id, uid, amount)
    rec = remember_qr(uid, amount, dep_id)
    dep_paid_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="I HAVE PAID", callback_data=f"dep_paid_{dep_id}_{amount}")
    ]])
    await send_payment_qr(
        msg, amount,
        (
            f"💳 <b>WALLET DEPOSIT — ₹{amount}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"UPI: <code>{UPI_ID}</code>\n"
            f"Amount: <b>₹{amount}</b>\n\n"
            f"{qr_valid_line(rec)}\n\n"
            f"📌 Steps:\n"
            f"1️⃣ Scan QR\n"
            f"2️⃣ Pay ₹{amount}\n"
            f"3️⃣ Click <b>I HAVE PAID</b> below\n\n"
            f"ℹ️ Admin manually verify karke wallet me add karega.\n"
            f"🆔 Deposit ID: <code>{dep_id}</code>"
        ),
        reply_markup=dep_paid_kb
    )

async def ask_qr_amount(msg: Message, state: FSMContext) -> None:
    await state.set_state(QRState.waiting_amount)
    await msg.answer(
        "💳 <b>QR BANANA HAI — kitne ka?</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Sirf amount bhejiye (jaise <code>100</code>).\n\n"
        f"⏳ QR banne ke baad <b>{QR_VALID_MIN} minute</b> valid rahega.\n"
        "❌ Cancel karne ke liye /cancel bhejiye.",
        parse_mode="HTML")

@dp.message(Command("qr"))
async def qr_cmd(msg: Message, state: FSMContext):
    await state.clear()
    parts = (msg.text or "").split()
    if len(parts) > 1:
        m = re.search(r"(\d+(?:\.\d+)?)", parts[1])
        if m:
            await send_qr_deposit(msg, m.group(1))
            return
    await ask_qr_amount(msg, state)

@dp.message(QRState.waiting_amount)
async def qr_amount_handler(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if text.startswith("/"):
        await state.clear()
        await msg.answer("❌ <b>QR cancel ho gaya.</b>", parse_mode="HTML")
        return
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if not m:
        await msg.answer("❌ <b>Sirf number bhejiye</b> — jaise <code>100</code>", parse_mode="HTML")
        return
    amount = int(float(m.group(1)))
    if amount <= 0:
        await msg.answer("❌ <b>Amount ₹1 se zyada hona chahiye.</b>", parse_mode="HTML")
        return
    await state.clear()
    await send_qr_deposit(msg, amount)

# ══════════════════════════════════════════════════
#  WALLET / REFERRAL DISPLAY HELPERS
# ══════════════════════════════════════════════════
async def _show_wallet(target, uid: int):
    bal, unlocked = get_wallet(uid)
    ref_code, ref_count, _ = get_referral_info(uid)
    history = get_wallet_history(uid, 5)

    text = (f"💚 <b>YOUR WALLET</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Balance: <b>₹{bal:.2f}</b>\n"
            f"🤝 Referrals: {ref_count}\n\n"
            f"➕ <b>Money add karne ke liye</b> bas type kijiye:\n"
            f"<code>qr 100</code>  (jitna amount chahiye)\n\n"
            f"🛒 Buy karte waqt wallet se ya QR se — dono option milenge.\n\n"
            f"📋 <b>Recent Transactions:</b>\n")
    if history:
        for amt, typ, reason, date in history:
            em = "➕" if typ=="credit" else "➖"
            text += f"{em} ₹{amt:.2f} — {reason[:30]}\n"
    else:
        text += "No transactions yet.\n"

    b = InlineKeyboardBuilder()
    if gw_enabled():
        b.button(text="⚡ ADD MONEY (Instant UPI)", callback_data="gwadd")
    b.button(text="🛒 BUY NOW",     callback_data="buy_now")
    b.button(text="🤝 My Referral", callback_data="ref_view")
    b.button(text="🔙 BACK",        callback_data="back")
    b.adjust(1)
    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=b.as_markup())
    else:
        await target.message.answer(text, parse_mode="HTML", reply_markup=b.as_markup())
        await target.answer()

async def _show_referral(target, uid: int):
    ref_code, ref_count, unlocked = get_referral_info(uid)
    bal, _ = get_wallet(uid)
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start={ref_code}"

    text = (f"🤝 <b>YOUR REFERRAL PANEL</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 Your Referral Link:\n<code>{ref_link}</code>\n\n"
            f"📊 <b>Stats:</b>\n"
            f"• Successful Referrals: <b>{ref_count}</b>\n"
            f"• Wallet Balance: <b>₹{bal:.2f}</b>\n"
            f"• Wallet: ✅ Buy karne ke liye ready\n\n"
            f"💰 <b>Rewards:</b>\n"
            f"• You earn <b>₹{REFERRAL_REWARD}</b> per referral\n"
            f"• New user gets <b>₹{WELCOME_BONUS}</b> welcome bonus\n\n"
            f"📌 Share your link — friends must join channel to activate reward!")

    b = InlineKeyboardBuilder()
    b.button(text="💚 My Wallet", callback_data="wallet_view")
    b.button(text="🔙 BACK",      callback_data="back")
    b.adjust(1)
    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=b.as_markup())
    else:
        await target.message.answer(text, parse_mode="HTML", reply_markup=b.as_markup())
        await target.answer()

async def _send_admin_panel(target):
    u, t, p, d, r, refs, wused = get_stats()
    d_cnt, d_rev = get_daily_sales()
    text = (f"🔧 <b>ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>STATS</b>\n"
            f"👥 Users: {u}  |  📦 Orders: {t}\n"
            f"⏳ Pending: {p}  |  ✅ Done: {d}\n"
            f"💰 Revenue: ₹{r}  |  💚 Wallet Used: ₹{wused:.0f}\n"
            f"🤝 Referrals: {refs}\n\n"
            f"📅 <b>TODAY</b>\n"
            f"✅ Sales: {d_cnt}  |  ₹{d_rev}")
    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=admin_kb())
    else:
        try:
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=admin_kb())
        except Exception:
            await target.message.answer(text, parse_mode="HTML", reply_markup=admin_kb())
        await target.answer()

# ══════════════════════════════════════════════════
#  REFERRAL PROCESSING
# ══════════════════════════════════════════════════
async def _process_referral(referred_id: int, referrer_id: int):
    """Called when new user joins channel. Completes referral if valid."""
    ok = record_referral(referrer_id, referred_id)
    if not ok:
        return
    complete_referral_reward(referrer_id, referred_id)
    # Notify referrer
    newly_unlocked = _check_wallet_unlock(referrer_id)
    try:
        msg_to_referrer = (f"🎉 <b>Referral Completed!</b>\n\n"
                           f"User joined via your link.\n"
                           f"💚 You earned <b>₹{REFERRAL_REWARD}</b>!")
        if newly_unlocked:
            msg_to_referrer += "\n\n🔓 <b>WALLET UNLOCKED!</b> You can now use wallet for purchases."
        await bot.send_message(referrer_id, msg_to_referrer, parse_mode="HTML")
    except Exception:
        pass

# ══════════════════════════════════════════════════
#  AUTO SERVICE DETECTION (silent if not found)
# ══════════════════════════════════════════════════
@dp.message(StateFilter(None))
async def auto_detect_service(msg: Message, state: FSMContext):
    uid  = msg.from_user.id
    text = msg.text or ""

    # Commands handled by their own handlers — ignore
    if text.startswith("/"):
        return

    # Admins: no auto-detect noise
    if is_admin(uid):
        return

    if is_user_banned(uid):
        return

    # ── One-time offline auto-reply (sent only ONCE per user) ──
    if not has_auto_replied(uid):
        mark_auto_replied(uid)
        offline_txt = get_setting("offline_msg")
        try:
            await msg.answer(offline_txt, parse_mode="HTML")
        except Exception:
            pass

    # Not joined — prompt join
    if not await is_joined(uid):
        await msg.answer(
            "🔒 <b>Join our channel first!</b>\n\nRequired to use the bot.",
            parse_mode="HTML",
            reply_markup=join_kb()
        )
        return

    # Try to detect service
    found = detect_service(text)
    if found:
        await show_product_menu(msg, found)
    elif re.search(r"\brefund\b", text.lower()):
        await msg.answer(REFUND_MSG, parse_mode="HTML", reply_markup=main_kb())
    # else: SILENT — do not send "service not found" for normal conversation

    # ── QR Deposit Detection ────────────────────────
    low = text.lower().strip()

    # Bare "qr" / "qr code" / "qr banao" (no amount) -> amount poocho
    if re.fullmatch(r"/?qr(?:\s*code)?(?:\s*(?:banao|bana|do|chahiye|send|dedo))?", low):
        await ask_qr_amount(msg, state)
        return

    # "qr 20", "qr 20rs", "qr20rs", "qr 20 rupees" ...
    qr_match = re.search(r"\bqr\s*(\d+(?:\.\d+)?)\s*(?:rs|₹|rupees|rps|rupe)?\b", low)
    if qr_match:
        await send_qr_deposit(msg, qr_match.group(1))
        return

# ══════════════════════════════════════════════════
#  SCREENSHOT HANDLER
# ══════════════════════════════════════════════════
@dp.message(OrderState.waiting_for_screenshot)
async def screenshot_handler(msg: Message, state: FSMContext):
    if not msg.photo:
        await msg.answer("❌ <b>Please send a screenshot image.</b>", parse_mode="HTML")
        return

    data         = await state.get_data()
    oid          = data.get("oid")
    product_key  = data.get("product_key")
    duration     = data.get("duration")
    amount       = data.get("amount")
    product_name = PRODUCTS.get(product_key, {}).get("display_name", "Unknown")

    card = payment_review_card(
        msg.from_user, amount, oid,
        purpose="product",
        product_name=product_name,
        duration=duration,
        ref_label="Order ID",
    )
    for admin_id in admin_ids():
        try:
            await bot.send_photo(
                admin_id,
                photo=msg.photo[-1].file_id,
                caption=card,
                parse_mode="HTML",
                reply_markup=payment_decision_kb(oid, amount, msg.from_user.id)
            )
        except Exception:
            pass

    await msg.answer(
        get_setting("payment_pending_msg"),
        parse_mode="HTML", reply_markup=main_kb()
    )
    await state.clear()

# ══════════════════════════════════════════════════
#  DEPOSIT SCREENSHOT HANDLER
# ══════════════════════════════════════════════════
@dp.message(DepositState.waiting_for_screenshot)
async def deposit_screenshot_handler(msg: Message, state: FSMContext):
    if not msg.photo:
        await msg.answer("❌ <b>Screenshot bhejiye (photo).</b>", parse_mode="HTML")
        return

    data      = await state.get_data()
    dep_id    = data.get("dep_id")
    amount    = data.get("dep_amount")

    card = payment_review_card(
        msg.from_user, amount, dep_id,
        purpose="wallet",
        ref_label="Deposit ID",
    )
    for admin_id in admin_ids():
        try:
            await bot.send_photo(
                admin_id,
                photo=msg.photo[-1].file_id,
                caption=card,
                parse_mode="HTML",
                reply_markup=deposit_decision_kb(dep_id, amount, msg.from_user.id)
            )
        except Exception:
            pass

    await msg.answer(
        "⏳ <b>Screenshot mil gaya!</b>\n\n"
        "🔍 Admin verify kar raha hai.\n"
        "✅ Approve hone par wallet mein amount add ho jayega.\n\n"
        "📩 Support: @HIND_DEALS",
        parse_mode="HTML",
        reply_markup=main_kb()
    )
    await state.clear()

# ══════════════════════════════════════════════════
#  REVIEW HANDLER
# ══════════════════════════════════════════════════
@dp.message(OrderState.waiting_for_review)
async def review_handler(msg: Message, state: FSMContext):
    data   = await state.get_data()
    oid    = data.get("oid")
    rating = data.get("rating", 0)

    if msg.text and msg.text.strip().lower() in ("/skip", "skip"):
        await msg.answer("✅ <b>Thank you! Come back soon!</b> 🎉", parse_mode="HTML")
    else:
        update_rating(oid, rating, msg.text or "")
        await msg.answer(
            f"✅ <b>Thank you for your feedback!</b> {'⭐'*rating}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n<i>\"{msg.text}\"</i>\n\nCome back soon! 🎉",
            parse_mode="HTML"
        )
    await state.clear()

# ══════════════════════════════════════════════════
#  ADMIN TEXT HANDLERS
# ══════════════════════════════════════════════════
@dp.message(AdminState.waiting_for_user_id)
async def admin_user_handler(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    try:
        uid = int(msg.text.strip())
    except Exception:
        await msg.answer("❌ <b>Invalid ID</b>", parse_mode="HTML")
        await state.clear()
        return

    fsm    = await state.get_data()
    action = fsm.get("admin_action")

    # ── Mini app subscription actions ──────────────
    if action == "minisubs_check":
        sub = get_mini_app_sub(uid)
        if sub:
            await msg.answer(f"📺 <b>Active Sub</b>\n\n👤 <code>{uid}</code>\n✅ Plan: {sub[0]}\n📅 Expires: {sub[1][:10]}", parse_mode="HTML")
        else:
            await msg.answer(f"❌ User <code>{uid}</code> ka koi active subscription nahi hai.", parse_mode="HTML")
        await state.clear()
        return

    if action == "minisubs_revoke":
        conn = db()
        c = conn.cursor()
        c.execute("UPDATE mini_app_subscriptions SET is_active=0 WHERE user_id=?", (uid,))
        changed = c.rowcount
        conn.commit()
        conn.close()
        await msg.answer(
            f"✅ <b>{changed} subscription(s) revoked</b> for <code>{uid}</code>." if changed
            else f"ℹ️ User <code>{uid}</code> ka koi active sub nahi tha.", parse_mode="HTML")
        if changed:
            try:
                await bot.send_message(uid, "📺 <b>Aapka HIND DEALS TV subscription band kar diya gaya hai.</b>", parse_mode="HTML")
            except Exception:
                pass
        await state.clear()
        return

    user, orders = get_user_full(uid)
    if not user:
        await msg.answer(f"❌ <b>User {uid} not found</b>", parse_mode="HTML")
        await state.clear()
        return

    total   = len(orders)
    done    = sum(1 for o in orders if o[4]=="delivered")
    rej     = sum(1 for o in orders if o[4]=="rejected")
    pend    = sum(1 for o in orders if o[4]=="pending")
    spent   = user[8] if len(user) > 8 else 0
    bal     = user[9] if len(user) > 9 else 0
    ref_cnt = user[12] if len(user) > 12 else 0

    text  = f"👤 <b>USER KUNDALI</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🆔 ID: <code>{user[0]}</code>\n"
    text += f"👤 @{user[1] or 'N/A'}  |  📛 {user[2] or 'N/A'}\n"
    text += f"📅 Joined: {user[3]}\n"
    text += f"🕐 Active: {user[4]}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📦 Orders: {total}  (✅{done} ❌{rej} ⏳{pend})\n"
    text += f"💰 Spent: ₹{spent}  |  💚 Wallet: ₹{bal:.2f}\n"
    text += f"🤝 Referrals: {ref_cnt}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📋 LAST ORDERS:\n"
    for o in orders[:5]:
        em = "✅" if o[4]=="delivered" else ("⏳" if o[4]=="pending" else "❌")
        text += f"{em} <code>{o[0]}</code> — {o[1]} ({o[2]}) — ₹{o[3]}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🚫 STATUS: <b>{'BANNED' if user[5] else 'ACTIVE'}</b>"
    if user[5] and len(user) > 6 and user[6]:
        text += f"\n📌 Reason: {user[6]}"

    rows = []
    if can_manage_wallet(msg.from_user.id):
        rows.append([
            InlineKeyboardButton(text="➕ ADD BALANCE", callback_data=f"wquick_add_{uid}"),
            InlineKeyboardButton(text="➖ DEDUCT",      callback_data=f"wquick_ded_{uid}"),
        ])
    if user[5] == 0:
        rows.append([InlineKeyboardButton(text="🔨 BAN USER", callback_data=f"ban_now_{uid}")])
    else:
        rows.append([InlineKeyboardButton(text="🔓 UNBAN USER", callback_data=f"unban_{uid}")])
    rows.append([InlineKeyboardButton(text="📞 CONTACT", callback_data=f"contact_{uid}")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await msg.answer(text, parse_mode="HTML", reply_markup=kb)
    await state.clear()

# ══════════════════════════════════════════════════
#  BROADCAST ENGINE v2 (audience targeting + any media)
# ══════════════════════════════════════════════════
AUDIENCE_LABELS = {
    "all":       "👥 All users",
    "buyers":    "🛒 Buyers only",
    "nonbuyers": "🕊️ Never bought",
    "active":    "🔥 Active last 7 days",
    "wallet":    "💚 Wallet balance > 0",
    "subs":      "📺 Mini app subscribers",
}

def get_broadcast_targets(audience: str) -> list[int]:
    """Return user IDs for the chosen audience (banned users always excluded)."""
    conn = db()
    c = conn.cursor()
    if audience == "buyers":
        q = """SELECT DISTINCT u.user_id FROM users u
               JOIN orders o ON o.user_id = u.user_id
               WHERE u.is_banned=0"""
    elif audience == "nonbuyers":
        q = """SELECT u.user_id FROM users u
               WHERE u.is_banned=0
                 AND u.user_id NOT IN (SELECT user_id FROM orders)"""
    elif audience == "active":
        q = """SELECT user_id FROM users
               WHERE is_banned=0 AND last_active >= datetime('now','-7 days')"""
    elif audience == "wallet":
        q = "SELECT user_id FROM users WHERE is_banned=0 AND wallet_balance > 0"
    elif audience == "subs":
        q = """SELECT DISTINCT u.user_id FROM users u
               JOIN mini_app_subscriptions m ON m.user_id = u.user_id
               WHERE u.is_banned=0 AND m.is_active=1"""
    else:
        q = "SELECT user_id FROM users WHERE is_banned=0"
    try:
        c.execute(q)
        rows = [r[0] for r in c.fetchall()]
    except Exception:
        rows = []
    conn.close()
    return rows

@dp.message(BroadcastState.waiting_content)
async def broadcast_content_handler(msg: Message, state: FSMContext):
    """Accepts ANY message (text, photo, video, document, sticker…) as broadcast content."""
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    data     = await state.get_data()
    audience = data.get("bc_audience", "all")
    targets  = get_broadcast_targets(audience)
    await state.update_data(bc_chat_id=msg.chat.id, bc_msg_id=msg.message_id, bc_count=len(targets))

    await msg.answer(
        f"👀 <b>BROADCAST PREVIEW</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 Audience: <b>{AUDIENCE_LABELS.get(audience, audience)}</b>\n"
        f"👥 Recipients: <b>{len(targets)}</b>\n"
        f"📨 Content: the message you just sent (upar wala)\n\n"
        f"Bhejne ke liye <b>SEND NOW</b> dabaiye.",
        parse_mode="HTML",
        reply_markup=broadcast_confirm_kb()
    )
    await state.set_state(BroadcastState.waiting_confirm)

async def run_broadcast(admin_msg: Message, chat_id: int, msg_id: int, targets: list[int], audience: str):
    sent = failed = blocked = 0
    status = await admin_msg.answer(
        f"📢 <b>Broadcasting…</b>\n0 / {len(targets)}", parse_mode="HTML"
    )
    for i, u in enumerate(targets, 1):
        try:
            await bot.copy_message(chat_id=u, from_chat_id=chat_id, message_id=msg_id)
            sent += 1
        except Exception as e:
            txt = str(e).lower()
            if "blocked" in txt or "chat not found" in txt or "deactivated" in txt:
                blocked += 1
            else:
                failed += 1
        await asyncio.sleep(0.05)
        if i % 25 == 0 or i == len(targets):
            try:
                await status.edit_text(
                    f"📢 <b>Broadcasting…</b>\n{i} / {len(targets)}\n"
                    f"✅ {sent}  🚫 {blocked}  ⚠️ {failed}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    try:
        await status.edit_text(
            f"✅ <b>BROADCAST COMPLETE</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 Audience: <b>{AUDIENCE_LABELS.get(audience, audience)}</b>\n"
            f"👥 Total: {len(targets)}\n"
            f"✅ Delivered: <b>{sent}</b>\n"
            f"🚫 Blocked bot: {blocked}\n"
            f"⚠️ Failed: {failed}",
            parse_mode="HTML"
        )
    except Exception:
        pass

# ══════════════════════════════════════════════════
#  ADMIN WALLET MANAGEMENT (give / take balance)
# ══════════════════════════════════════════════════
def _parse_wallet_input(text: str):
    """Parse '123456789 50 optional reason' -> (uid, amount, reason)."""
    parts = (text or "").strip().split()
    if len(parts) < 2:
        return None, None, ""
    try:
        uid = int(parts[0])
        amount = float(parts[1])
    except Exception:
        return None, None, ""
    if amount <= 0:
        return None, None, ""
    reason = " ".join(parts[2:]).strip()
    return uid, amount, reason

@dp.message(WalletAdminState.waiting_add)
async def wadm_add_handler(msg: Message, state: FSMContext):
    if not can_manage_wallet(msg.from_user.id):
        await state.clear()
        return
    uid, amount, reason = _parse_wallet_input(msg.text)
    if not uid:
        await msg.answer("❌ Format galat.\n\nUse: <code>USER_ID AMOUNT reason</code>\nExample: <code>123456789 50 bonus</code>", parse_mode="HTML")
        return
    u, _ = get_user_full(uid)
    if not u:
        await msg.answer(f"❌ User <code>{uid}</code> bot me nahi mila.", parse_mode="HTML")
        await state.clear()
        return
    credit_wallet(uid, amount, reason or f"Admin credit by {msg.from_user.id}")
    bal, _ = get_wallet(uid)
    await msg.answer(
        f"✅ <b>₹{amount:.0f} ADDED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 User: <code>{uid}</code>\n💚 New Balance: <b>₹{bal:.2f}</b>\n"
        f"📝 Reason: {reason or 'Admin credit'}",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            uid,
            f"💚 <b>WALLET CREDITED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"➕ ₹{amount:.0f} aapke wallet me add kiya gaya.\n"
            f"💰 New Balance: <b>₹{bal:.2f}</b>\n"
            f"📝 {reason or 'Admin credit'}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await state.clear()

@dp.message(WalletAdminState.waiting_deduct)
async def wadm_deduct_handler(msg: Message, state: FSMContext):
    if not can_manage_wallet(msg.from_user.id):
        await state.clear()
        return
    uid, amount, reason = _parse_wallet_input(msg.text)
    if not uid:
        await msg.answer("❌ Format galat.\n\nUse: <code>USER_ID AMOUNT reason</code>", parse_mode="HTML")
        return
    ok = debit_wallet(uid, amount, reason or f"Admin debit by {msg.from_user.id}")
    bal, _ = get_wallet(uid)
    if not ok:
        await msg.answer(f"❌ <b>Insufficient balance.</b>\n\n👤 <code>{uid}</code>\n💚 Current: ₹{bal:.2f}", parse_mode="HTML")
        await state.clear()
        return
    await msg.answer(
        f"✅ <b>₹{amount:.0f} DEDUCTED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 User: <code>{uid}</code>\n💚 New Balance: <b>₹{bal:.2f}</b>\n"
        f"📝 Reason: {reason or 'Admin debit'}",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            uid,
            f"➖ <b>WALLET DEBITED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"₹{amount:.0f} wallet se kaata gaya.\n"
            f"💰 New Balance: <b>₹{bal:.2f}</b>\n"
            f"📝 {reason or 'Admin debit'}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await state.clear()

@dp.message(WalletAdminState.waiting_check)
async def wadm_check_handler(msg: Message, state: FSMContext):
    if not can_manage_wallet(msg.from_user.id):
        await state.clear()
        return
    try:
        uid = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Sirf user ID bhejiye.", parse_mode="HTML")
        return
    u, _ = get_user_full(uid)
    if not u:
        await msg.answer(f"❌ User <code>{uid}</code> not found.", parse_mode="HTML")
        await state.clear()
        return
    bal, _ = get_wallet(uid)
    hist = get_wallet_history(uid, 8)
    text = (f"💳 <b>USER WALLET</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <code>{uid}</code> @{u[1] or 'N/A'}\n"
            f"💰 Balance: <b>₹{bal:.2f}</b>\n\n🧾 <b>Last transactions:</b>\n")
    if hist:
        for amt, typ, reason, date in hist:
            em = "➕" if typ == "credit" else "➖"
            text += f"{em} ₹{amt:.2f} — {reason[:28]} ({date[5:16]})\n"
    else:
        text += "No transactions yet.\n"
    b = InlineKeyboardBuilder()
    b.button(text="➕ ADD BALANCE", callback_data=f"wquick_add_{uid}")
    b.button(text="➖ DEDUCT",      callback_data=f"wquick_ded_{uid}")
    b.button(text="🔙 BACK",        callback_data="admin_wallet")
    b.adjust(2)
    await msg.answer(text, parse_mode="HTML", reply_markup=b.as_markup())
    await state.clear()

@dp.message(AdminState.waiting_for_stock_update)
async def stock_update_handler(msg: Message, state: FSMContext):
    data        = await state.get_data()
    product_key = data.get("stock_product_key")
    try:
        parts    = msg.text.split("|")
        duration = parts[0].strip()
        new_stk  = int(parts[1].strip())
        update_stock_db(product_key, duration, new_stk)
        pname = PRODUCTS.get(product_key, {}).get("display_name", product_key)
        await msg.answer(f"✅ <b>{pname}</b>\n• {duration}: {new_stk} units", parse_mode="HTML")
    except Exception:
        await msg.answer("❌ <b>Invalid format.</b>\n\nUse: <code>duration|new_stock</code>\nExample: <code>1 Month|50</code>", parse_mode="HTML")
    await state.clear()

@dp.message(AdminState.waiting_for_ban_reason)
async def ban_reason_handler(msg: Message, state: FSMContext):
    data   = await state.get_data()
    uid    = data.get("ban_user_id")
    reason = msg.text.strip()
    if uid:
        ban_user(uid, reason)
        await msg.answer(f"✅ <b>User {uid} BANNED!</b>\n\nReason: {reason}", parse_mode="HTML")
        try:
            await bot.send_message(uid, f"🚫 <b>You have been banned.</b>\n\nReason: {reason}\n\nContact: @HIND_DEALS", parse_mode="HTML")
        except Exception:
            pass
    await state.clear()

# ── Admin-manage states ────────────────────────────
@dp.message(AdminManageState.waiting_add_id)
async def admin_add_id_handler(msg: Message, state: FSMContext):
    if msg.from_user.id != OWNER_ID:
        await state.clear()
        return
    try:
        target = int(msg.text.strip())
    except Exception:
        await msg.answer("❌ <b>Invalid ID</b>", parse_mode="HTML")
        await state.clear()
        return
    if get_admin_role(target):
        await msg.answer(f"ℹ️ User <code>{target}</code> is already an admin.", parse_mode="HTML")
        await state.clear()
        return
    await state.update_data(new_admin_id=target)
    await msg.answer(f"👤 <b>User {target}</b>\n\nSelect role:", parse_mode="HTML", reply_markup=role_select_kb(target))
    await state.clear()  # role is handled via callback

@dp.message(AdminManageState.waiting_remove)
async def admin_remove_handler(msg: Message, state: FSMContext):
    if msg.from_user.id != OWNER_ID:
        await state.clear()
        return
    try:
        target = int(msg.text.strip())
    except Exception:
        await msg.answer("❌ <b>Invalid ID</b>", parse_mode="HTML")
        await state.clear()
        return
    if target == OWNER_ID:
        await msg.answer("⛔ Cannot remove owner.", parse_mode="HTML")
        await state.clear()
        return
    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id=?", (target,))
    conn.commit()
    conn.close()
    await msg.answer(f"✅ <b>Admin {target} removed.</b>", parse_mode="HTML")
    await state.clear()

# ── Service-add FSM ────────────────────────────────
@dp.message(ServiceAddState.name)
async def svc_add_name(msg: Message, state: FSMContext):
    await state.update_data(svc_name=msg.text.strip())
    await msg.answer("📝 <b>Send service description:</b>", parse_mode="HTML")
    await state.set_state(ServiceAddState.description)

@dp.message(ServiceAddState.description)
async def svc_add_desc(msg: Message, state: FSMContext):
    await state.update_data(svc_desc=msg.text.strip())
    await msg.answer("🔑 <b>Send keywords (comma-separated):</b>\n\nExample: <code>cooler,cool,clr</code>", parse_mode="HTML")
    await state.set_state(ServiceAddState.keywords)

@dp.message(ServiceAddState.keywords)
async def svc_add_kw(msg: Message, state: FSMContext):
    await state.update_data(svc_kw=msg.text.strip())
    await msg.answer("⏱️ <b>Send durations (one per line):</b>\n\nExample:\n<code>1 Month\n3 Months\n6 Months</code>", parse_mode="HTML")
    await state.set_state(ServiceAddState.durations)

@dp.message(ServiceAddState.durations)
async def svc_add_dur(msg: Message, state: FSMContext):
    durs = [d.strip() for d in msg.text.strip().split("\n") if d.strip()]
    await state.update_data(svc_durs=durs)
    await msg.answer(
        f"💰 <b>Send prices for {len(durs)} durations (one per line):</b>\n\n"
        + "\n".join(f"  {d}:" for d in durs),
        parse_mode="HTML"
    )
    await state.set_state(ServiceAddState.prices)

@dp.message(ServiceAddState.prices)
async def svc_add_prices(msg: Message, state: FSMContext):
    data = await state.get_data()
    durs = data.get("svc_durs", [])
    price_lines = [p.strip() for p in msg.text.strip().split("\n") if p.strip()]
    if len(price_lines) != len(durs):
        await msg.answer(f"❌ Need exactly {len(durs)} prices.", parse_mode="HTML")
        return
    try:
        prices = [int(p) for p in price_lines]
    except Exception:
        await msg.answer("❌ Invalid prices. Enter numbers only.", parse_mode="HTML")
        return
    await state.update_data(svc_prices=prices)
    await msg.answer(
        f"📦 <b>Send stocks for {len(durs)} durations (one per line):</b>",
        parse_mode="HTML"
    )
    await state.set_state(ServiceAddState.stocks)

@dp.message(ServiceAddState.stocks)
async def svc_add_stocks(msg: Message, state: FSMContext):
    data = await state.get_data()
    durs   = data.get("svc_durs", [])
    prices = data.get("svc_prices", [])
    stock_lines = [s.strip() for s in msg.text.strip().split("\n") if s.strip()]
    if len(stock_lines) != len(durs):
        await msg.answer(f"❌ Need exactly {len(durs)} stock values.", parse_mode="HTML")
        return
    try:
        stocks = [int(s) for s in stock_lines]
    except Exception:
        await msg.answer("❌ Invalid stocks. Enter numbers only.", parse_mode="HTML")
        return

    # Build service key from name (lowercase, no spaces/special chars)
    svc_name = data.get("svc_name", "")
    svc_key  = re.sub(r"[^a-z0-9]", "", svc_name.lower())[:20]
    if not svc_key:
        svc_key = f"svc{random.randint(1000,9999)}"

    conn = db()
    c = conn.cursor()
    # Ensure unique key
    orig_key = svc_key
    i = 1
    while True:
        c.execute("SELECT service_key FROM services WHERE service_key=?", (svc_key,))
        if not c.fetchone():
            break
        svc_key = f"{orig_key}{i}"
        i += 1

    c.execute("INSERT INTO services (service_key, display_name, description, keywords, is_active) VALUES (?,?,?,?,1)",
              (svc_key, svc_name, data.get("svc_desc",""), data.get("svc_kw","")))
    for dur, price, stk in zip(durs, prices, stocks):
        c.execute("INSERT INTO service_prices (service_key, duration, price, stock) VALUES (?,?,?,?)",
                  (svc_key, dur, price, stk))
    conn.commit()
    conn.close()
    reload_products()

    await msg.answer(
        f"✅ <b>Service Added!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 Key: <code>{svc_key}</code>\n"
        f"📛 Name: {svc_name}\n"
        f"⏱️ Durations: {len(durs)}\n\n"
        f"Service is now live!",
        parse_mode="HTML"
    )
    await state.clear()

# ══════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════
@dp.callback_query()
async def handle_cb(cb: CallbackQuery, state: FSMContext):
    data = cb.data
    uid  = cb.from_user.id

    # ── Channel join check ─────────────────────────
    if data == "check_join":
        if await is_joined(uid):
            # Complete pending referral if any
            fsm_data = await state.get_data()
            rid = fsm_data.get("pending_referrer")
            if rid:
                await _process_referral(uid, rid)
                await state.update_data(pending_referrer=None)
            # Edit the join-button message into the full welcome screen
            wtext = get_setting("welcome_msg") or WELCOME_MSG
            try:
                await cb.message.edit_text(
                    wtext,
                    parse_mode="HTML",
                    reply_markup=welcome_kb(joined=True)
                )
            except Exception:
                await cb.message.answer(
                    wtext,
                    parse_mode="HTML",
                    reply_markup=welcome_kb(joined=True)
                )
            await cb.answer("✅ Welcome! Bot is now unlocked!", show_alert=True)
        else:
            await cb.answer("❌ Please join the channel first!", show_alert=True)
        return

    # ── Navigation ─────────────────────────────────
    if data == "buy_now":
        # Open the paginated services browse screen (new message or edit-in-place)
        text = browse_text(0)
        kb   = browse_kb(0)
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await cb.answer()
        return

    if data == "back":
        # Return to the welcome screen with action buttons — edit in-place
        wtext = get_setting("welcome_msg") or WELCOME_MSG
        try:
            await cb.message.edit_text(
                wtext,
                parse_mode="HTML",
                reply_markup=welcome_kb(joined=True)
            )
        except Exception:
            await cb.message.answer(
                wtext,
                parse_mode="HTML",
                reply_markup=welcome_kb(joined=True)
            )
        await cb.answer()
        return

    if data == "no":
        try:
            await cb.message.edit_text("❌ <b>Cancelled.</b> Type a service name to start!", parse_mode="HTML")
        except Exception:
            pass
        await cb.answer()
        return

    if data == "sold_out":
        await cb.answer("❌ Sold out! Choose another duration.", show_alert=True)
        return

    if data == "not_delivered":
        await cb.answer("⚠️ Contact admin to resolve.", show_alert=True)
        return

    if data == "contact":
        await cb.message.answer(
            "📞 <b>Contact Support</b>\n━━━━━━━━━━━━━━━━━━━━\n\nMessage: @HIND_DEALS\n\n📢 Reviews: https://t.me/HIND_DEALS_REVIEWS",
            parse_mode="HTML", reply_markup=main_kb()
        )
        await cb.answer()
        return

    if data == "my_orders":
        orders = get_user_orders(uid)
        if not orders:
            await cb.message.answer("📭 <b>No orders found</b>", parse_mode="HTML")
        else:
            text = "📦 <b>YOUR ORDERS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for o in orders:
                em = "✅" if o[4]=="delivered" else ("⏳" if o[4]=="pending" else "❌")
                text += f"{em} <code>{o[0]}</code> — {o[1]} ({o[2]}) — ₹{o[3]}\n"
            await cb.message.answer(text, parse_mode="HTML")
        await cb.answer()
        return

    if data == "wallet_view":
        await _show_wallet(cb, uid)
        return

    if data == "ref_view":
        await _show_referral(cb, uid)
        return

    # ── BROWSE SCREEN PAGINATION ───────────────────
    if data == "startpg_noop":
        # Page indicator button — acknowledge tap silently, no action
        await cb.answer()
        return

    if data.startswith("startpg_"):
        # Navigate between pages — always edit-in-place (single message)
        try:
            page = int(data.split("_")[1])
        except (IndexError, ValueError):
            page = 0
        text = browse_text(page)
        kb   = browse_kb(page)
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await cb.answer()
        return

    if data.startswith("browse_"):
        # User tapped a service tile from the browse grid
        service_key = data[7:]
        if not is_admin(uid) and not await is_joined(uid):
            await cb.answer("❌ Join the channel first!", show_alert=True)
            return
        if service_key not in PRODUCTS:
            await cb.answer("⚠️ Service not available right now.", show_alert=True)
            return
        # show_product_menu sends a NEW message (duration picker)
        await show_product_menu(cb, service_key)
        return

    # ── Duration selection ─────────────────────────
    if data.startswith("dur_"):
        if not await is_joined(uid):
            await cb.answer("❌ Join channel first!", show_alert=True)
            return
        parts       = data.split("_", 3)
        product_key = parts[1]
        duration    = parts[2]
        amount      = int(parts[3])

        # Payment method screen — wallet AND QR always offered
        bal, _unlocked = get_wallet(uid)
        text = (f"🛒 <b>YOUR SELECTION</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📺 {PRODUCTS[product_key]['display_name']}\n"
                f"⏱️ {duration}\n"
                f"💰 Amount: <b>₹{amount}</b>\n"
                f"💚 Wallet Balance: <b>₹{bal:.2f}</b>\n\n"
                f"👇 <b>Payment method choose kijiye:</b>")
        try:
            await cb.message.edit_text(text, parse_mode="HTML",
                                       reply_markup=payment_method_kb(product_key, duration, amount, bal))
        except Exception:
            await cb.message.answer(text, parse_mode="HTML",
                                    reply_markup=payment_method_kb(product_key, duration, amount, bal))
        await cb.answer()
        return


    # ══ PAYMENT GATEWAY — USER ═════════════════════
    if data == "gwadd":
        if not gw_enabled():
            await cb.answer("⚡ Auto payment abhi band hai. 'qr 100' use kijiye.", show_alert=True)
            return
        await state.set_state(GatewayState.waiting_amount)
        await state.update_data(gw_purpose="deposit")
        await cb.message.answer(
            f"⚡ <b>INSTANT WALLET RECHARGE</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Kitna amount add karna hai? Sirf number bhejiye.\n"
            f"Minimum: <b>₹{gw_min()}</b>\n\n"
            f"Payment hote hi wallet me <b>automatic</b> add ho jayega.",
            parse_mode="HTML"
        )
        await cb.answer()
        return

    if data.startswith("gwbuy_"):
        parts       = data.split("_", 3)
        product_key = parts[1]
        duration    = parts[2]
        amount      = int(parts[3])
        if not gw_enabled():
            await cb.answer("⚡ Auto payment abhi band hai — QR use kijiye.", show_alert=True)
            return
        shop_oid = generate_order_id(uid)
        save_order(shop_oid, uid, product_key, duration, amount)
        gw_oid = gw_new_id(uid)
        ok, url, err = await gw_create_order(amount, gw_oid, remark=f"order {shop_oid}")
        if not ok:
            await cb.answer("⚠️ Gateway abhi respond nahi kar raha — QR se pay kijiye.", show_alert=True)
            await cb.message.answer(f"⚠️ <b>Online payment fail:</b> {err}", parse_mode="HTML")
            return
        gw_save(gw_oid, uid, amount, f"order:{shop_oid}", "", url)
        await cb.message.answer(
            f"⚡ <b>ONLINE PAYMENT</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📺 {PRODUCTS.get(product_key,{}).get('display_name', product_key)}\n"
            f"⏱️ {duration}\n💰 <b>₹{amount}</b>\n\n"
            f"1️⃣ PAY NOW dabaiye\n2️⃣ UPI se pay kijiye\n"
            f"3️⃣ Payment hote hi order <b>automatic</b> confirm ho jayega\n\n"
            f"🆔 Order: <code>{shop_oid}</code>",
            parse_mode="HTML",
            reply_markup=gw_pay_kb(gw_oid, url)
        )
        await cb.answer()
        return

    if data.startswith("gwchk_"):
        gw_oid = data.split("_", 1)[1]
        row = gw_get(gw_oid)
        if not row:
            await cb.answer("❌ Payment record nahi mila.", show_alert=True)
            return
        if row[7]:
            await cb.answer("✅ Ye payment already confirm ho chuka hai.", show_alert=True)
            return
        state_, msg_ = await gw_check_status(gw_oid)
        if state_ == "success":
            await gw_settle(gw_oid)
            await cb.answer("✅ Payment mil gaya!", show_alert=True)
            try:
                await cb.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        elif state_ == "failed":
            gw_set_status(gw_oid, "failed")
            await cb.answer("❌ Payment fail/cancel ho gaya. Dobara try kijiye.", show_alert=True)
        else:
            await cb.answer("⏳ Abhi payment nahi mila. Pay karke 10-20 sec baad check kijiye.", show_alert=True)
        return

    if data.startswith("gwcan_"):
        gw_oid = data.split("_", 1)[1]
        row = gw_get(gw_oid)
        if row and not row[7]:
            gw_set_status(gw_oid, "cancelled")
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await cb.answer("❌ Cancel kar diya.")
        return

    # ══ PAYMENT GATEWAY — ADMIN ════════════════════
    if data == "admin_gateway":
        if not is_admin(uid):
            await cb.answer("⛔ Unauthorized", show_alert=True)
            return
        ok_cnt, ok_sum, pend = gw_stats()
        tok = gw_token()
        masked = (tok[:4] + "•" * 6 + tok[-4:]) if len(tok) > 8 else ("set" if tok else "❌ not set")
        await cb.message.edit_text(
            f"⚡ <b>PAYMENT GATEWAY</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Status: <b>{'🟢 ON' if gw_enabled() else '🔴 OFF'}</b>\n"
            f"Panel: <code>{gw_base()}</code>\n"
            f"Token: <code>{masked}</code>\n"
            f"Min amount: ₹{gw_min()}\n\n"
            f"✅ Successful: {ok_cnt} — ₹{ok_sum:.0f}\n"
            f"⏳ Pending: {pend}\n\n"
            f"<i>Payment aate hi wallet/order auto confirm ho jata hai (har "
            f"{GATEWAY_POLL_SECONDS}s auto-check).</i>",
            parse_mode="HTML",
            reply_markup=gw_admin_kb()
        )
        await cb.answer()
        return

    if data.startswith("gwadm_"):
        if not is_admin(uid):
            await cb.answer("⛔ Unauthorized", show_alert=True)
            return
        act = data.split("_", 1)[1]
        if act == "toggle":
            if not gw_token():
                await cb.answer("🔑 Pehle API token set kijiye.", show_alert=True)
                return
            set_setting("gw_enabled", "0" if get_setting("gw_enabled", "0") == "1" else "1")
            await cb.answer("✅ Updated")
            try:
                await cb.message.edit_reply_markup(reply_markup=gw_admin_kb())
            except Exception:
                pass
            return
        if act == "token":
            await state.set_state(GatewayState.waiting_token)
            await cb.message.answer(
                "🔑 <b>Gateway API token bhejiye</b>\n\n"
                "iPey.shop panel → login → <b>API / Developer</b> section → "
                "<code>user_token</code> copy karke yahan paste kijiye.",
                parse_mode="HTML")
            await cb.answer(); return
        if act == "base":
            await state.set_state(GatewayState.waiting_base)
            await cb.message.answer(
                f"🌐 <b>Panel URL bhejiye</b>\n\nAbhi: <code>{gw_base()}</code>\n"
                f"Example: <code>https://ipey.shop</code>", parse_mode="HTML")
            await cb.answer(); return
        if act == "min":
            await state.set_state(GatewayState.waiting_min)
            await cb.message.answer("💵 <b>Minimum auto-deposit amount bhejiye (number):</b>", parse_mode="HTML")
            await cb.answer(); return
        if act == "test":
            await cb.answer("🧪 Testing…")
            test_id = gw_new_id(uid)
            ok, url, err = await gw_create_order(gw_min(), test_id, remark="test")
            if ok:
                gw_save(test_id, uid, gw_min(), "deposit", "", url)
                await cb.message.answer(
                    f"✅ <b>Gateway working!</b>\n\nTest link bana:\n{url}\n\n"
                    f"Pay karoge to ₹{gw_min()} wallet me auto add ho jayega.",
                    parse_mode="HTML")
            else:
                await cb.message.answer(
                    f"❌ <b>Gateway error</b>\n\n<code>{err}</code>\n\n"
                    f"Token / panel URL check kijiye.", parse_mode="HTML")
            return
        if act == "pending":
            rows = gw_pending_rows()[:15]
            txt = "📋 <b>PENDING ONLINE PAYMENTS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            if not rows:
                txt += "Koi pending payment nahi."
            for r in rows:
                txt += f"🆔 <code>{r[0]}</code>\n👤 {r[1]} — ₹{r[2]:.0f} — {r[3]}\n🕒 {r[8]}\n\n"
            await cb.message.answer(txt, parse_mode="HTML")
            await cb.answer(); return
        await cb.answer()
        return

    if data == "wallet_empty":
        await cb.answer("💚 Wallet khali hai. 'qr 100' type karke money add kijiye.", show_alert=True)
        return

    # ── Wallet USE ─────────────────────────────────
    if data.startswith("wuse_"):
        parts       = data.split("_", 3)
        product_key = parts[1]
        duration    = parts[2]
        amount      = int(parts[3])
        bal, _unlocked = get_wallet(uid)
        use_amt     = min(bal, amount)
        remaining   = int(amount - use_amt)
        if use_amt <= 0:
            await cb.answer("💚 Wallet balance ₹0 — QR se pay kijiye.", show_alert=True)
            return

        if remaining == 0:
            # Full wallet payment
            oid = generate_order_id(uid)
            save_order(oid, uid, product_key, duration, amount, wallet_used=use_amt)
            debit_wallet(uid, use_amt, f"Purchase {oid} — {PRODUCTS.get(product_key,{}).get('display_name','')}")
            update_order_status(oid, "approved")
            add_order_spent(uid, amount)
            decrement_stock(product_key, duration)

            # Notify admins for delivery
            conn = db()
            c = conn.cursor()
            c.execute("SELECT user_id FROM admins")
            admins_list = [r[0] for r in c.fetchall()]
            conn.close()
            for adm in admins_list:
                try:
                    await bot.send_message(
                        adm,
                        f"💚 <b>WALLET PAYMENT — DELIVERY REQUIRED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"Order: <code>{oid}</code>\n"
                        f"User: <code>{uid}</code>\n"
                        f"Product: {PRODUCTS.get(product_key,{}).get('display_name','')}\n"
                        f"Duration: {duration}\n"
                        f"Amount: ₹{amount} (paid via wallet)\n\n"
                        f"No screenshot required — wallet payment confirmed.",
                        parse_mode="HTML",
                        reply_markup=deliver_kb(oid, uid, amount)
                    )
                except Exception:
                    pass

            await cb.message.edit_text(
                f"💚 <b>Wallet Payment Successful!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Order ID: <code>{oid}</code>\n"
                f"₹{use_amt:.0f} deducted from wallet.\n\n"
                f"Admin will deliver your service shortly!",
                parse_mode="HTML"
            )
        else:
            # Partial wallet payment — generate QR for remaining
            oid = generate_order_id(uid)
            save_order(oid, uid, product_key, duration, amount, wallet_used=use_amt)
            debit_wallet(uid, use_amt, f"Partial wallet for {oid}")
            try:
                await cb.message.delete()
            except Exception:
                pass
            await send_payment_qr(
                cb.message,
                remaining,
                (f"💳 <b>PARTIAL WALLET PAYMENT</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                         f"💚 Wallet deducted: ₹{use_amt:.0f}\n"
                         f"💳 Pay via UPI: ₹{remaining}\n\n"
                         f"UPI: <code>{UPI_ID}</code>\n\n"
                         f"1️⃣ Scan QR  2️⃣ Pay ₹{remaining}  3️⃣ Click PAID\n\n"
                         f"Order ID: <code>{oid}</code>"),
                reply_markup=paid_kb(product_key, duration, remaining, oid)
            )
        await cb.answer()
        return

    # ── Wallet SKIP ────────────────────────────────
    if data.startswith("wskip_"):
        parts       = data.split("_", 3)
        product_key = parts[1]
        duration    = parts[2]
        amount      = int(parts[3])
        await cb.message.edit_text(
            f"🛒 <b>YOUR SELECTION</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📺 {PRODUCTS[product_key]['display_name']}\n⏱️ {duration}\n💰 ₹{amount}\n\nProceed to payment?",
            parse_mode="HTML",
            reply_markup=confirm_kb(product_key, duration, amount)
        )
        await cb.answer()
        return

    # ── Confirm YES ────────────────────────────────
    if data.startswith("yes_"):
        parts       = data.split("_", 3)
        product_key = parts[1]
        duration    = parts[2]
        amount      = int(parts[3])
        oid         = generate_order_id(uid)
        save_order(oid, uid, product_key, duration, amount)
        try:
            await cb.message.delete()
        except Exception:
            pass
        await send_payment_qr(
            cb.message,
            amount,
            (f"💳 <b>PAYMENT DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                     f"UPI: <code>{UPI_ID}</code>\n"
                     f"Amount: ₹{amount}\n\n"
                     f"📌 Steps:\n1️⃣ Scan QR\n2️⃣ Pay ₹{amount}\n3️⃣ Click 'I HAVE PAID'\n\n"
                     f"⏱️ Pay within 10 minutes\n\n"
                     f"Order ID: <code>{oid}</code>"),
            reply_markup=paid_kb(product_key, duration, amount, oid)
        )
        await cb.answer()
        return

    # ── I Have Paid ────────────────────────────────
    if data.startswith("paid_"):
        parts       = data.split("_", 4)
        product_key = parts[1]
        duration    = parts[2]
        amount      = int(parts[3])
        oid         = parts[4]
        await state.update_data(oid=oid, product_key=product_key, duration=duration, amount=amount)
        await cb.message.edit_caption(
            caption=(f"📸 <b>SEND SCREENSHOT</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                     f"Send your payment screenshot now.\n\n"
                     f"Order ID: <code>{oid}</code>\nAmount: ₹{amount}"),
            parse_mode="HTML"
        )
        await state.set_state(OrderState.waiting_for_screenshot)
        await cb.answer()
        return

    # ── Rating ─────────────────────────────────────
    if data.startswith("rate_"):
        parts  = data.split("_")
        oid    = parts[1]
        rating = int(parts[2])
        await state.update_data(oid=oid, rating=rating)
        await cb.message.edit_text(
            f"⭐ <b>Rating: {'⭐'*rating}</b>\n\n📝 Write a review (or type /skip):",
            parse_mode="HTML"
        )
        await state.set_state(OrderState.waiting_for_review)
        await cb.answer()
        return

    if data.startswith("skip_"):
        await cb.message.edit_text("✅ <b>Thank you for your order! Come back soon!</b> 🎉", parse_mode="HTML")
        await cb.answer()
        return

    # ── Deposit I Have Paid ────────────────────────
    if data.startswith("dep_paid_"):
        parts  = data.split("_", 3)
        dep_id = parts[2]
        amount = int(parts[3])
        await state.update_data(dep_id=dep_id, dep_amount=amount)
        try:
            await cb.message.edit_caption(
                caption=(
                    f"📸 <b>DEPOSIT SCREENSHOT BHEJIYE</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Payment ka screenshot ab bhejiye.\n\n"
                    f"💰 Amount: ₹{amount}\n"
                    f"🆔 Deposit ID: <code>{dep_id}</code>"
                ),
                parse_mode="HTML"
            )
        except Exception:
            await cb.message.answer(
                f"📸 <b>DEPOSIT SCREENSHOT BHEJIYE</b>\n\nPayment ka screenshot bhejiye.\n\n💰 Amount: ₹{amount}",
                parse_mode="HTML"
            )
        await state.set_state(DepositState.waiting_for_screenshot)
        await cb.answer()
        return

    # ══════════════════════════════════════════════
    #  ADMIN-ONLY CALLBACKS (role-gated)
    # ══════════════════════════════════════════════
    if not is_admin(uid):
        await cb.answer("⛔ Unauthorized", show_alert=True)
        return

    # ── Admin navigation ───────────────────────────
    if data == "admin_back":
        await _send_admin_panel(cb)
        return

    # ── Pending orders ─────────────────────────────
    if data == "admin_pending":
        pending = get_pending()
        if not pending:
            await cb.message.answer("📭 <b>No pending orders</b>", parse_mode="HTML")
        else:
            text = "📦 <b>PENDING ORDERS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for p in pending:
                text += f"🔹 <code>{p[0]}</code> — {p[2]} ({p[3]}) — ₹{p[4]}\n"
            await cb.message.answer(text, parse_mode="HTML")
        await cb.answer()
        return

    # ── Analytics ──────────────────────────────────
    if data == "admin_analytics":
        u, t, p, d, r, refs, wused = get_stats()
        d_cnt, d_rev = get_daily_sales()
        text = (f"📈 <b>FULL ANALYTICS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 Total Users: {u}\n"
                f"📦 Total Orders: {t}\n"
                f"⏳ Pending: {p}\n"
                f"✅ Completed: {d}\n"
                f"💰 Total Revenue: ₹{r}\n"
                f"💚 Wallet Used: ₹{wused:.0f}\n"
                f"🤝 Total Referrals: {refs}\n\n"
                f"📅 <b>TODAY</b>\n"
                f"✅ Sales: {d_cnt}  |  Revenue: ₹{d_rev}")
        await cb.message.answer(text, parse_mode="HTML")
        await cb.answer()
        return

    # ── Top services ───────────────────────────────
    if data == "admin_top":
        top = get_top_services()
        if not top:
            await cb.message.answer("📊 <b>No data yet</b>", parse_mode="HTML")
        else:
            text = "🏆 <b>TOP SELLING SERVICES</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for i, (nm, cnt, rev) in enumerate(top, 1):
                text += f"{i}. {nm} — {cnt} orders — ₹{rev}\n"
            await cb.message.answer(text, parse_mode="HTML")
        await cb.answer()
        return

    # ── Top referrers ──────────────────────────────
    if data == "admin_referrers":
        rows = get_top_referrers()
        if not rows:
            await cb.message.answer("📊 <b>No referrals yet</b>", parse_mode="HTML")
        else:
            text = "👑 <b>TOP REFERRERS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for i, (uid_, uname, cnt) in enumerate(rows, 1):
                text += f"{i}. @{uname or uid_} — {cnt} referrals\n"
            await cb.message.answer(text, parse_mode="HTML")
        await cb.answer()
        return

    # ── User Kundali ───────────────────────────────
    if data == "admin_kundali":
        await cb.message.answer("👤 <b>Send user ID:</b>\n\nExample: <code>8598847348</code>", parse_mode="HTML")
        await state.set_state(AdminState.waiting_for_user_id)
        await cb.answer()
        return

    # ── Ban/Unban ──────────────────────────────────
    if data == "admin_ban":
        await cb.message.answer("🚫 <b>Send user ID to ban:</b>", parse_mode="HTML")
        await state.set_state(AdminState.waiting_for_user_id)
        await cb.answer()
        return

    if data.startswith("ban_now_"):
        target_uid = int(data.split("_")[2])
        await state.update_data(ban_user_id=target_uid)
        await cb.message.answer("📝 <b>Send ban reason:</b>\n\nExample: Fraud, Spam, etc.", parse_mode="HTML")
        await state.set_state(AdminState.waiting_for_ban_reason)
        await cb.answer()
        return

    if data.startswith("unban_"):
        target_uid = int(data.split("_")[1])
        unban_user(target_uid)
        try:
            await cb.message.edit_text(cb.message.text + "\n\n✅ <b>USER UNBANNED</b>", parse_mode="HTML")
        except Exception:
            await cb.message.answer(f"✅ <b>User {target_uid} UNBANNED!</b>", parse_mode="HTML")
        try:
            await bot.send_message(target_uid, "✅ <b>You have been UNBANNED!</b>\n\nType /start to continue.", parse_mode="HTML")
        except Exception:
            pass
        await cb.answer("✅ Unbanned!", show_alert=True)
        return

    if data.startswith("contact_"):
        target_uid = int(data.split("_")[1])
        await cb.message.answer(f"📞 User ID: <code>{target_uid}</code>\n\nMessage them directly on Telegram.", parse_mode="HTML")
        await cb.answer()
        return

    # ── Broadcast ──────────────────────────────────
    if data == "admin_broadcast":
        await cb.message.answer(
            "📢 <b>BROADCAST</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 Pehle audience choose kijiye:",
            parse_mode="HTML", reply_markup=broadcast_audience_kb()
        )
        await cb.answer()
        return

    if data.startswith("bcaud_"):
        audience = data.split("_", 1)[1]
        targets  = get_broadcast_targets(audience)
        await state.clear()
        await state.update_data(bc_audience=audience)
        await cb.message.answer(
            f"📢 <b>{AUDIENCE_LABELS.get(audience, audience)}</b>\n"
            f"👥 Recipients: <b>{len(targets)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Ab wo message bhejiye jo broadcast karna hai.\n"
            f"📝 Text, 🖼️ photo, 🎥 video, 📄 file, 🔊 voice — kuch bhi chalega.\n\n"
            f"❌ Rokne ke liye /cancel",
            parse_mode="HTML"
        )
        await state.set_state(BroadcastState.waiting_content)
        await cb.answer()
        return

    if data == "bc_cancel":
        await state.clear()
        await cb.message.edit_text("❌ <b>Broadcast cancelled.</b>", parse_mode="HTML")
        await cb.answer()
        return

    if data == "bc_send":
        bdata    = await state.get_data()
        chat_id  = bdata.get("bc_chat_id")
        msg_id   = bdata.get("bc_msg_id")
        audience = bdata.get("bc_audience", "all")
        await state.clear()
        if not chat_id or not msg_id:
            await cb.answer("⚠️ Broadcast content missing. Dobara try kijiye.", show_alert=True)
            return
        targets = get_broadcast_targets(audience)
        await cb.answer("🚀 Sending…")
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await run_broadcast(cb.message, chat_id, msg_id, targets, audience)
        return

    # ── Wallet management (give / take balance) ────
    if data == "admin_wallet":
        if not can_manage_wallet(uid):
            await cb.answer("⛔ Aapko wallet permission nahi hai.", show_alert=True)
            return
        conn = db()
        c = conn.cursor()
        c.execute("SELECT COALESCE(SUM(wallet_balance),0), COUNT(*) FROM users WHERE wallet_balance > 0")
        total, holders = c.fetchone()
        conn.close()
        await cb.message.answer(
            f"💳 <b>WALLET MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Total user balance: <b>₹{total:.2f}</b>\n"
            f"👥 Wallet holders: <b>{holders}</b>\n\n"
            f"Kisi bhi user ki ID par balance add ya deduct kijiye.",
            parse_mode="HTML", reply_markup=wallet_mgmt_kb()
        )
        await cb.answer()
        return

    if data in ("wadm_add", "wadm_deduct", "wadm_check"):
        if not can_manage_wallet(uid):
            await cb.answer("⛔ Aapko wallet permission nahi hai.", show_alert=True)
            return
        if data == "wadm_add":
            await cb.message.answer(
                "➕ <b>ADD BALANCE</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                "Format: <code>USER_ID AMOUNT reason</code>\n"
                "Example: <code>123456789 100 diwali bonus</code>", parse_mode="HTML")
            await state.set_state(WalletAdminState.waiting_add)
        elif data == "wadm_deduct":
            await cb.message.answer(
                "➖ <b>DEDUCT BALANCE</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                "Format: <code>USER_ID AMOUNT reason</code>\n"
                "Example: <code>123456789 50 refund reverse</code>", parse_mode="HTML")
            await state.set_state(WalletAdminState.waiting_deduct)
        else:
            await cb.message.answer("🔍 <b>User ID bhejiye:</b>", parse_mode="HTML")
            await state.set_state(WalletAdminState.waiting_check)
        await cb.answer()
        return

    if data.startswith("wquick_"):
        if not can_manage_wallet(uid):
            await cb.answer("⛔ No permission", show_alert=True)
            return
        _, action, target_id = data.split("_", 2)
        if action == "add":
            await cb.message.answer(f"➕ Send: <code>{target_id} AMOUNT reason</code>", parse_mode="HTML")
            await state.set_state(WalletAdminState.waiting_add)
        else:
            await cb.message.answer(f"➖ Send: <code>{target_id} AMOUNT reason</code>", parse_mode="HTML")
            await state.set_state(WalletAdminState.waiting_deduct)
        await cb.answer()
        return

    if data == "wadm_top":
        if not can_manage_wallet(uid):
            await cb.answer("⛔ No permission", show_alert=True)
            return
        conn = db()
        c = conn.cursor()
        c.execute("SELECT user_id, username, wallet_balance FROM users WHERE wallet_balance>0 ORDER BY wallet_balance DESC LIMIT 15")
        rows = c.fetchall()
        conn.close()
        text = "🏆 <b>TOP WALLETS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if rows:
            for i, (u_, un, b_) in enumerate(rows, 1):
                text += f"{i}. <code>{u_}</code> @{un or 'N/A'} — ₹{b_:.2f}\n"
        else:
            text += "Koi wallet balance nahi hai."
        await cb.message.answer(text, parse_mode="HTML")
        await cb.answer()
        return

    if data == "wadm_logs":
        if not can_manage_wallet(uid):
            await cb.answer("⛔ No permission", show_alert=True)
            return
        conn = db()
        c = conn.cursor()
        c.execute("SELECT user_id, amount, type, reason, date FROM wallet_logs ORDER BY id DESC LIMIT 15")
        rows = c.fetchall()
        conn.close()
        text = "🧾 <b>RECENT WALLET LOGS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if rows:
            for u_, amt, typ, reason, date in rows:
                em = "➕" if typ == "credit" else "➖"
                text += f"{em} <code>{u_}</code> ₹{amt:.2f} — {reason[:25]} ({date[5:16]})\n"
        else:
            text += "No wallet activity yet."
        await cb.message.answer(text, parse_mode="HTML")
        await cb.answer()
        return

    # ── Owner: wallet permission give/take ─────────
    if data == "admins_perms":
        if uid != OWNER_ID:
            await cb.answer("⛔ Only owner", show_alert=True)
            return
        await cb.message.answer(
            "💳 <b>WALLET PERMISSIONS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "Tap karke kisi admin ko wallet give/take ki power do ya wapas lo.",
            parse_mode="HTML", reply_markup=wallet_perm_kb()
        )
        await cb.answer()
        return

    if data == "wperm_noop":
        await cb.answer("Owner ke paas hamesha permission hai.")
        return

    if data.startswith("wperm_"):
        if uid != OWNER_ID:
            await cb.answer("⛔ Only owner", show_alert=True)
            return
        try:
            target_id = int(data.split("_", 1)[1])
        except ValueError:
            await cb.answer()
            return
        current = can_manage_wallet(target_id)
        set_wallet_perm(target_id, not current)
        try:
            await cb.message.edit_reply_markup(reply_markup=wallet_perm_kb())
        except Exception:
            pass
        try:
            await bot.send_message(
                target_id,
                ("💳 <b>Wallet permission mil gayi!</b>\n\nAb aap /admin → WALLET MGMT se users ka balance add/deduct kar sakte ho."
                 if not current else
                 "🚫 <b>Wallet permission hata di gayi hai.</b>"),
                parse_mode="HTML"
            )
        except Exception:
            pass
        await cb.answer("✅ Permission updated", show_alert=True)
        return

    # ── Stock management ───────────────────────────
    if data == "admin_stock":
        await state.update_data(stock_page=0)
        await cb.message.answer("📦 <b>Select product to manage stock:</b>", parse_mode="HTML", reply_markup=stock_kb(0))
        await cb.answer()
        return

    if data.startswith("stkpg_"):
        page = int(data.split("_")[1])
        try:
            await cb.message.edit_text("📦 <b>Select product to manage stock:</b>", parse_mode="HTML", reply_markup=stock_kb(page))
        except Exception:
            pass
        await cb.answer()
        return

    if data.startswith("stk_"):
        product_key = data[4:]
        p = PRODUCTS.get(product_key)
        if not p:
            await cb.answer("Service not found", show_alert=True)
            return
        await state.update_data(stock_product_key=product_key)
        text = f"📦 <b>{p['display_name']} — Stock</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for d, s in p["stock"].items():
            text += f"• {d}: {s} units\n"
        text += "\n━━━━━━━━━━━━━━━━━━━━\nFormat: <code>duration|new_stock</code>\nExample: <code>1 Month|50</code>"
        await cb.message.answer(text, parse_mode="HTML")
        await state.set_state(AdminState.waiting_for_stock_update)
        await cb.answer()
        return

    # ── Services management ────────────────────────
    if data == "admin_services":
        if not can_manage_services(uid):
            await cb.answer("⛔ No permission", show_alert=True)
            return
        await cb.message.answer("🛠️ <b>SERVICES MANAGEMENT</b>\n\n✅ = Active  🚫 = Disabled", parse_mode="HTML", reply_markup=services_mgmt_kb(0))
        await cb.answer()
        return

    if data.startswith("svcpg_"):
        page = int(data.split("_")[1])
        try:
            await cb.message.edit_reply_markup(reply_markup=services_mgmt_kb(page))
        except Exception:
            pass
        await cb.answer()
        return

    if data == "svc_add":
        if not can_manage_services(uid):
            await cb.answer("⛔ No permission", show_alert=True)
            return
        await cb.message.answer("📛 <b>Enter service name:</b>\n\nExample: <code>Cooler Premium</code>", parse_mode="HTML")
        await state.set_state(ServiceAddState.name)
        await cb.answer()
        return

    if data.startswith("svc_"):
        svc_key = data[4:]
        conn = db()
        c = conn.cursor()
        c.execute("SELECT display_name, description, keywords, is_active FROM services WHERE service_key=?", (svc_key,))
        row = c.fetchone()
        c.execute("SELECT duration, price, stock FROM service_prices WHERE service_key=? ORDER BY price", (svc_key,))
        prices_rows = c.fetchall()
        conn.close()
        if not row:
            await cb.answer("Service not found", show_alert=True)
            return
        dname, desc, kw, active = row
        text  = f"🛠️ <b>{dname}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"📝 {desc[:100]}…\n🔑 Keywords: {kw}\n\n"
        text += "💰 Plans:\n"
        for dur, price, stk in prices_rows:
            text += f"• {dur}: ₹{price} ({stk} stock)\n"
        text += f"\n🔘 Status: {'✅ Active' if active else '🚫 Disabled'}"
        await cb.message.answer(text, parse_mode="HTML", reply_markup=service_detail_kb(svc_key, active))
        await cb.answer()
        return

    if data.startswith("svctoggle_"):
        svc_key = data[10:]
        conn = db()
        c = conn.cursor()
        c.execute("SELECT is_active FROM services WHERE service_key=?", (svc_key,))
        row = c.fetchone()
        new_active = 0
        if row:
            new_active = 0 if row[0] else 1
            c.execute("UPDATE services SET is_active=? WHERE service_key=?", (new_active, svc_key))
            conn.commit()
        conn.close()
        reload_products()
        await cb.answer(f"{'✅ Enabled' if new_active else '🚫 Disabled'} service.", show_alert=True)
        # Refresh view
        conn2 = db()
        c2 = conn2.cursor()
        c2.execute("SELECT display_name, description, keywords, is_active FROM services WHERE service_key=?", (svc_key,))
        row2 = c2.fetchone()
        conn2.close()
        if row2:
            try:
                await cb.message.edit_reply_markup(reply_markup=service_detail_kb(svc_key, row2[3]))
            except Exception:
                pass
        return

    if data.startswith("svcdel_"):
        svc_key = data[7:]
        conn = db()
        c = conn.cursor()
        c.execute("DELETE FROM service_prices WHERE service_key=?", (svc_key,))
        c.execute("DELETE FROM services WHERE service_key=?", (svc_key,))
        conn.commit()
        conn.close()
        reload_products()
        await cb.message.edit_text("🗑️ <b>Service deleted.</b>", parse_mode="HTML", reply_markup=services_mgmt_kb())
        await cb.answer("Deleted!", show_alert=True)
        return

    if data.startswith("svcedit_"):
        parts   = data.split("_", 2)
        field   = parts[1]
        svc_key = parts[2]
        await state.update_data(edit_svc_key=svc_key, edit_svc_field=field)
        prompts = {
            "name":   "📛 Send new service name:",
            "desc":   "📝 Send new description (HTML tags supported like b, i):",
            "kw":     "🔑 Send new keywords (comma-separated):",
            "prices": "💰 Send new prices — format:\n<code>duration|price</code> one per line\nExample:\n<code>1 Month|49\n3 Months|99</code>",
            "stock":  "📦 Send new stock — format:\n<code>duration|stock</code> one per line",
        }
        await cb.message.answer(prompts.get(field, "Send new value:"), parse_mode="HTML")
        await state.set_state(ServiceEditState.new_value)
        await cb.answer()
        return

    # ── Admin management ───────────────────────────
    if data == "admin_admins":
        if uid != OWNER_ID:
            await cb.answer("⛔ Only owner can manage admins.", show_alert=True)
            return
        await cb.message.answer("👮 <b>ADMIN MANAGEMENT</b>\n\n⚠️ Only owner can add/remove admins.", parse_mode="HTML", reply_markup=admin_mgmt_kb())
        await cb.answer()
        return

    if data == "admins_list":
        rows = get_all_admins()
        text = "👮 <b>ADMIN LIST</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for auid, role, date in rows:
            text += f"🔹 <code>{auid}</code> — <b>{role}</b>\n"
        await cb.message.answer(text, parse_mode="HTML")
        await cb.answer()
        return

    if data == "admins_add":
        if uid != OWNER_ID:
            await cb.answer("⛔ Only owner", show_alert=True)
            return
        await cb.message.answer("👤 <b>Send user ID to add as admin:</b>", parse_mode="HTML")
        await state.set_state(AdminManageState.waiting_add_id)
        await cb.answer()
        return

    if data == "admins_remove":
        if uid != OWNER_ID:
            await cb.answer("⛔ Only owner", show_alert=True)
            return
        await cb.message.answer("👤 <b>Send admin user ID to remove:</b>", parse_mode="HTML")
        await state.set_state(AdminManageState.waiting_remove)
        await cb.answer()
        return

    if data.startswith("setrole_"):
        if uid != OWNER_ID:
            await cb.answer("⛔ Only owner", show_alert=True)
            return
        _, target_id_str, role = data.split("_", 2)
        target_id = int(target_id_str)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = db()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO admins (user_id, role, added_by, added_date) VALUES (?,?,?,?)",
                  (target_id, role, uid, now))
        conn.commit()
        conn.close()
        await cb.message.answer(f"✅ <b>Admin added!</b>\n\nID: <code>{target_id}</code>\nRole: <b>{role}</b>", parse_mode="HTML")
        try:
            await bot.send_message(target_id, f"👮 <b>You have been added as admin!</b>\n\nRole: <b>{role}</b>\n\nUse /admin to access admin panel.", parse_mode="HTML")
        except Exception:
            pass
        await cb.answer("Admin added!", show_alert=True)
        return

    # ── Approve / Reject ───────────────────────────
    if data.startswith("approve_"):
        parts    = data.split("_")
        oid      = parts[1]
        amount   = int(parts[2])
        uid_user = int(parts[3])
        update_order_status(oid, "approved")
        add_order_spent(uid_user, amount)
        decrement_stock_for_order(oid)
        msg_text = (f"✅ <b>PAYMENT APPROVED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"• Order ID: <code>{oid}</code>\n"
                    f"• Buyer ID: <code>{uid_user}</code>\n"
                    f"• Amount: <b>₹{amount}</b>\n"
                    f"• Approved by: <code>{uid}</code>\n\n"
                    f"➡️ Account details bhejne ke baad DELIVERED dabaiye.")
        try:
            await cb.message.edit_caption(caption=msg_text, parse_mode="HTML")
        except Exception:
            await cb.message.edit_text(msg_text, parse_mode="HTML")

        # Send confirmation to all admins for delivery
        conn = db()
        c = conn.cursor()
        c.execute("SELECT user_id FROM admins")
        admins_list = [r[0] for r in c.fetchall()]
        conn.close()
        for adm in admins_list:
            try:
                await bot.send_message(
                    adm,
                    f"🔔 <b>DELIVERY REQUIRED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Order: <code>{oid}</code>\nUser: <code>{uid_user}</code>\nAmount: ₹{amount}\n\n"
                    f"Send account details to user.",
                    parse_mode="HTML",
                    reply_markup=deliver_kb(oid, uid_user, amount)
                )
            except Exception:
                pass

        await bot.send_message(
            uid_user,
            f"{PAYMENT_CONFIRMED_MSG}\n\n🆔 Order: <code>{oid}</code>",
            parse_mode="HTML"
        )
        await cb.answer()
        return

    if data.startswith("reject_"):
        parts    = data.split("_")
        oid      = parts[1]
        uid_user = int(parts[2])
        update_order_status(oid, "rejected")
        msg_text = (f"❌ <b>PAYMENT DECLINED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"• Order ID: <code>{oid}</code>\n"
                    f"• Buyer ID: <code>{uid_user}</code>\n"
                    f"• Declined by: <code>{uid}</code>")
        try:
            await cb.message.edit_caption(caption=msg_text, parse_mode="HTML")
        except Exception:
            await cb.message.edit_text(msg_text, parse_mode="HTML")
        await bot.send_message(uid_user, f"❌ <b>Order {oid} rejected.</b>\n\nContact @HIND_DEALS for help.", parse_mode="HTML")
        await cb.answer()
        return

    # ── Deposit Approve ────────────────────────────
    if data.startswith("dep_approve_"):
        parts    = data.split("_", 4)
        dep_id   = parts[2]
        amount   = int(parts[3])
        uid_user = int(parts[4])
        dep = get_deposit(dep_id)
        if not dep or dep[3] != "pending":
            await cb.answer("⚠️ Deposit already processed.", show_alert=True)
            return
        update_deposit_status(dep_id, "approved")
        credit_wallet(uid_user, amount, f"Deposit approved — {dep_id}")
        msg_text = (f"✅ <b>WALLET TOP-UP APPROVED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"• Deposit ID: <code>{dep_id}</code>\n"
                    f"• Buyer ID: <code>{uid_user}</code>\n"
                    f"• Amount: <b>₹{amount}</b> wallet mein add ho gaya\n"
                    f"• Approved by: <code>{uid}</code>")
        try:
            await cb.message.edit_caption(caption=msg_text, parse_mode="HTML")
        except Exception:
            await cb.message.edit_text(msg_text, parse_mode="HTML")
        try:
            await bot.send_message(
                uid_user,
                f"✅ <b>Deposit Approved!</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💚 ₹{amount} aapke wallet mein add ho gaya!\n"
                f"🆔 Deposit ID: <code>{dep_id}</code>\n\n"
                f"Ab aap wallet se koi bhi service khareed sakte hain. 🎉",
                parse_mode="HTML",
                reply_markup=main_kb()
            )
        except Exception:
            pass
        await cb.answer("✅ Deposit Approved!", show_alert=True)
        return

    # ── Deposit Reject ─────────────────────────────
    if data.startswith("dep_reject_"):
        parts    = data.split("_", 3)
        dep_id   = parts[2]
        uid_user = int(parts[3])
        dep = get_deposit(dep_id)
        if not dep or dep[3] != "pending":
            await cb.answer("⚠️ Deposit already processed.", show_alert=True)
            return
        update_deposit_status(dep_id, "rejected")
        msg_text = (f"❌ <b>WALLET TOP-UP DECLINED</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"• Deposit ID: <code>{dep_id}</code>\n"
                    f"• Buyer ID: <code>{uid_user}</code>\n"
                    f"• Declined by: <code>{uid}</code>")
        try:
            await cb.message.edit_caption(caption=msg_text, parse_mode="HTML")
        except Exception:
            await cb.message.edit_text(msg_text, parse_mode="HTML")
        try:
            await bot.send_message(
                uid_user,
                f"❌ <b>Deposit Rejected.</b>\n\n"
                f"🆔 Deposit ID: <code>{dep_id}</code>\n\n"
                f"Koi issue hai? Contact karein: @HIND_DEALS",
                parse_mode="HTML",
                reply_markup=main_kb()
            )
        except Exception:
            pass
        await cb.answer("❌ Deposit Rejected!", show_alert=True)
        return

    # ── Deliver ────────────────────────────────────
    if data.startswith("deliver_"):
        if not is_delivery_admin(uid):
            await cb.answer("⛔ No permission", show_alert=True)
            return
        parts    = data.split("_")
        oid      = parts[1]
        uid_user = int(parts[2])
        amount   = int(parts[3])
        update_order_status(oid, "delivered")
        # Activate HIND DEALS TV subscription if this is a TV order
        maybe_activate_hindtv(oid, uid_user)
        msg_text = f"✅ <b>Order {oid} — DELIVERED!</b>\n\nRating request sent."
        try:
            await cb.message.edit_caption(caption=msg_text, parse_mode="HTML")
        except Exception:
            await cb.message.edit_text(msg_text, parse_mode="HTML")

        # Build delivery message; if TV order, add myapp button
        sub = get_mini_app_sub(uid_user)
        delivery_text = (
            f"✅ <b>Order {oid} has been DELIVERED!</b> 🎉\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        deliver_kb_user = rating_kb(oid)
        if sub:
            delivery_text += "📺 Your <b>HIND DEALS TV</b> subscription is now active!\nUse /myapp to access.\n\n"
        delivery_text += "⭐ <b>Rate your experience!</b> (Tap a star or SKIP)"
        await bot.send_message(uid_user, delivery_text, parse_mode="HTML", reply_markup=deliver_kb_user)
        await cb.answer()
        return

    # ── Admin Settings (Edit Messages) ─────────────
    if data == "admin_settings":
        if not can_manage_services(uid):
            await cb.answer("⛔ No permission", show_alert=True)
            return
        settings = get_all_settings()
        text = (
            "✏️ <b>EDIT BOT MESSAGES</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Select which message/setting to edit:\n\n"
            f"🔗 Review Link: <code>{settings.get('review_link','')[:50]}</code>\n"
            f"📺 Mini App URL: <code>{settings.get('mini_app_url','') or 'Not set'}</code>\n\n"
            "<i>All changes take effect immediately.</i>"
        )
        await cb.message.answer(text, parse_mode="HTML", reply_markup=settings_kb())
        await cb.answer()
        return

    if data.startswith("editset_"):
        if not can_manage_services(uid):
            await cb.answer("⛔ No permission", show_alert=True)
            return
        setting_key = data[8:]   # e.g., "welcome_msg"
        prompts = {
            "welcome_msg":         "✏️ Send the new <b>Welcome Message</b> text:\n\n<i>HTML tags supported (b, i, code, etc.)</i>",
            "payment_pending_msg": "✏️ Send the new <b>Payment Pending Message</b>:\n\n<i>Sent to users after they send payment screenshot.</i>",
            "offline_msg":         "✏️ Send the new <b>Offline Auto-Reply</b> message:\n\n<i>Sent once to new users when they first message the bot.</i>",
            "mini_app_url":        "✏️ Send the <b>Telegram Mini App URL</b>:\n\n<i>Must be a valid HTTPS URL for a Telegram WebApp.</i>",
            "review_link":         "✏️ Send the new <b>Review/Community Link</b>:\n\n<i>Example: https://t.me/HIND_DEALS_REVIEWS</i>",
        }
        prompt = prompts.get(setting_key, "✏️ Send the new value:")
        await cb.message.answer(prompt, parse_mode="HTML")
        await state.update_data(setting_key=setting_key)
        await state.set_state(EditSettingState.waiting_value)
        await cb.answer()
        return

    # ── Mini App Subscriptions management ──────────
    if data == "admin_minisubs":
        if not can_manage_services(uid):
            await cb.answer("⛔ No permission", show_alert=True)
            return
        active = get_all_active_subs(50)
        text = f"📺 <b>HIND DEALS TV — Active Subscriptions</b>\n━━━━━━━━━━━━━━━━━━━━\n\nTotal active: <b>{len(active)}</b>\n"
        await cb.message.answer(text, parse_mode="HTML", reply_markup=minisubs_kb())
        await cb.answer()
        return

    if data == "minisubs_list":
        active = get_all_active_subs(30)
        if not active:
            await cb.message.answer("📭 <b>No active subscriptions</b>", parse_mode="HTML")
        else:
            text = "📺 <b>ACTIVE MINI APP SUBS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for uid_, uname, plan, expiry in active:
                text += f"👤 @{uname or uid_} (<code>{uid_}</code>)\n   {plan} → {expiry[:10]}\n\n"
            await cb.message.answer(text, parse_mode="HTML")
        await cb.answer()
        return

    if data == "minisubs_check":
        await cb.message.answer("👤 <b>Send user ID to check subscription:</b>", parse_mode="HTML")
        await state.set_state(AdminState.waiting_for_user_id)
        await state.update_data(admin_action="minisubs_check")
        await cb.answer()
        return

    if data == "minisubs_revoke":
        await cb.message.answer("👤 <b>Send user ID to revoke subscription:</b>", parse_mode="HTML")
        await state.set_state(AdminState.waiting_for_user_id)
        await state.update_data(admin_action="minisubs_revoke")
        await cb.answer()
        return

    # Fallback for unhandled callbacks
    await cb.answer()


# ── Service edit FSM (new_value state) ────────────
@dp.message(ServiceEditState.new_value)
async def svc_edit_value_handler(msg: Message, state: FSMContext):
    data    = await state.get_data()
    svc_key = data.get("edit_svc_key")
    field   = data.get("edit_svc_field")

    conn = db()
    c = conn.cursor()

    if field == "name":
        c.execute("UPDATE services SET display_name=? WHERE service_key=?", (msg.text.strip(), svc_key))
        conn.commit()
        conn.close()
        reload_products()
        await msg.answer(f"✅ <b>Name updated!</b>", parse_mode="HTML")

    elif field == "desc":
        c.execute("UPDATE services SET description=? WHERE service_key=?", (msg.text.strip(), svc_key))
        conn.commit()
        conn.close()
        reload_products()
        await msg.answer("✅ <b>Description updated!</b>", parse_mode="HTML")

    elif field == "kw":
        c.execute("UPDATE services SET keywords=? WHERE service_key=?", (msg.text.strip(), svc_key))
        conn.commit()
        conn.close()
        reload_products()
        await msg.answer(f"✅ <b>Keywords updated!</b>", parse_mode="HTML")

    elif field == "prices":
        lines = [l.strip() for l in msg.text.strip().split("\n") if l.strip()]
        errors = []
        for line in lines:
            try:
                dur, price = line.split("|")
                c.execute("UPDATE service_prices SET price=? WHERE service_key=? AND duration=?",
                          (int(price.strip()), svc_key, dur.strip()))
            except Exception:
                errors.append(line)
        conn.commit()
        conn.close()
        reload_products()
        if errors:
            await msg.answer(f"⚠️ Updated with errors on: {', '.join(errors)}", parse_mode="HTML")
        else:
            await msg.answer("✅ <b>Prices updated!</b>", parse_mode="HTML")

    elif field == "stock":
        lines = [l.strip() for l in msg.text.strip().split("\n") if l.strip()]
        errors = []
        for line in lines:
            try:
                dur, stk = line.split("|")
                c.execute("UPDATE service_prices SET stock=? WHERE service_key=? AND duration=?",
                          (int(stk.strip()), svc_key, dur.strip()))
            except Exception:
                errors.append(line)
        conn.commit()
        conn.close()
        reload_products()
        if errors:
            await msg.answer(f"⚠️ Updated with errors on: {', '.join(errors)}", parse_mode="HTML")
        else:
            await msg.answer("✅ <b>Stock updated!</b>", parse_mode="HTML")
    else:
        conn.close()
        await msg.answer("❌ Unknown field.", parse_mode="HTML")

    await state.clear()

# ══════════════════════════════════════════════════
#  HELPER — decrement stock for an order
# ══════════════════════════════════════════════════
def decrement_stock_for_order(order_id: str):
    """Safely decrement stock when an order is approved."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT product_name, duration FROM orders WHERE order_id=?", (order_id,))
    row = c.fetchone()
    conn.close()
    if row:
        decrement_stock(row[0], row[1])

def maybe_activate_hindtv(order_id: str, user_id: int):
    """If this order is for HIND DEALS TV, activate the mini-app subscription."""
    o = get_order(order_id)
    if not o:
        return
    product_key = o[2]   # product_name column
    duration    = o[3]
    if product_key == "hindtv":
        activate_mini_app_sub(user_id, duration, order_id)

# ──────────────────────────────────────────────────
#  Edit Setting FSM handler
# ──────────────────────────────────────────────────
@dp.message(EditSettingState.waiting_value)
async def edit_setting_value_handler(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    key  = data.get("setting_key", "")
    val  = msg.text or ""
    if not key or not val.strip():
        await msg.answer("❌ <b>Empty value — not saved.</b>", parse_mode="HTML")
        await state.clear()
        return
    set_setting(key, val.strip())
    friendly = {
        "welcome_msg":         "Welcome Message",
        "payment_pending_msg": "Payment Pending Message",
        "offline_msg":         "Offline Auto-Reply",
        "mini_app_url":        "Mini App URL",
        "review_link":         "Review Link",
    }.get(key, key)
    await msg.answer(
        f"✅ <b>{friendly} updated successfully!</b>\n\n"
        f"<i>New value saved. It will be used from now on.</i>",
        parse_mode="HTML"
    )
    await state.clear()




# ══════════════════════════════════════════════════
#  PAYMENT GATEWAY — INPUT HANDLERS
# ══════════════════════════════════════════════════
@dp.message(GatewayState.waiting_amount)
async def gw_amount_handler(msg: Message, state: FSMContext):
    raw = (msg.text or "").strip().replace("₹", "")
    try:
        amount = int(float(raw))
    except Exception:
        await msg.answer("❌ <b>Sirf number bhejiye</b> jaise <code>100</code>", parse_mode="HTML")
        return
    if amount < gw_min():
        await msg.answer(f"❌ Minimum ₹{gw_min()} hai.", parse_mode="HTML")
        return
    await state.clear()
    uid = msg.from_user.id
    gw_oid = gw_new_id(uid)
    ok, url, err = await gw_create_order(amount, gw_oid, remark="wallet recharge")
    if not ok:
        await msg.answer(
            f"⚠️ <b>Online payment abhi available nahi</b>\n\n<code>{err}</code>\n\n"
            f"Aap <code>qr {amount}</code> type karke QR se bhi pay kar sakte hain.",
            parse_mode="HTML")
        return
    gw_save(gw_oid, uid, amount, "deposit", "", url)
    await msg.answer(
        f"⚡ <b>WALLET RECHARGE — ₹{amount}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1️⃣ <b>PAY NOW</b> dabaiye\n2️⃣ Kisi bhi UPI app se pay kijiye\n"
        f"3️⃣ Paisa aate hi wallet me <b>automatic</b> add ho jayega\n\n"
        f"🆔 <code>{gw_oid}</code>\n⏱️ Link {GATEWAY_EXPIRY_MIN} min valid hai.",
        parse_mode="HTML",
        reply_markup=gw_pay_kb(gw_oid, url)
    )

@dp.message(GatewayState.waiting_token)
async def gw_token_handler(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear(); return
    tok = (msg.text or "").strip()
    if len(tok) < 6:
        await msg.answer("❌ Token bahut chhota lag raha hai. Dobara bhejiye.", parse_mode="HTML")
        return
    set_setting("gw_token", tok)
    set_setting("gw_enabled", "1")
    await state.clear()
    await msg.answer("✅ <b>Token save ho gaya aur gateway ON hai.</b>\n\n"
                     "Ab admin panel → ⚡ PAYMENT GATEWAY → 🧪 TEST GATEWAY se check kijiye.",
                     parse_mode="HTML")

@dp.message(GatewayState.waiting_base)
async def gw_base_handler(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear(); return
    url = (msg.text or "").strip().rstrip("/")
    if not url.startswith("http"):
        await msg.answer("❌ URL <code>https://</code> se start hona chahiye.", parse_mode="HTML")
        return
    set_setting("gw_base", url)
    await state.clear()
    await msg.answer(f"✅ Panel URL set: <code>{url}</code>", parse_mode="HTML")

@dp.message(GatewayState.waiting_min)
async def gw_min_handler(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear(); return
    try:
        val = max(1, int(float((msg.text or "").strip())))
    except Exception:
        await msg.answer("❌ Sirf number bhejiye.", parse_mode="HTML")
        return
    set_setting("gw_min", str(val))
    await state.clear()
    await msg.answer(f"✅ Minimum amount ₹{val} set.", parse_mode="HTML")

@dp.message(Command("gateway"))
async def gateway_cmd(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ <b>Unauthorized</b>", parse_mode="HTML")
        return
    ok_cnt, ok_sum, pend = gw_stats()
    tok = gw_token()
    masked = (tok[:4] + "•" * 6 + tok[-4:]) if len(tok) > 8 else ("set" if tok else "❌ not set")
    await msg.answer(
        f"⚡ <b>PAYMENT GATEWAY</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Status: <b>{'🟢 ON' if gw_enabled() else '🔴 OFF'}</b>\n"
        f"Panel: <code>{gw_base()}</code>\nToken: <code>{masked}</code>\n"
        f"Min: ₹{gw_min()}\n\n✅ Success: {ok_cnt} — ₹{ok_sum:.0f}\n⏳ Pending: {pend}",
        parse_mode="HTML", reply_markup=gw_admin_kb())

@dp.message(Command("addmoney"))
async def addmoney_cmd(msg: Message, state: FSMContext):
    if not gw_enabled():
        await msg.answer("⚡ Auto payment abhi band hai.\n\n<code>qr 100</code> type karke QR se add kijiye.",
                         parse_mode="HTML")
        return
    await state.set_state(GatewayState.waiting_amount)
    await msg.answer(f"⚡ <b>Kitna amount add karna hai?</b> (min ₹{gw_min()})", parse_mode="HTML")

# ══════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════
async def main():
    init_db()
    me = await bot.get_me()
    print("=" * 55)
    print("🤖 HIND DEALS BOT v3.0 STARTED  —  main.py")
    print(f"✅ Bot:            @{me.username}")
    print(f"✅ Channel:        {CHANNEL_USERNAME}")
    print(f"✅ Owner:          {OWNER_ID}")
    print(f"✅ Active Services:{len(PRODUCTS)}")
    print(f"✅ Start page size:{START_MENU_PER_PAGE}")
    print(f"✅ Database:       {DB_NAME}")
    print(f"✅ Referral:       ₹{REFERRAL_REWARD} / Welcome ₹{WELCOME_BONUS}")
    print(f"✅ Wallet:         open for all users (QR + Wallet checkout)")
    print(f"✅ QR validity:    {QR_VALID_MIN} minutes (no re-generate)")
    print(f"✅ Admin wallet:   give/take balance enabled")
    print("=" * 55)
    if AUTO_APPROVAL:
        asyncio.create_task(gw_poller())
    else:
        print("⛔ Auto approval:  OFF (manual admin approval only)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
