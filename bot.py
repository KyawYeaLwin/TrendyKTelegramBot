"""
bot.py  –  TrendyKBot (Telegram Menu Bot)
------------------------------------------
Menu flow:
  /start  →  Main Menu
             ├─ 📦 Check Stock
             │    ├─ 🔤 By Brand Name   →  Brand list (paged 10)
             │    │                          └─ [Brand]  →  Products (paged 10)
             │    │                                           └─ [Product]  →  Detail
             │    └─ 📂 By Product Type →  Type list (paged 10)
             │                               └─ [Type]   →  Products (paged 10)
             │                                                └─ [Product]  →  Detail
             └─ ℹ️  Help / Info

Pagination: 10 items per page, with ◀️ Prev / Next ▶️ buttons.
"""

import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import sheets_service as sheet

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

PAGE_SIZE = 10

# ═══════════════════════════ Keyboard helpers ══════════════════════════════════

def _kb(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(rows)


def main_menu_kb() -> InlineKeyboardMarkup:
    return _kb([
        [InlineKeyboardButton("📦 Check Stock", callback_data="menu_stock")],
        [InlineKeyboardButton("ℹ️  Help / Info", callback_data="menu_help")],
    ])


def back_main_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")]


def back_stock_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("🔙 Check Stock", callback_data="menu_stock")]


# ═══════════════════════════ Cache helpers ════════════════════════════════════

def _cached_brands(context: ContextTypes.DEFAULT_TYPE) -> list[str]:
    """Fetch brands from sheet (cached in bot_data for the session)."""
    if "brands" not in context.bot_data:
        context.bot_data["brands"] = sheet.get_categories()
    return context.bot_data["brands"]


def _cached_types(context: ContextTypes.DEFAULT_TYPE) -> list[str]:
    """Fetch product types from sheet (cached in bot_data for the session)."""
    if "types" not in context.bot_data:
        context.bot_data["types"] = sheet.get_product_types()
    return context.bot_data["types"]


def _paginate(items: list, page: int) -> tuple[list, int]:
    """Return (slice_for_page, total_count)."""
    start = page * PAGE_SIZE
    return items[start: start + PAGE_SIZE], len(items)


def _nav_row(page: int, total: int, base_cb: str) -> list[InlineKeyboardButton]:
    """Build Prev / Next navigation buttons."""
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"{base_cb}:{page - 1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"{base_cb}:{page + 1}"))
    return nav


# ═══════════════════════════ /start ═══════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    first = _esc(user.first_name) if user else "there"
    await update.message.reply_text(
        f"👋 Hello *{first}*\\! Welcome to *TrendyK Store*\\.\n\n"
        "What would you like to do today?",
        parse_mode="MarkdownV2",
        reply_markup=main_menu_kb(),
    )


