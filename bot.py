#!/usr/bin/env python3
"""OG IOS SHOP — Telegram Bot"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
import uuid
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
    PicklePersistence
)
from telegram.error import Conflict, NetworkError, TimedOut

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  DEFAULT CONFIG  (editable at runtime via Admin → Settings)
# ═══════════════════════════════════════════════════════════════════════════════
BOT_TOKEN         = os.environ.get("BOT_TOKEN", "8767460408:AAHAt3YOL4S0tExSC8656zUdlmsws3QYdJ8")
ADMIN_IDS         = [8503115617, 6761125512, 6617032248, 8405538061]

DEFAULT_SHOP_NAME       = "MARSCOT SELLER"
DEFAULT_SUPPORT         = "@Blyat35"
DEFAULT_VERIFY_CHANNEL  = -1002309985456

DATA_FILE        = "bot_data.json"
def find_image(paths: list) -> str | None:
    for p in paths:
        if Path(p).exists():
            return p
    return None

# ═══════════════════════════════════════════════════════════════════════════════
#  CUSTOM EMOJI HELPER
# ═══════════════════════════════════════════════════════════════════════════════
def ce(eid: str, fb: str) -> str:
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'

CE_ANIM     = ce("5456140674028019486", "⏳")
CE_ACCT     = ce("5954175920506933873", "👤")
CE_CART     = ce("5440841102871517055", "🛒")
CE_WALLET   = ce("5764706418951200101", "💰")
CE_ADMIN    = ce("5765087343895649564", "🔧")
CE_STATUS   = ce("6059653892025618055", "✅")
CE_AVAIL    = ce("5445195276291693508", "🟢")
CE_UNAVAIL  = ce("5445102217235292298", "🔴")
CE_STATS    = ce("5877332341331857066", "📊")
CE_DENY     = ce("5462989862669920629", "❌")
CE_SUCCESS  = ce("5953810354365538566", "🎉")
CE_PROD_LBL = ce("5323289282499064033", "📦")
CE_DUR_LBL  = ce("5472026645659401564", "⏱️")
CE_KEY_LBL  = ce("6147915796375935782", "🔑")
CE_SETTINGS = ce("5377435272541401661", "⚙️")

CE_FLUORITE = ce("5292158397465005457", "💎")
CE_PROXY    = ce("5796407074346767851", "🔷")
CE_FLIZA    = ce("5764984492313811194", "⚡")
CE_MIGUL    = ce("6233248412771295068", "⭐")

CE_WELCOME  = ce("5305388752162539722", "👋")
CE_SHOP     = ce("5235752437347807943", "🏪")
CE_FF       = ce("6228904568747465283", "🎮")

# ═══════════════════════════════════════════════════════════════════════════════
#  BASE MENU  (prices/names are overridable via Settings)
# ═══════════════════════════════════════════════════════════════════════════════
BASE_MENU = {
    "ff_ios": {
        "label": "Free Fire (iOS)",
        "ce": CE_FF,
        "products": [
            {
                "id": "fluorite",
                "name": "Fluorite Panel",
                "ce": CE_FLUORITE,
                "prices": [
                    ("31 Days", "15.00"),
                    ("1 Week",  "9.00"),
                    ("1 Day",   "4.00"),
                ],
            },
            {
                "id": "proxy",
                "name": "Proxy Aimdrag",
                "ce": CE_PROXY,
                "prices": [
                    ("1 Month", "10.00"),
                    ("1 Week",  "6.00"),
                    ("1 Day",   "2.00"),
                ],
            },
            {
                "id": "filza",
                "name": "Filza Cheat",
                "ce": CE_FLIZA,
                "prices": [
                    ("Aimdrag", "20.00"),
                    ("Aimneck", "20.00"),
                ],
            },
            {
                "id": "migul",
                "name": "Migul Panel",
                "ce": CE_MIGUL,
                "prices": [
                    ("1 Month", "15.00"),
                    ("1 Week",  "8.00"),
                    ("1 Day",   "4.00"),
                ],
            },
        ],
    },
}
CAT_ORDER = ["ff_ios"]


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
_MEM_DATA:  dict = {}
_MEM_STATE: dict = {}

def load() -> dict:
    global _MEM_DATA
    d = None
    if Path(DATA_FILE).exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            pass
    if d is None:
        d = dict(_MEM_DATA) if _MEM_DATA else {}
    d.setdefault("verified", [])
    d.setdefault("admin_ids", [])
    d.setdefault("keys", {})
    d.setdefault("files", {})
    d.setdefault("balances", {})
    d.setdefault("pending_orders", {})
    d.setdefault("_state", {})
    d.setdefault("config", {})
    return d

def save(d: dict):
    global _MEM_DATA
    _MEM_DATA = d
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except Exception:
        pass

def get_state(d: dict, uid: int):
    key = str(uid)
    return d.get("_state", {}).get(key) or _MEM_STATE.get(key)

def set_state(d: dict, uid: int, state):
    key = str(uid)
    _MEM_STATE[key] = state
    d.setdefault("_state", {})[key] = state
    save(d)

def clear_state(d: dict, uid: int):
    key = str(uid)
    _MEM_STATE.pop(key, None)
    d.setdefault("_state", {}).pop(key, None)
    save(d)

def is_admin(uid: int, d: dict) -> bool:
    return uid in ADMIN_IDS or uid in d.get("admin_ids", [])

def is_verified(uid: int, d: dict) -> bool:
    return is_admin(uid, d) or uid in d.get("verified", [])

def get_balance(uid: int, d: dict) -> float:
    return round(float(d.get("balances", {}).get(str(uid), 0.0)), 2)

def esc(t) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ═══════════════════════════════════════════════════════════════════════════════
#  RUNTIME CONFIG HELPERS  (read config overrides, fall back to defaults)
# ═══════════════════════════════════════════════════════════════════════════════
def cfg(d: dict, key: str, default):
    return d.get("config", {}).get(key, default)

def shop_name(d: dict) -> str:
    return cfg(d, "shop_name", DEFAULT_SHOP_NAME)

def support(d: dict) -> str:
    return cfg(d, "support", DEFAULT_SUPPORT)

def binance_id(d: dict) -> str:
    return cfg(d, "binance_id", DEFAULT_BINANCE_ID)

def verify_channel(d: dict) -> int:
    return int(cfg(d, "verify_channel", DEFAULT_VERIFY_CHANNEL))

def prod_name(cat_key: str, idx: int, d: dict) -> str:
    key = f"{cat_key}_{idx}_name"
    return cfg(d, key, BASE_MENU[cat_key]["products"][idx]["name"])

def prod_prices(cat_key: str, idx: int, d: dict) -> list[tuple[str, str]]:
    """Return list of (duration_label, price_str) with any price overrides applied."""
    base = BASE_MENU[cat_key]["products"][idx]["prices"]
    overrides = d.get("config", {}).get("prices", {}).get(f"{cat_key}_{idx}", {})
    if not overrides:
        return base
    return [(dur, overrides.get(dur, price)) for dur, price in base]

def set_price(cat_key: str, idx: int, dur: str, new_price: str, d: dict):
    d.setdefault("config", {}).setdefault("prices", {}).setdefault(f"{cat_key}_{idx}", {})[dur] = new_price
    save(d)


# ═══════════════════════════════════════════════════════════════════════════════
#  KEY / FILE / STOCK HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def key_slot(cat: str, idx: int, dur: str) -> str:
    return f"{cat}_{idx}_{dur}"

def file_slot(cat: str, idx: int) -> str:
    return f"file_{cat}_{idx}"

def keys_count(cat: str, idx: int, dur: str, d: dict) -> int:
    return len(d.get("keys", {}).get(key_slot(cat, idx, dur), []))

def files_count(cat: str, idx: int, d: dict) -> int:
    return len(d.get("files", {}).get(file_slot(cat, idx), []))

def slot_stock(cat: str, idx: int, dur: str, d: dict) -> int:
    return keys_count(cat, idx, dur, d)

def total_product_stock(k: str, i: int, d: dict) -> int:
    prods = BASE_MENU[k]
    if i >= len(prods["products"]):
        return 0
    return sum(slot_stock(k, i, dur, d) for dur, _ in prod_prices(k, i, d))

def pop_key(cat: str, idx: int, dur: str, d: dict):
    slot = key_slot(cat, idx, dur)
    lst  = d.get("keys", {}).get(slot, [])
    if not lst:
        return None
    k = lst.pop(0)
    d["keys"][slot] = lst
    save(d)
    return k

def pop_file(cat: str, idx: int, d: dict):
    slot = file_slot(cat, idx)
    lst  = d.get("files", {}).get(slot, [])
    if not lst:
        return None
    f = lst.pop(0)
    d["files"][slot] = lst
    save(d)
    return f

def peek_file(cat: str, idx: int, d: dict):
    slot = file_slot(cat, idx)
    lst  = d.get("files", {}).get(slot, [])
    return lst[0] if lst else None

async def send_long(target, text: str, **kwargs):
    limit = 4096
    if len(text) <= limit:
        await target.reply_text(text, **kwargs)
        return
    chunks, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    for chunk in chunks:
        await target.reply_text(chunk, **kwargs)
        await asyncio.sleep(0.15)


# ═══════════════════════════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════════════
def kb_main(uid: int, d: dict) -> ReplyKeyboardMarkup:
    rows = [["🛒 Shop"], ["👤 Account", "📊 Stock"]]
    if is_admin(uid, d):
        rows.append(["🔧 Admin Panel"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def kb_login_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌  Cancel", callback_data="login_cancel")
    ]])

def kb_cat(k: str, d: dict) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(prod_name(k, i, d), callback_data=f"prod|{k}|{i}")]
        for i in range(len(BASE_MENU[k]["products"]))
    ]
    return InlineKeyboardMarkup(rows)

def kb_durations(k: str, idx: int, d: dict) -> InlineKeyboardMarkup:
    rows = []
    for dur, price in prod_prices(k, idx, d):
        qty    = slot_stock(k, idx, dur, d)
        status = "✅" if qty > 0 else "❌"
        rows.append([InlineKeyboardButton(
            f"{status}  {dur}  —  ${price}",
            callback_data=f"dur|{k}|{idx}|{dur}|{price}"
        )])
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data=f"cat|{k}")])
    return InlineKeyboardMarkup(rows)

def kb_buy_balance(k: str, idx: int, dur: str, price: str) -> InlineKeyboardMarkup:
    base = f"{k}|{idx}|{dur}|{price}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💰  Buy Now  (${price})", callback_data=f"pay|bal|{base}")],
        [InlineKeyboardButton("⬅️  Back", callback_data=f"prod|{k}|{idx}")],
    ])

def kb_approve_deny(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅  Approve", callback_data=f"approve|{order_id}"),
        InlineKeyboardButton("❌  Deny",    callback_data=f"deny|{order_id}"),
    ]])

def kb_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌  Cancel", callback_data="adm|cancel")
    ]])

def kb_admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑  Add Keys",         callback_data="adm|add_keys"),
         InlineKeyboardButton("📁  Add File",         callback_data="adm|add_files")],
        [InlineKeyboardButton("🔑  View Keys Stock",  callback_data="adm|view_keys"),
         InlineKeyboardButton("📁  View Files Stock", callback_data="adm|view_files")],
        [InlineKeyboardButton("🗑️  Remove File",      callback_data="adm|remove_file"),
         InlineKeyboardButton("🗑️  Remove Keys",      callback_data="adm|clear")],
        [InlineKeyboardButton("💰  Add Balance",      callback_data="adm|add_bal"),
         InlineKeyboardButton("💰  Deduct Balance",   callback_data="adm|ded_bal")],
        [InlineKeyboardButton("💰  Check Balance",    callback_data="adm|chk_bal"),
         InlineKeyboardButton("👑  Add Admin",        callback_data="adm|add_admin")],
        [InlineKeyboardButton("🔐  Credentials",      callback_data="adm|creds")],
        [InlineKeyboardButton("📢  Broadcast",        callback_data="adm|broadcast")],
        [InlineKeyboardButton(f"⚙️  Settings",        callback_data="cfg|menu")],
    ])

def kb_creds(d: dict) -> InlineKeyboardMarkup:
    rows = []
    creds = d.get("credentials", [])
    for i, c in enumerate(creds):
        label = c.get("label", "—")
        pw    = c.get("password", "")
        rows.append([InlineKeyboardButton(
            f"🗑️  {label}  ({pw})",
            callback_data=f"adm|del_cred|{i}"
        )])
    rows.append([InlineKeyboardButton("➕  Add Credential", callback_data="adm|add_cred")])
    rows.append([InlineKeyboardButton("⬅️  Back",          callback_data="adm|back")])
    return InlineKeyboardMarkup(rows)

# ── Settings keyboards ────────────────────────────────────────────────────────
def kb_settings() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪  Shop Name",       callback_data="cfg|shop_name"),
         InlineKeyboardButton("📞  Support Contacts",callback_data="cfg|support")],
        [InlineKeyboardButton("📦  Product Names",   callback_data="cfg|prod_names")],
        [InlineKeyboardButton("💰  Product Prices",  callback_data="cfg|prices_menu")],
        [InlineKeyboardButton("⬅️  Back",            callback_data="adm|back")],
    ])

def kb_cfg_prod_names(d: dict) -> InlineKeyboardMarkup:
    rows = []
    for k in CAT_ORDER:
        for i, p in enumerate(BASE_MENU[k]["products"]):
            name = prod_name(k, i, d)
            rows.append([InlineKeyboardButton(name, callback_data=f"cfg|pn|{k}|{i}")])
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data="cfg|menu")])
    return InlineKeyboardMarkup(rows)

def kb_cfg_prices_cats(d: dict) -> InlineKeyboardMarkup:
    rows = []
    for k in CAT_ORDER:
        for i, p in enumerate(BASE_MENU[k]["products"]):
            name = prod_name(k, i, d)
            rows.append([InlineKeyboardButton(name, callback_data=f"cfg|pp|{k}|{i}")])
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data="cfg|menu")])
    return InlineKeyboardMarkup(rows)

def kb_cfg_prices_durs(k: str, idx: int, d: dict) -> InlineKeyboardMarkup:
    rows = []
    for dur, price in prod_prices(k, idx, d):
        dur_enc = dur.replace(" ", "~")
        rows.append([InlineKeyboardButton(
            f"{dur}  — ${price}",
            callback_data=f"cfg|ppd|{k}|{idx}|{dur_enc}"
        )])
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data="cfg|prices_menu")])
    return InlineKeyboardMarkup(rows)

# ── Admin file/key keyboards ──────────────────────────────────────────────────
def kb_adm_cats_keys(d: dict) -> InlineKeyboardMarkup:
    rows = []
    for k in CAT_ORDER:
        if not BASE_MENU[k]["products"]:
            continue
        rows.append([InlineKeyboardButton(BASE_MENU[k]["label"], callback_data=f"akc|{k}")])
    rows.append([InlineKeyboardButton("❌  Cancel", callback_data="adm|cancel")])
    return InlineKeyboardMarkup(rows)

def kb_adm_cats_files(mode: str, d: dict) -> InlineKeyboardMarkup:
    rows = []
    for k in CAT_ORDER:
        if not BASE_MENU[k]["products"]:
            continue
        rows.append([InlineKeyboardButton(BASE_MENU[k]["label"], callback_data=f"a{mode}c|{k}")])
    rows.append([InlineKeyboardButton("❌  Cancel", callback_data="adm|cancel")])
    return InlineKeyboardMarkup(rows)

def kb_adm_prods_keys(cat_key: str, d: dict) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(prod_name(cat_key, i, d), callback_data=f"akp|{cat_key}|{i}")]
        for i in range(len(BASE_MENU[cat_key]["products"]))
    ]
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data="adm|add_keys")])
    return InlineKeyboardMarkup(rows)

def kb_adm_prods_files(mode: str, cat_key: str, d: dict) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(prod_name(cat_key, i, d), callback_data=f"a{mode}p|{cat_key}|{i}")]
        for i in range(len(BASE_MENU[cat_key]["products"]))
    ]
    back = "add_files" if mode == "f" else "remove_file"
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data=f"adm|{back}")])
    return InlineKeyboardMarkup(rows)

def kb_adm_durs_keys(cat_key: str, idx: int, d: dict) -> InlineKeyboardMarkup:
    rows = []
    for dur, _ in prod_prices(cat_key, idx, d):
        dur_enc = dur.replace(" ", "~")
        rows.append([InlineKeyboardButton(dur, callback_data=f"akd|{cat_key}|{idx}|{dur_enc}")])
    rows.append([InlineKeyboardButton("⬅️  Back", callback_data=f"akc|{cat_key}")])
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════════════════════════════════════
#  DISPLAY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def cat_msg(k: str, d: dict) -> str:
    cat = BASE_MENU[k]
    cce = cat["ce"]
    lines = [f"{cce} <b>{esc(cat['label'])}</b>\n"]
    for i, p in enumerate(cat["products"]):
        pname = prod_name(k, i, d)
        prices = prod_prices(k, i, d)
        lines.append(f"{p['ce']} <b>{esc(pname)}</b>")
        for dur, pr in prices:
            lines.append(f"   ‣ {esc(dur)}  —  <b>${esc(pr)}</b>")
        lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
#  CREDENTIAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def check_credential(password: str, d: dict) -> bool:
    for c in d.get("credentials", []):
        if c.get("password", "") == password:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  PAYMENT DETAILS
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
#  DELIVER PRODUCT
# ═══════════════════════════════════════════════════════════════════════════════
async def deliver_product(user_id: int, order: dict, ctx: ContextTypes.DEFAULT_TYPE):
    k      = order["k"]
    i      = order["i"]
    dur    = order["dur"]
    price  = order["price"]
    method = order["method"]

    d   = load()
    cat = BASE_MENU.get(k)
    if not cat or i >= len(cat["products"]):
        return False
    if keys_count(k, i, dur, d) == 0:
        return False

    pname    = prod_name(k, i, d)
    key_val  = pop_key(k, i, dur, d)
    file_val = pop_file(k, i, d) if files_count(k, i, d) > 0 else None
    sup      = support(d)
    sname    = shop_name(d)
    method_label = {"upi": "UPI", "bnb": "Binance", "other": "Other", "bal": "Balance"}.get(method, method)

    await ctx.bot.send_message(
        chat_id=user_id,
        text=(
            f"{CE_SUCCESS} <b>PURCHASE SUCCESSFUL — {esc(sname)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{CE_PROD_LBL} <b>Product:</b> {esc(pname)}\n"
            f"{CE_DUR_LBL} <b>Duration:</b> {esc(dur)}\n"
            f"{CE_KEY_LBL} <b>Key:</b> <code>{esc(key_val)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Support: {sup}"
        ),
        parse_mode="HTML"
    )

    if file_val:
        ft, fv, fn = file_val.get("type","link"), file_val.get("value",""), file_val.get("name","file")
        if ft == "document":
            await ctx.bot.send_document(chat_id=user_id, document=fv,
                                        caption=f"📁 <b>{esc(fn)}</b>", parse_mode="HTML")
        elif ft == "photo":
            await ctx.bot.send_photo(chat_id=user_id, photo=fv,
                                     caption=f"🖼 <b>{esc(fn)}</b>", parse_mode="HTML")
        else:
            await ctx.bot.send_message(chat_id=user_id,
                                       text=f"📁 <b>Download Link:</b>\n{esc(fv)}", parse_mode="HTML")
    else:
        await ctx.bot.send_message(chat_id=user_id,
                                   text=f"📁 <b>File coming soon.</b>\nContact admin: {sup}", parse_mode="HTML")

    d2         = load()
    all_admins = list(set(ADMIN_IDS + d2.get("admin_ids", [])))
    for aid in all_admins:
        try:
            file_note = (f"File: <b>{esc(file_val.get('name','?'))}</b>"
                         if file_val else "File: <b>not sent (none in stock)</b>")
            await ctx.bot.send_message(
                chat_id=aid,
                text=(
                    f"🛒 <b>Purchase Delivered</b>\n\n"
                    f"User: <code>{user_id}</code>\n"
                    f"Product: {esc(pname)}\n"
                    f"Duration: {esc(dur)}\n"
                    f"Price: ${esc(price)}\n"
                    f"Method: {method_label}\n"
                    f"Key: <code>{esc(key_val)}</code>\n"
                    f"{file_note}"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass
    return True


# ═══════════════════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    uid  = update.effective_user.id
    name = esc(update.effective_user.first_name or "there")
    sn   = shop_name(d)
    if is_verified(uid, d):
        await update.message.reply_text(
            f"{CE_WELCOME} <b>Welcome back, {name}!</b>\n\n"
            f"{CE_SHOP} <b>{esc(sn)}</b>\n\n"
            f"Tap <b>Shop</b> to browse products.",
            parse_mode="HTML", reply_markup=kb_main(uid, d)
        )
    else:
        set_state(d, uid, "awaiting_login")
        await update.message.reply_text(
            f"{CE_SHOP} <b>{esc(sn)}</b>\n\n"
            f"Hello, <b>{name}</b>!\n\n"
            f"🔐 Enter your <b>login password</b> to access the shop:",
            parse_mode="HTML", reply_markup=kb_login_cancel()
        )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    await update.message.reply_text(
        f"<b>{esc(shop_name(d))} — Help</b>\n\n"
        "/start — Main menu\n"
        "/help — This message\n\n"
        f"Support: {support(d)}",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  MEDIA HANDLER (admin adds file / user sends payment screenshot)
# ═══════════════════════════════════════════════════════════════════════════════
async def handle_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    if not is_verified(uid, d):
        await update.message.reply_text("Please enter your password first. Use /start")
        return

    state = get_state(d, uid)

    if state and state.startswith("add_file_item|") and is_admin(uid, d):
        parts = state.split("|", 3)
        if len(parts) != 3:
            await update.message.reply_text("State error. Use /start to reset.")
            return
        _, cat, idx_str = parts
        idx  = int(idx_str)
        slot = file_slot(cat, idx)
        d.setdefault("files", {}).setdefault(slot, [])

        if update.message.document:
            fobj      = update.message.document
            file_item = {"type": "document", "value": fobj.file_id, "name": fobj.file_name or "file"}
        elif update.message.photo:
            fobj      = update.message.photo[-1]
            file_item = {"type": "photo", "value": fobj.file_id, "name": "image"}
        else:
            await update.message.reply_text("Unsupported file type. Send a document or photo.")
            return

        d["files"][slot].append(file_item)
        clear_state(d, uid)
        save(d)
        pname = prod_name(cat, idx, d)
        await update.message.reply_text(
            f"✅ <b>File Added!</b>\n\n"
            f"Product: <b>{esc(pname)}</b>\n"
            f"File: <b>{esc(file_item['name'])}</b>\n"
            f"Total in slot: <b>{len(d['files'][slot])}</b>",
            parse_mode="HTML"
        )
        return

    if not state:
        await update.message.reply_text("Use /start to open the main menu.", parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════════
#  TEXT HANDLER
# ═══════════════════════════════════════════════════════════════════════════════
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    uid  = update.effective_user.id
    text = (update.message.text or "").strip()

    state = get_state(d, uid)

    # ── Login password handler ─────────────────────────────────────────────────
    if not is_verified(uid, d):
        if is_admin(uid, d):
            if uid not in d.get("verified", []):
                d.setdefault("verified", []).append(uid)
                save(d)
            name = esc(update.effective_user.first_name or "there")
            await update.message.reply_text(
                f"{CE_WELCOME} <b>Welcome, {name}!</b>\n\n{CE_SHOP} <b>{esc(shop_name(d))}</b>\n\nTap <b>Shop</b> to browse products.",
                parse_mode="HTML", reply_markup=kb_main(uid, d)
            )
            return
        if state == "awaiting_login":
            if check_credential(text, d):
                d.setdefault("verified", []).append(uid)
                clear_state(d, uid)
                save(d)
                name = esc(update.effective_user.first_name or "there")
                await update.message.reply_text(
                    f"{CE_SUCCESS} <b>Access Granted!</b>\n\n"
                    f"{CE_WELCOME} Welcome, <b>{name}</b>!\n\n"
                    f"{CE_SHOP} <b>{esc(shop_name(d))}</b>\n\nTap <b>Shop</b> to browse products.",
                    parse_mode="HTML", reply_markup=kb_main(uid, d)
                )
            else:
                await update.message.reply_text(
                    "❌ <b>Wrong password.</b> Try again or contact admin.",
                    parse_mode="HTML", reply_markup=kb_login_cancel()
                )
        else:
            set_state(d, uid, "awaiting_login")
            await update.message.reply_text(
                f"🔐 Enter your <b>login password</b> to access <b>{esc(shop_name(d))}</b>:",
                parse_mode="HTML", reply_markup=kb_login_cancel()
            )
        return

    # ── Clear state when any main menu button is pressed ──────────────────────
    if text in ("🛒 Shop", "👤 Account", "📊 Stock", "🔧 Admin Panel"):
        if state:
            clear_state(d, uid)
        state = None   # MUST reset local var so state handlers below don't fire

    # ── Admin: add keys ────────────────────────────────────────────────────────
    if state and state.startswith("add_keys_item|") and is_admin(uid, d):
        parts = state.split("|", 4)
        if len(parts) != 4:
            await update.message.reply_text("State error. Use /start to reset.")
            return
        _, cat, idx_str, dur = parts
        idx  = int(idx_str)
        slot = key_slot(cat, idx, dur)
        d.setdefault("keys", {}).setdefault(slot, [])
        new_keys = [k.strip() for k in text.splitlines() if k.strip()]
        d["keys"][slot].extend(new_keys)
        clear_state(d, uid)
        save(d)
        pname = prod_name(cat, idx, d)
        await update.message.reply_text(
            f"✅ <b>{len(new_keys)} key(s) added!</b>\n\n"
            f"Product: <b>{esc(pname)}</b>\n"
            f"Duration: <b>{esc(dur)}</b>\n"
            f"Total in slot: <b>{len(d['keys'][slot])}</b>",
            parse_mode="HTML"
        )
        return

    # ── Admin: add file link ───────────────────────────────────────────────────
    if state and state.startswith("add_file_item|") and is_admin(uid, d):
        parts = state.split("|", 3)
        if len(parts) != 3:
            await update.message.reply_text("State error. Use /start to reset.")
            return
        _, cat, idx_str = parts
        idx  = int(idx_str)
        slot = file_slot(cat, idx)
        d.setdefault("files", {}).setdefault(slot, [])
        file_item = {"type": "link", "value": text, "name": text[:60]}
        d["files"][slot].append(file_item)
        clear_state(d, uid)
        save(d)
        pname = prod_name(cat, idx, d)
        await update.message.reply_text(
            f"✅ <b>Link Added!</b>\n\n"
            f"Product: <b>{esc(pname)}</b>\n"
            f"Link: <code>{esc(text[:80])}</code>\n"
            f"Total in slot: <b>{len(d['files'][slot])}</b>",
            parse_mode="HTML"
        )
        return

    # ── Admin: broadcast ──────────────────────────────────────────────────────
    if state == "broadcast" and is_admin(uid, d):
        users = list(set(d.get("verified", []) + d.get("admin_ids", []) + ADMIN_IDS))
        clear_state(d, uid)
        sent = failed = 0
        for u in users:
            try:
                await ctx.bot.send_message(chat_id=u, text=text, parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)
        await update.message.reply_text(
            f"📢 <b>Broadcast sent!</b>\n\n✅ Delivered: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
            parse_mode="HTML"
        )
        return

    # ── Admin: balance ─────────────────────────────────────────────────────────
    if state == "add_bal" and is_admin(uid, d):
        try:
            parts = text.split(); tid = int(parts[0]); amt = float(parts[1]); assert amt > 0
        except Exception:
            await update.message.reply_text("Send: <code>USER_ID AMOUNT</code>", parse_mode="HTML")
            return
        new = round(get_balance(tid, d) + amt, 2)
        d.setdefault("balances", {})[str(tid)] = new
        clear_state(d, uid); save(d)
        await update.message.reply_text(
            f"{CE_WALLET} Balance updated.\nUser: <code>{tid}</code>\n"
            f"Added: <b>+${amt:.2f}</b>\nNew balance: <b>${new:.2f}</b>",
            parse_mode="HTML"
        )
        return

    if state == "ded_bal" and is_admin(uid, d):
        try:
            parts = text.split(); tid = int(parts[0]); amt = float(parts[1]); assert amt > 0
        except Exception:
            await update.message.reply_text("Send: <code>USER_ID AMOUNT</code>", parse_mode="HTML")
            return
        new = max(0.0, round(get_balance(tid, d) - amt, 2))
        d.setdefault("balances", {})[str(tid)] = new
        clear_state(d, uid); save(d)
        await update.message.reply_text(
            f"{CE_WALLET} Balance updated.\nUser: <code>{tid}</code>\n"
            f"Deducted: <b>-${amt:.2f}</b>\nNew balance: <b>${new:.2f}</b>",
            parse_mode="HTML"
        )
        return

    if state == "chk_bal" and is_admin(uid, d):
        try:
            tid = int(text.strip())
        except ValueError:
            await update.message.reply_text("Send a valid numeric Telegram User ID.")
            return
        bal = get_balance(tid, d)
        clear_state(d, uid)
        await update.message.reply_text(
            f"User: <code>{tid}</code>\n{CE_WALLET} Balance: <b>${bal:.2f}</b>",
            parse_mode="HTML"
        )
        return

    if state == "admin_id" and is_admin(uid, d):
        try:
            new_id = int(text.strip())
        except ValueError:
            await update.message.reply_text("Send a valid numeric Telegram User ID.")
            return
        admins = d.setdefault("admin_ids", [])
        if new_id not in admins and new_id not in ADMIN_IDS:
            admins.append(new_id)
        clear_state(d, uid); save(d)
        await update.message.reply_text(
            f"✅ <b>Admin added!</b>\nUser ID: <code>{new_id}</code>", parse_mode="HTML"
        )
        return

    # ── Settings state handlers ────────────────────────────────────────────────
    if state == "cfg_shop_name" and is_admin(uid, d):
        d["config"]["shop_name"] = text
        clear_state(d, uid); save(d)
        await update.message.reply_text(
            f"✅ Shop name updated to: <b>{esc(text)}</b>", parse_mode="HTML"
        )
        return

    if state == "cfg_support" and is_admin(uid, d):
        d["config"]["support"] = text
        clear_state(d, uid); save(d)
        await update.message.reply_text(
            f"✅ Support contacts updated to:\n<code>{esc(text)}</code>", parse_mode="HTML"
        )
        return

    if state == "cfg_verify_ch" and is_admin(uid, d):
        try:
            ch = int(text.strip())
        except ValueError:
            await update.message.reply_text("Send a valid channel ID (e.g. -1001234567890).")
            return
        d["config"]["verify_channel"] = ch
        clear_state(d, uid); save(d)
        await update.message.reply_text(
            f"✅ Verify channel updated to: <code>{ch}</code>", parse_mode="HTML"
        )
        return

    if state and state.startswith("cfg_pname|") and is_admin(uid, d):
        _, k, idx_str = state.split("|", 2)
        idx = int(idx_str)
        d["config"][f"{k}_{idx}_name"] = text
        clear_state(d, uid); save(d)
        await update.message.reply_text(
            f"✅ Product name updated to: <b>{esc(text)}</b>", parse_mode="HTML"
        )
        return

    if state and state.startswith("cfg_price|") and is_admin(uid, d):
        _, k, idx_str, dur = state.split("|", 3)
        idx = int(idx_str)
        try:
            price_f = float(text.strip().replace("$", ""))
            assert price_f > 0
        except Exception:
            await update.message.reply_text("Send a valid price (e.g. <code>15.00</code>).", parse_mode="HTML")
            return
        new_price = f"{price_f:.2f}"
        set_price(k, idx, dur, new_price, d)
        clear_state(d, uid)
        pname = prod_name(k, idx, d)
        await update.message.reply_text(
            f"✅ Price updated!\n\nProduct: <b>{esc(pname)}</b>\nDuration: <b>{esc(dur)}</b>\nNew price: <b>${new_price}</b>",
            parse_mode="HTML"
        )
        return

    # ── Admin: add credential ─────────────────────────────────────────────────
    if state == "add_cred" and is_admin(uid, d):
        parts = text.strip().split(None, 1)
        if len(parts) < 2:
            await update.message.reply_text(
                "⚠️ Format: <code>LABEL PASSWORD</code>\nExample: <code>VIP user123</code>",
                parse_mode="HTML", reply_markup=kb_cancel()
            )
            return
        label, password = parts
        d.setdefault("credentials", []).append({"label": label, "password": password})
        clear_state(d, uid)
        save(d)
        await update.message.reply_text(
            f"✅ <b>Credential added!</b>\n\nLabel: <b>{esc(label)}</b>\nPassword: <code>{esc(password)}</code>",
            parse_mode="HTML"
        )
        return

    # ── Menu buttons ──────────────────────────────────────────────────────────
    if text == "🛒 Shop":
        txt = cat_msg("ff_ios", d)
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=kb_cat("ff_ios", d))
        return

    if text == "👤 Account":
        bal   = get_balance(uid, d)
        role  = "Admin" if is_admin(uid, d) else "User"
        uname = update.effective_user.username or "N/A"
        await update.message.reply_text(
            f"{CE_ACCT} <b>Account Info</b>\n\n"
            f"Name: {esc(update.effective_user.full_name or 'N/A')}\n"
            f"Username: @{esc(uname)}\n"
            f"ID: <code>{uid}</code>\n"
            f"Role: <b>{role}</b>\n"
            f"{CE_WALLET} Balance: <b>${bal:.2f}</b>\n"
            f"Status: <b>Verified ✅</b>",
            parse_mode="HTML"
        )
        return

    if text == "📊 Stock":
        d2    = load()
        lines = [f"{CE_STATS} <b>{esc(shop_name(d2))} — Stock</b>\n"]
        for k in CAT_ORDER:
            cat = BASE_MENU[k]
            lines.append(f"{cat['ce']} <b>{esc(cat['label'])}</b>")
            for i, p in enumerate(cat["products"]):
                pname  = prod_name(k, i, d2)
                total  = sum(keys_count(k, i, dur, d2) for dur, _ in prod_prices(k, i, d2))
                dot    = CE_AVAIL if total > 0 else CE_UNAVAIL
                lines.append(f"  {dot} {p['ce']} {esc(pname)} — <b>{total} keys</b>")
            lines.append("")
        await send_long(update.message, "\n".join(lines), parse_mode="HTML")
        return

    if text == "🔧 Admin Panel":
        if not is_admin(uid, d):
            await update.message.reply_text("Admins only.")
            return
        await update.message.reply_text(
            f"{CE_ADMIN} <b>Admin Panel — {esc(shop_name(d))}</b>\n\nChoose an action:",
            parse_mode="HTML", reply_markup=kb_admin_panel()
        )
        return


# ═══════════════════════════════════════════════════════════════════════════════
#  SETTINGS HANDLER  (called from handle_cb inside a try/except)
# ═══════════════════════════════════════════════════════════════════════════════
async def _handle_cfg(action: str, q, uid: int, d: dict):
    """All ⚙️ Settings sub-actions. Raises on error so caller can report it."""

    async def reply(text: str, kb=None):
        kwargs = {"parse_mode": "HTML"}
        if kb:
            kwargs["reply_markup"] = kb
        await q.message.reply_text(text, **kwargs)

    if action == "menu":
        sn = shop_name(d)
        await reply(
            f"<b>⚙️ Settings — {esc(sn)}</b>\n\n"
            f"🏪 Shop Name: <b>{esc(sn)}</b>\n"
            f"📞 Support: <code>{esc(support(d))}</code>\n"
            f"Choose what to edit:",
            kb_settings()
        )
        return

    if action == "shop_name":
        set_state(d, uid, "cfg_shop_name")
        await reply(
            f"🏪 <b>Edit Shop Name</b>\n\n"
            f"Current: <b>{esc(shop_name(d))}</b>\n\n"
            f"Send the new shop name:",
            kb_cancel()
        )
        return

    if action == "support":
        set_state(d, uid, "cfg_support")
        await reply(
            f"📞 <b>Edit Support Contacts</b>\n\n"
            f"Current: <code>{esc(support(d))}</code>\n\n"
            f"Send the new support (e.g. @user1 @user2):",
            kb_cancel()
        )
        return

    if action == "verify_ch":
        set_state(d, uid, "cfg_verify_ch")
        await reply(
            f"📡 <b>Edit Verify Channel</b>\n\n"
            f"Current: <code>{verify_channel(d)}</code>\n\n"
            f"Send the channel ID (e.g. <code>-1001234567890</code>):",
            kb_cancel()
        )
        return

    if action == "prod_names":
        await reply(
            "📦 <b>Edit Product Names</b>\n\nSelect a product to rename:",
            kb_cfg_prod_names(d)
        )
        return

    if action.startswith("pn|"):
        _, k, idx_str = action.split("|", 2)
        idx     = int(idx_str)
        current = prod_name(k, idx, d)
        set_state(d, uid, f"cfg_pname|{k}|{idx}")
        await reply(
            f"📦 <b>Rename Product</b>\n\n"
            f"Current: <b>{esc(current)}</b>\n\n"
            f"Send the new name:",
            kb_cancel()
        )
        return

    if action == "prices_menu":
        await reply(
            "💰 <b>Edit Prices</b>\n\nSelect a product:",
            kb_cfg_prices_cats(d)
        )
        return

    if action.startswith("pp|"):
        _, k, idx_str = action.split("|", 2)
        idx   = int(idx_str)
        pname = prod_name(k, idx, d)
        await reply(
            f"💰 <b>Edit Prices — {esc(pname)}</b>\n\nSelect a duration:",
            kb_cfg_prices_durs(k, idx, d)
        )
        return

    if action.startswith("ppd|"):
        parts   = action.split("|")
        k       = parts[1]
        idx     = int(parts[2])
        dur_enc = parts[3]
        dur     = dur_enc.replace("~", " ")
        pname   = prod_name(k, idx, d)
        current = dict(prod_prices(k, idx, d)).get(dur, "?")
        set_state(d, uid, f"cfg_price|{k}|{idx}|{dur}")
        await reply(
            f"💰 <b>Edit Price</b>\n\n"
            f"Product: <b>{esc(pname)}</b>\n"
            f"Duration: <b>{esc(dur)}</b>\n"
            f"Current price: <b>${current}</b>\n\n"
            f"Send the new price (e.g. <code>12.00</code>):",
            kb_cancel()
        )
        return

# ═══════════════════════════════════════════════════════════════════════════════
#  CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════════════════════════
async def handle_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    await q.answer()
    d   = load()
    uid = q.from_user.id
    cb  = q.data

    # ── Login cancel ──────────────────────────────────────────────────────────
    if cb == "login_cancel":
        clear_state(d, uid)
        await q.message.reply_text(
            "Login cancelled. Use /start to try again.",
            parse_mode="HTML"
        )
        return

    if not is_verified(uid, d):
        await q.answer("Please enter your password first. Use /start", show_alert=True)
        return

    # ── Approve order ─────────────────────────────────────────────────────────
    if cb.startswith("approve|"):
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True); return
        order_id = cb[8:]
        order    = d.get("pending_orders", {}).get(order_id)
        if not order:
            await q.answer("Order not found or already processed.", show_alert=True)
            try: await q.edit_message_reply_markup(reply_markup=None)
            except Exception: pass
            return
        success = await deliver_product(order["user_id"], order, ctx)
        d2      = load()
        d2.get("pending_orders", {}).pop(order_id, None)
        save(d2)
        if success:
            await q.answer("✅ Approved! Product delivered.")
            try:
                await q.edit_message_caption(
                    caption=(q.message.caption or "") + "\n\n✅ <b>APPROVED</b>",
                    parse_mode="HTML", reply_markup=None)
            except Exception: pass
        else:
            await q.answer("❌ No stock available!", show_alert=True)
            try:
                await q.edit_message_caption(
                    caption=(q.message.caption or "") + "\n\n⚠️ <b>APPROVED but NO STOCK</b>",
                    parse_mode="HTML", reply_markup=None)
            except Exception: pass
            try:
                await ctx.bot.send_message(chat_id=order["user_id"],
                    text=f"⚠️ <b>Payment approved but out of stock.</b>\nContact admin: {support(d)}",
                    parse_mode="HTML")
            except Exception: pass
        return

    # ── Deny order ────────────────────────────────────────────────────────────
    if cb.startswith("deny|"):
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True); return
        order_id = cb[5:]
        order    = d.get("pending_orders", {}).get(order_id)
        if not order:
            await q.answer("Order not found or already processed.", show_alert=True)
            try: await q.edit_message_reply_markup(reply_markup=None)
            except Exception: pass
            return
        d.get("pending_orders", {}).pop(order_id, None)
        save(d)
        await q.answer("❌ Denied.")
        try:
            await q.edit_message_caption(
                caption=(q.message.caption or "") + "\n\n❌ <b>DENIED</b>",
                parse_mode="HTML", reply_markup=None)
        except Exception: pass
        try:
            await ctx.bot.send_message(chat_id=order["user_id"],
                text=f"{CE_DENY} <b>Order Denied</b> — contact admin: {support(d)}",
                parse_mode="HTML")
        except Exception: pass
        return

    # ── Category / product browsing ───────────────────────────────────────────
    if cb.startswith("cat|"):
        k   = cb[4:]
        cat = BASE_MENU.get(k)
        if not cat: return
        txt = cat_msg(k, d)
        try:
            await q.edit_message_text(txt, parse_mode="HTML", reply_markup=kb_cat(k, d))
        except Exception:
            await q.message.reply_text(txt, parse_mode="HTML", reply_markup=kb_cat(k, d))
        return

    if cb.startswith("prod|"):
        _, k, si = cb.split("|"); i = int(si)
        cat = BASE_MENU.get(k)
        if not cat or i >= len(cat["products"]): return
        pname = prod_name(k, i, d)
        total = total_product_stock(k, i, d)
        txt   = (
            f"{cat['products'][i]['ce']} <b>{esc(pname)}</b>\n\n"
            f"{CE_STATUS} Status: Good &amp; Safe\n"
            f"📦 In stock: <b>{total}</b>\n\n"
            f"<b>Select a duration:</b>"
        )
        try:
            await q.edit_message_text(txt, parse_mode="HTML", reply_markup=kb_durations(k, i, d))
        except Exception:
            await q.message.reply_text(txt, parse_mode="HTML", reply_markup=kb_durations(k, i, d))
        return

    if cb.startswith("dur|"):
        _, k, si, dur, price = cb.split("|", 4); i = int(si)
        cat = BASE_MENU.get(k)
        if not cat or i >= len(cat["products"]): return
        pname = prod_name(k, i, d)
        qty   = slot_stock(k, i, dur, d)
        bal   = get_balance(uid, d)
        if qty == 0:
            txt = (
                f"{cat['products'][i]['ce']} <b>{esc(pname)}</b>\n"
                f"Duration: <b>{esc(dur)}</b>  |  Price: <b>${esc(price)}</b>\n\n"
                f"❌ <b>Out of stock.</b> Contact admin: {support(d)}"
            )
        elif bal < float(price):
            txt = (
                f"{cat['products'][i]['ce']} <b>{esc(pname)}</b>\n"
                f"Duration: <b>{esc(dur)}</b>  |  Price: <b>${esc(price)}</b>\n"
                f"{CE_WALLET} Your balance: <b>${bal:.2f}</b>\n\n"
                f"⚠️ <b>Insufficient balance.</b>\nContact admin to top up: {support(d)}"
            )
        else:
            txt = (
                f"{cat['products'][i]['ce']} <b>{esc(pname)}</b>\n"
                f"Duration: <b>{esc(dur)}</b>  |  Price: <b>${esc(price)}</b>\n"
                f"📦 In stock: <b>{qty}</b>\n"
                f"{CE_WALLET} Your balance: <b>${bal:.2f}</b>\n\n"
                f"Tap below to complete your purchase:"
            )
        kb = kb_buy_balance(k, i, dur, price) if (qty > 0 and bal >= float(price)) else \
             InlineKeyboardMarkup([[InlineKeyboardButton("⬅️  Back", callback_data=f"prod|{k}|{i}")]])
        try:
            await q.edit_message_text(txt, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await q.message.reply_text(txt, parse_mode="HTML", reply_markup=kb)
        return

    if cb.startswith("pay|"):
        parts  = cb.split("|", 6)
        method = parts[1]
        k, si, dur, price = parts[2], parts[3], parts[4], parts[5]; i = int(si)
        cat = BASE_MENU.get(k)
        if not cat or i >= len(cat["products"]): return

        if method == "bal":
            try:
                price_f = float(price)
            except ValueError:
                await q.answer("Invalid price.", show_alert=True); return
            bal = get_balance(uid, d)
            if bal < price_f:
                await q.answer(f"Insufficient balance. You have ${bal:.2f}", show_alert=True); return
            if slot_stock(k, i, dur, d) == 0:
                await q.answer("No stock! Contact admin.", show_alert=True); return
            d["balances"][str(uid)] = round(bal - price_f, 2)
            save(d)
            order   = {"k": k, "i": i, "dur": dur, "price": price, "method": "bal"}
            success = await deliver_product(uid, order, ctx)
            if success:
                try:
                    await q.edit_message_text(
                        f"{CE_SUCCESS} <b>Purchase Successful!</b>\n\n"
                        f"${price_f:.2f} deducted from balance.\n"
                        f"Remaining balance: <b>${d['balances'][str(uid)]:.2f}</b>\n\n"
                        f"Your key and file have been sent above! ⬆️",
                        parse_mode="HTML")
                except Exception: pass
            else:
                d2 = load()
                d2["balances"][str(uid)] = round(get_balance(uid, d2) + price_f, 2)
                save(d2)
                await q.answer("Out of stock! Balance refunded.", show_alert=True)
            return

    # ══════════════════════════════════════════════════════════════════════════
    #  SETTINGS CALLBACKS
    # ══════════════════════════════════════════════════════════════════════════
    if cb.startswith("cfg|"):
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        action = cb[4:]
        try:
            await _handle_cfg(action, q, uid, d)
        except Exception as e:
            logger.error(f"Settings error: {e}", exc_info=e)
            try:
                await q.message.reply_text(
                    f"⚠️ Settings error: <code>{esc(str(e))}</code>\n\nTry again or use /start",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        return

    # ══════════════════════════════════════════════════════════════════════════
    #  ADMIN FILE / KEY CALLBACKS
    # ══════════════════════════════════════════════════════════════════════════
    if cb.startswith("afc|"):
        if not is_admin(uid, d): await q.answer("Admins only.", show_alert=True); return
        cat_key = cb[4:]
        cat     = BASE_MENU.get(cat_key)
        if not cat: return
        await q.edit_message_text(
            f"📁 <b>Add File — {esc(cat['label'])}</b>\n\nSelect a product:",
            parse_mode="HTML", reply_markup=kb_adm_prods_files("f", cat_key, d))
        return

    if cb.startswith("afp|"):
        if not is_admin(uid, d): await q.answer("Admins only.", show_alert=True); return
        _, cat_key, idx_str = cb.split("|", 2); idx = int(idx_str)
        cat = BASE_MENU.get(cat_key)
        if not cat or idx >= len(cat["products"]): return
        pname    = prod_name(cat_key, idx, d)
        existing = files_count(cat_key, idx, d)
        set_state(d, uid, f"add_file_item|{cat_key}|{idx}")
        await q.edit_message_text(
            f"📁 <b>Add File — {esc(pname)}</b>\n\n"
            f"Currently in stock: <b>{existing} file(s)</b>\n\n"
            f"Send the file or link:\n"
            f"• IPA / ZIP → send as <b>document</b>\n"
            f"• Download link → send as <b>text</b>",
            parse_mode="HTML")
        return

    if cb.startswith("arc|"):
        if not is_admin(uid, d): await q.answer("Admins only.", show_alert=True); return
        cat_key = cb[4:]
        cat     = BASE_MENU.get(cat_key)
        if not cat: return
        await q.edit_message_text(
            f"🗑️ <b>Remove File — {esc(cat['label'])}</b>\n\nSelect a product:",
            parse_mode="HTML", reply_markup=kb_adm_prods_files("r", cat_key, d))
        return

    if cb.startswith("arp|"):
        if not is_admin(uid, d): await q.answer("Admins only.", show_alert=True); return
        _, cat_key, idx_str = cb.split("|", 2); idx = int(idx_str)
        cat = BASE_MENU.get(cat_key)
        if not cat or idx >= len(cat["products"]): return
        pname    = prod_name(cat_key, idx, d)
        existing = files_count(cat_key, idx, d)
        if existing == 0:
            await q.edit_message_text(
                f"📁 <b>{esc(pname)}</b> has no files in stock.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="adm|remove_file")]]))
            return
        nf        = peek_file(cat_key, idx, d)
        file_desc = f"\nNext: <code>{esc(nf.get('name','?'))}</code> [{nf.get('type','?')}]" if nf else ""
        await q.edit_message_text(
            f"🗑️ <b>Remove File — {esc(pname)}</b>\n\nFiles: <b>{existing}</b>{file_desc}\n\nWhat to do?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Remove Next File", callback_data=f"arc_confirm|{cat_key}|{idx}")],
                [InlineKeyboardButton("🗑️ Clear ALL Files",  callback_data=f"arc_all|{cat_key}|{idx}")],
                [InlineKeyboardButton("⬅️ Back",             callback_data="adm|remove_file")],
            ]))
        return

    if cb.startswith("arc_confirm|"):
        if not is_admin(uid, d): await q.answer("Admins only.", show_alert=True); return
        _, cat_key, idx_str = cb.split("|", 2); idx = int(idx_str)
        removed = pop_file(cat_key, idx, d)
        if removed:
            await q.edit_message_text(
                f"✅ File removed: <code>{esc(removed.get('name','?'))}</code>\nRemaining: <b>{files_count(cat_key, idx, d)}</b>",
                parse_mode="HTML")
        else:
            await q.edit_message_text("No files to remove.")
        return

    if cb.startswith("arc_all|"):
        if not is_admin(uid, d): await q.answer("Admins only.", show_alert=True); return
        _, cat_key, idx_str = cb.split("|", 2); idx = int(idx_str)
        d.setdefault("files", {})[file_slot(cat_key, idx)] = []
        save(d)
        await q.edit_message_text(
            f"✅ All files cleared for <b>{esc(prod_name(cat_key, idx, d))}</b>.", parse_mode="HTML")
        return

    if cb.startswith("akc|"):
        if not is_admin(uid, d): await q.answer("Admins only.", show_alert=True); return
        cat_key = cb[4:]
        cat     = BASE_MENU.get(cat_key)
        if not cat: return
        await q.edit_message_text(
            f"🔑 <b>Add Keys — {esc(cat['label'])}</b>\n\nSelect a product:",
            parse_mode="HTML", reply_markup=kb_adm_prods_keys(cat_key, d))
        return

    if cb.startswith("akp|"):
        if not is_admin(uid, d): await q.answer("Admins only.", show_alert=True); return
        _, cat_key, idx_str = cb.split("|", 2); idx = int(idx_str)
        cat = BASE_MENU.get(cat_key)
        if not cat or idx >= len(cat["products"]): return
        pname = prod_name(cat_key, idx, d)
        await q.edit_message_text(
            f"🔑 <b>Add Keys — {esc(pname)}</b>\n\nSelect a duration:",
            parse_mode="HTML", reply_markup=kb_adm_durs_keys(cat_key, idx, d))
        return

    if cb.startswith("akd|"):
        if not is_admin(uid, d): await q.answer("Admins only.", show_alert=True); return
        parts   = cb.split("|"); cat_key = parts[1]; idx = int(parts[2]); dur_enc = parts[3]
        dur     = dur_enc.replace("~", " ")
        cat     = BASE_MENU.get(cat_key)
        if not cat or idx >= len(cat["products"]): return
        pname    = prod_name(cat_key, idx, d)
        existing = keys_count(cat_key, idx, dur, d)
        set_state(d, uid, f"add_keys_item|{cat_key}|{idx}|{dur}")
        await q.edit_message_text(
            f"🔑 <b>Add Keys</b>\n\n"
            f"Product: <b>{esc(pname)}</b>\n"
            f"Duration: <b>{esc(dur)}</b>\n"
            f"Current stock: <b>{existing}</b>\n\n"
            f"Send keys — <b>one per line</b>:",
            parse_mode="HTML")
        return

    # ── Admin panel actions ───────────────────────────────────────────────────
    if cb.startswith("adm|"):
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True); return
        action = cb[4:]

        if action == "back":
            await q.message.reply_text(
                f"{CE_ADMIN} <b>Admin Panel — {esc(shop_name(d))}</b>\n\nChoose an action:",
                parse_mode="HTML", reply_markup=kb_admin_panel())

        elif action == "add_keys":
            clear_state(d, uid)
            await q.message.reply_text(
                "🔑 <b>Add Keys</b>\n\nSelect a category:",
                parse_mode="HTML", reply_markup=kb_adm_cats_keys(d))

        elif action == "add_files":
            clear_state(d, uid)
            await q.message.reply_text(
                "📁 <b>Add File</b>\n\nSelect a category:",
                parse_mode="HTML", reply_markup=kb_adm_cats_files("f", d))

        elif action == "remove_file":
            clear_state(d, uid)
            await q.message.reply_text(
                "🗑️ <b>Remove File</b>\n\nSelect a category:",
                parse_mode="HTML", reply_markup=kb_adm_cats_files("r", d))

        elif action == "view_keys":
            DOT_ON = CE_AVAIL; DOT_OFF = CE_UNAVAIL
            lines  = ["🔑 <b>Keys Stock</b>\n"]
            for k in CAT_ORDER:
                cat = BASE_MENU[k]
                lines.append(f"📂 <b>{esc(cat['label'])}</b>")
                for i in range(len(cat["products"])):
                    pname = prod_name(k, i, d)
                    for dur, _ in prod_prices(k, i, d):
                        qty = keys_count(k, i, dur, d)
                        dot = DOT_ON if qty > 0 else DOT_OFF
                        lines.append(f"  {dot} {esc(pname)} — {esc(dur)}: <b>{qty}</b>")
                lines.append("")
            full = "\n".join(lines)
            limit, chunk = 4000, ""
            for line in full.split("\n"):
                if len(chunk) + len(line) + 1 > limit:
                    if chunk:
                        try: await q.message.reply_text(chunk.strip(), parse_mode="HTML")
                        except Exception: await q.message.reply_text(chunk.strip())
                        await asyncio.sleep(0.15)
                    chunk = line
                else:
                    chunk = chunk + "\n" + line if chunk else line
            if chunk.strip():
                try: await q.message.reply_text(chunk.strip(), parse_mode="HTML")
                except Exception: await q.message.reply_text(chunk.strip())

        elif action == "view_files":
            DOT_ON = CE_AVAIL; DOT_OFF = CE_UNAVAIL
            lines  = ["📁 <b>Files Stock</b>\n"]
            for k in CAT_ORDER:
                cat = BASE_MENU[k]
                lines.append(f"📂 <b>{esc(cat['label'])}</b>")
                for i in range(len(cat["products"])):
                    pname = prod_name(k, i, d)
                    fqty  = files_count(k, i, d)
                    dot   = DOT_ON if fqty > 0 else DOT_OFF
                    lines.append(f"  {dot} {esc(pname)}: <b>{fqty} file{'s' if fqty != 1 else ''}</b>")
                lines.append("")
            full = "\n".join(lines)
            limit, chunk = 4000, ""
            for line in full.split("\n"):
                if len(chunk) + len(line) + 1 > limit:
                    if chunk:
                        try: await q.message.reply_text(chunk.strip(), parse_mode="HTML")
                        except Exception: await q.message.reply_text(chunk.strip())
                        await asyncio.sleep(0.15)
                    chunk = line
                else:
                    chunk = chunk + "\n" + line if chunk else line
            if chunk.strip():
                try: await q.message.reply_text(chunk.strip(), parse_mode="HTML")
                except Exception: await q.message.reply_text(chunk.strip())

        elif action == "add_bal":
            set_state(d, uid, "add_bal")
            await q.message.reply_text(
                "<b>Add Balance</b>\n\nSend: <code>USER_ID AMOUNT</code>",
                parse_mode="HTML", reply_markup=kb_cancel())

        elif action == "ded_bal":
            set_state(d, uid, "ded_bal")
            await q.message.reply_text(
                "<b>Deduct Balance</b>\n\nSend: <code>USER_ID AMOUNT</code>",
                parse_mode="HTML", reply_markup=kb_cancel())

        elif action == "chk_bal":
            set_state(d, uid, "chk_bal")
            await q.message.reply_text(
                "<b>Check Balance</b>\n\nSend the Telegram User ID:",
                parse_mode="HTML", reply_markup=kb_cancel())

        elif action == "add_admin":
            set_state(d, uid, "admin_id")
            await q.message.reply_text(
                "<b>Add Admin</b>\n\nSend the Telegram User ID of the new admin:",
                parse_mode="HTML", reply_markup=kb_cancel())

        elif action == "creds":
            creds = d.get("credentials", [])
            header = "🔐 <b>Credentials</b>\n\nTap a credential to <b>delete</b> it.\n\n"
            if creds:
                lines = "\n".join(f"• <b>{esc(c.get('label','—'))}</b>  |  <code>{esc(c.get('password',''))}</code>" for c in creds)
                header += lines
            else:
                header += "<i>No credentials yet. Add one below.</i>"
            await q.message.reply_text(header, parse_mode="HTML", reply_markup=kb_creds(d))

        elif action == "add_cred":
            set_state(d, uid, "add_cred")
            await q.message.reply_text(
                "🔐 <b>Add Credential</b>\n\nSend in this format:\n<code>LABEL PASSWORD</code>\n\nExample: <code>VIP user123</code>",
                parse_mode="HTML", reply_markup=kb_cancel())

        elif action.startswith("del_cred|"):
            idx = int(action.split("|")[1])
            creds = d.get("credentials", [])
            if 0 <= idx < len(creds):
                removed = creds.pop(idx)
                save(d)
                await q.message.reply_text(
                    f"✅ Credential deleted: <b>{esc(removed.get('label','?'))}</b>  (<code>{esc(removed.get('password',''))}</code>)",
                    parse_mode="HTML", reply_markup=kb_creds(d))
            else:
                await q.answer("Not found.", show_alert=True)

        elif action == "broadcast":
            set_state(d, uid, "broadcast")
            await q.message.reply_text(
                "📢 <b>Broadcast</b>\n\nType your message (HTML supported):",
                parse_mode="HTML", reply_markup=kb_cancel())

        elif action == "clear":
            await q.message.reply_text(
                "⚠️ <b>Clear ALL keys?</b> This cannot be undone.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Yes, clear all", callback_data="adm|confirm_clear"),
                    InlineKeyboardButton("Cancel",         callback_data="adm|cancel"),
                ]]))

        elif action == "confirm_clear":
            d["keys"] = {}; save(d)
            try: await q.edit_message_text("✅ All keys cleared.")
            except Exception: await q.message.reply_text("✅ All keys cleared.")

        elif action == "cancel":
            clear_state(d, uid)
            try: await q.edit_message_text("Cancelled.")
            except Exception: await q.message.reply_text("Cancelled.")

        return


# ═══════════════════════════════════════════════════════════════════════════════
#  ERROR HANDLER
# ═══════════════════════════════════════════════════════════════════════════════
async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    err = ctx.error
    if isinstance(err, (Conflict, NetworkError, TimedOut)):
        logger.warning(f"Transient: {err}"); return
    logger.error(f"Unhandled error: {err}", exc_info=err)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    try:
        result = subprocess.run(["pgrep", "-f", "python3 bot.py"], capture_output=True, text=True)
        for pid_str in result.stdout.strip().splitlines():
            pid = int(pid_str.strip())
            if pid != os.getpid():
                try: os.kill(pid, signal.SIGTERM)
                except Exception: pass
    except Exception:
        pass

    for _f in [DATA_FILE, DATA_FILE + ".tmp", "bot_persistence"]:
        if Path(_f).exists():
            try: os.chmod(_f, 0o666)
            except Exception: pass

    persistence = PicklePersistence(filepath="bot_persistence")
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CallbackQueryHandler(handle_cb))
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.Document.ALL) & filters.ChatType.PRIVATE, handle_media))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_text))
    app.add_error_handler(on_error)

    logger.info(f"Starting {DEFAULT_SHOP_NAME} bot...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