# ═══════════════════════════ Callback router ══════════════════════════════════

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    # ── Main menu ──────────────────────────────────────────────────────────────
    if data == "menu_main":
        await query.edit_message_text(
            "🏠 *Main Menu*\n\nWhat would you like to do?",
            parse_mode="MarkdownV2",
            reply_markup=main_menu_kb(),
        )

    # ── Help ───────────────────────────────────────────────────────────────────
    elif data == "menu_help":
        await query.edit_message_text(
            "ℹ️ *TrendyK Bot Help*\n\n"
            "• *Check Stock By Brand Name* — Browse products by brand\\.\n"
            "• *Check Stock By Product Type* — Browse products by type\\.\n"
            "• Tap any product to see price, weight, stock, expiry \\& branch\\.\n"
            "• Use ◀️ Prev \\/ Next ▶️ to navigate through pages\\.\n\n"
            "For assistance please contact our team directly\\.",
            parse_mode="MarkdownV2",
            reply_markup=_kb([back_main_row()]),
        )

    # ── Stock sub-menu ─────────────────────────────────────────────────────────
    elif data == "menu_stock":
        await query.edit_message_text(
            "📦 *Check Stock*\n\nHow would you like to search?",
            parse_mode="MarkdownV2",
            reply_markup=_kb([
                [InlineKeyboardButton("🔤 By Brand Name",   callback_data="bl:0")],
                [InlineKeyboardButton("📂 By Product Type", callback_data="tl:0")],
                back_main_row(),
            ]),
        )

    # ── Brand Name list (paginated) ────────────────────────────────────────────
    elif data.startswith("bl:"):
        page = int(data.split(":")[1])
        await _show_brand_list(query, context, page)

    # ── Product Type list (paginated) ──────────────────────────────────────────
    elif data.startswith("tl:"):
        page = int(data.split(":")[1])
        await _show_type_list(query, context, page)

    # ── Products by Brand (paginated) ─────────────────────────────────────────
    elif data.startswith("bpl:"):
        # bpl:{brand_index}:{page}
        _, bi, pg = data.split(":")
        await _show_brand_products(query, context, int(bi), int(pg))

    # ── Products by Type (paginated) ──────────────────────────────────────────
    elif data.startswith("tpl:"):
        # tpl:{type_index}:{page}
        _, ti, pg = data.split(":")
        await _show_type_products(query, context, int(ti), int(pg))

    # ── Product detail ─────────────────────────────────────────────────────────
    elif data.startswith("pd:"):
        product_id = data[3:]
        await _show_product_detail(query, context, product_id)

    # ── Back from product detail ───────────────────────────────────────────────
    elif data == "pd_back":
        back_cb = context.user_data.get("pd_back_cb", "menu_stock")
        # Directly dispatch to the right view based on stored callback
        if back_cb.startswith("bpl:"):
            parts = back_cb.split(":")
            await _show_brand_products(query, context, int(parts[1]), int(parts[2]))
        elif back_cb.startswith("tpl:"):
            parts = back_cb.split(":")
            await _show_type_products(query, context, int(parts[1]), int(parts[2]))
        else:
            await query.edit_message_text(
                "📦 *Check Stock*\n\nHow would you like to search?",
                parse_mode="MarkdownV2",
                reply_markup=_kb([
                    [InlineKeyboardButton("🔤 By Brand Name",   callback_data="bl:0")],
                    [InlineKeyboardButton("📂 By Product Type", callback_data="tl:0")],
                    back_main_row(),
                ]),
            )

    else:
        await query.edit_message_text(
            "❓ Unknown action\\.",
            parse_mode="MarkdownV2",
            reply_markup=_kb([back_main_row()]),
        )


# ═══════════════════════════ View helpers ══════════════════════════════════════

async def _show_brand_list(query, context, page: int) -> None:
    """Display paginated brand (Brand Name) list."""
    brands = _cached_brands(context)

    if not brands:
        await query.edit_message_text(
            "⚠️ No brands found\\. Please check the Google Sheet\\.",
            parse_mode="MarkdownV2",
            reply_markup=_kb([back_stock_row(), back_main_row()]),
        )
        return

    items, total = _paginate(brands, page)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    rows = []
    for i, brand in enumerate(items):
        bi = page * PAGE_SIZE + i   # global index in brands list
        num = page * PAGE_SIZE + i + 1
        rows.append([InlineKeyboardButton(f"{num}. {brand}", callback_data=f"bpl:{bi}:0")])

    nav = _nav_row(page, total, "bl")
    if nav:
        rows.append(nav)

    rows.append(back_stock_row())
    rows.append(back_main_row())

    page_info = _esc(f"(Page {page + 1}/{total_pages})")
    await query.edit_message_text(
        f"🔤 *By Brand Name* {page_info}\n\nSelect a brand:",
        parse_mode="MarkdownV2",
        reply_markup=_kb(rows),
    )


async def _show_type_list(query, context, page: int) -> None:
    """Display paginated product type list."""
    types = _cached_types(context)

    if not types:
        await query.edit_message_text(
            "⚠️ No product types found\\. Please check the Google Sheet\\.",
            parse_mode="MarkdownV2",
            reply_markup=_kb([back_stock_row(), back_main_row()]),
        )
        return

    items, total = _paginate(types, page)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    rows = []
    for i, pt in enumerate(items):
        ti = page * PAGE_SIZE + i   # global index in types list
        num = page * PAGE_SIZE + i + 1
        rows.append([InlineKeyboardButton(f"{num}. {pt}", callback_data=f"tpl:{ti}:0")])

    nav = _nav_row(page, total, "tl")
    if nav:
        rows.append(nav)

    rows.append(back_stock_row())
    rows.append(back_main_row())

    page_info = _esc(f"(Page {page + 1}/{total_pages})")
    await query.edit_message_text(
        f"📂 *By Product Type* {page_info}\n\nSelect a product type:",
        parse_mode="MarkdownV2",
        reply_markup=_kb(rows),
    )


async def _show_brand_products(query, context, bi: int, page: int) -> None:
    """Display products for the brand at index bi, paginated."""
    brands = _cached_brands(context)
    if bi >= len(brands):
        await query.edit_message_text("❌ Brand not found\\.", parse_mode="MarkdownV2",
                                      reply_markup=_kb([back_stock_row()]))
        return

    brand = brands[bi]
    products = sheet.get_products_by_category(brand)
    await _show_product_list(
        query, context, products,
        title=f"🏷️ *{_esc(brand)}*",
        page=page,
        prod_page_cb=f"bpl:{bi}",
        back_list_cb=f"bl:{bi // PAGE_SIZE}",
    )


async def _show_type_products(query, context, ti: int, page: int) -> None:
    """Display products for the type at index ti, paginated."""
    types = _cached_types(context)
    if ti >= len(types):
        await query.edit_message_text("❌ Product type not found\\.", parse_mode="MarkdownV2",
                                      reply_markup=_kb([back_stock_row()]))
        return

    product_type = types[ti]
    products = sheet.get_products_by_type(product_type)
    await _show_product_list(
        query, context, products,
        title=f"📂 *{_esc(product_type)}*",
        page=page,
        prod_page_cb=f"tpl:{ti}",
        back_list_cb=f"tl:{ti // PAGE_SIZE}",
    )


async def _show_product_list(
    query, context,
    products: list[dict],
    title: str,
    page: int,
    prod_page_cb: str,   # e.g. "bpl:3"  → full cb will be "bpl:3:{page}"
    back_list_cb: str,   # e.g. "bl:0"   → back to the list page
) -> None:
    """Shared paginated product list renderer."""
    if not products:
        await query.edit_message_text(
            f"{title}\n\n⚠️ No products available in this selection\\.",
            parse_mode="MarkdownV2",
            reply_markup=_kb([
                [InlineKeyboardButton("🔙 Back", callback_data=back_list_cb)],
                back_stock_row(),
                back_main_row(),
            ]),
        )
        return

    items, total = _paginate(products, page)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    # Store back destination once for this page view
    context.user_data["pd_back_cb"] = f"{prod_page_cb}:{page}"

    rows = []
    for i, p in enumerate(items):
        num = page * PAGE_SIZE + i + 1
        label = f"{num}. {p['name']} ({p['available']} pcs)"
        rows.append([InlineKeyboardButton(label, callback_data=f"pd:{p['id']}")])

    nav = _nav_row(page, total, prod_page_cb)
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🔙 Back to List", callback_data=back_list_cb)])
    rows.append(back_stock_row())
    rows.append(back_main_row())

    page_info = _esc(f"(Page {page + 1}/{total_pages}  •  {total} items)")
    await query.edit_message_text(
        f"{title}\n\n{page_info}\n\nTap a product for details:",
        parse_mode="MarkdownV2",
        reply_markup=_kb(rows),
    )


async def _show_product_detail(query, context, product_id: str) -> None:
    """Display the detail card for a single product."""
    product = sheet.get_product_by_id(product_id)

    if not product:
        await query.edit_message_text(
            "❌ Product not found\\.",
            parse_mode="MarkdownV2",
            reply_markup=_kb([back_main_row()]),
        )
        return

    name  = _esc(product["name"])
    pid   = _esc(product["id"])
    size  = _esc(product["size"])         or "N/A"
    stock = _esc(product["available"])    or "N/A"
    expiry= _esc(product["expiry"])       or "N/A"
    ptype = _esc(product["product_type"]) or "N/A"

    text = (
        f"🛍️ *{name}*\n\n"
        f"🔖 Code: `{pid}`\n"
        f"📂 Type: {ptype}\n"
        f"📏 Size: {size}\n"
        f"📦 In Stock: {stock} pcs\n"
        f"📅 Expiry: {expiry}"
    )

    back_cb = context.user_data.get("pd_back_cb", "menu_stock")
    await query.edit_message_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=_kb([
            [InlineKeyboardButton("🔙 Back to Products", callback_data="pd_back")],
            back_stock_row(),
            back_main_row(),
        ]),
    )


# ═══════════════════════════ Utility ══════════════════════════════════════════

def _esc(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


# ═══════════════════════════ Main ═════════════════════════════════════════════

def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in your .env file.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu",  cmd_start))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("🤖 TrendyKBot is running…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
