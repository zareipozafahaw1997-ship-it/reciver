"""
handlers/admin.py
پنل مدیریت کامل — async
"""

from telethon import TelegramClient, events, Button
from keyboards.admin_kb import (
    admin_main_menu, admin_users_menu, admin_accounts_menu,
    admin_stats_menu, admin_subs_menu, admin_proxy_menu,
    admin_apis_menu, admin_channels_menu,
    seller_main_menu, seller_users_menu, seller_sub_menu,
    user_action_menu, back_to_admin,
)
from utils.helpers import admin_only, get_or_register_user, fmt_user, seller_or_admin
from utils.channel_logger import log_sale, log_error, send_backup_all
from utils.proxy_manager import fetch_proxies_from_webshare, test_proxy
from database.mongo import MongoDB
from database.redis_client import RedisClient
from config import BOT_NAME, ADMIN_IDS

# تعداد آیتم در هر صفحه
PAGE_SIZE = 8


def register_admin_handlers(client: TelegramClient) -> None:

    # ════════════════════════════════════════════════════════════
    #  /admin — ورود به پنل
    # ════════════════════════════════════════════════════════════
    @client.on(events.NewMessage(pattern="/admin"))
    async def cmd_admin(event):
        uid = event.sender_id
        await get_or_register_user(event)

        # ادمین اصلی
        if uid in ADMIN_IDS or await MongoDB.is_admin(uid):
            total_users    = await MongoDB.count_users()
            total_accounts = await MongoDB.count_all_accounts()
            online         = await RedisClient.count_online()
            await event.respond(
                f"👑 **پنل مدیریت {BOT_NAME}**\n\n"
                f"👥 کاربران: `{total_users}`\n"
                f"🔑 اکانت‌ها: `{total_accounts}`\n"
                f"🟢 آنلاین: `{online}`",
                buttons=admin_main_menu(),
            )
            return

        # ادمین فروش
        if await MongoDB.is_seller(uid):
            await event.respond(
                f"🛒 **پنل فروش**\n\nخوش آمدید!",
                buttons=seller_main_menu(),
            )
            return

        await event.respond("⛔ دسترسی ندارید!")

    # ── خانه پنل ────────────────────────────────────────────────
    @client.on(events.CallbackQuery(data="adm_home"))
    @admin_only
    async def cb_adm_home(event):
        total_users    = await MongoDB.count_users()
        total_accounts = await MongoDB.count_all_accounts()
        online         = await RedisClient.count_online()
        await event.edit(
            f"👑 **پنل مدیریت {BOT_NAME}**\n\n"
            f"👥 کاربران: `{total_users}`\n"
            f"🔑 اکانت‌ها: `{total_accounts}`\n"
            f"🟢 آنلاین: `{online}`",
            buttons=admin_main_menu(),
        )

    # ════════════════════════════════════════════════════════════
    #  پنل فروش
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="sel_home"))
    @seller_or_admin
    async def cb_sel_home(event):
        await event.edit("🛒 **پنل فروش**", buttons=seller_main_menu())

    @client.on(events.CallbackQuery(data="sel_sub"))
    @seller_or_admin
    async def cb_sel_sub(event):
        await event.edit("💎 **فروش اشتراک**\n\nعملیات را انتخاب کنید:",
                         buttons=seller_sub_menu())

    @client.on(events.CallbackQuery(data="sel_users"))
    @seller_or_admin
    async def cb_sel_users(event):
        await event.edit("👥 **مدیریت کاربران**\n\nعملیات را انتخاب کنید:",
                         buttons=seller_users_menu())

    # ════════════════════════════════════════════════════════════
    #  بخش کاربران
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_users"))
    @admin_only
    async def cb_adm_users(event):
        await event.edit(
            "👥 **مدیریت کاربران**\n\nعملیات مورد نظر را انتخاب کنید:",
            buttons=admin_users_menu(),
        )

    # ── لیست کاربران (صفحه‌بندی) ────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"adm_list_users"))
    @admin_only
    async def cb_list_users(event):
        await _show_users_page(event, page=0)

    @client.on(events.CallbackQuery(pattern=b"adm_users_page_"))
    @admin_only
    async def cb_users_page(event):
        page = int(event.data.decode().replace("adm_users_page_", ""))
        await _show_users_page(event, page=page)

    async def _show_users_page(event, page: int):
        users = await MongoDB.get_all_users()
        total = len(users)
        if not total:
            await event.edit("هیچ کاربری ثبت نشده!", buttons=back_to_admin("adm_users"))
            return

        start  = page * PAGE_SIZE
        end    = start + PAGE_SIZE
        chunk  = users[start:end]
        lines  = []
        for u in chunk:
            status = "🚫" if u.get("is_banned") else ("👑" if u.get("is_admin") else "👤")
            uname  = f"@{u['username']}" if u.get("username") else "—"
            lines.append(f"{status} `{u['user_id']}` | {u.get('full_name','؟')} | {uname}")

        text = (
            f"👥 **لیست کاربران** — صفحه {page+1}\n"
            f"📊 کل: `{total}` نفر\n\n"
            + "\n".join(lines)
        )

        # دکمه‌های صفحه‌بندی + انتخاب کاربر
        nav = []
        if page > 0:
            nav.append(Button.inline("◀️ قبلی", data=f"adm_users_page_{page-1}"))
        if end < total:
            nav.append(Button.inline("▶️ بعدی", data=f"adm_users_page_{page+1}"))

        buttons = []
        # دکمه هر کاربر برای مشاهده پروفایل
        for u in chunk:
            name = u.get("full_name", str(u["user_id"]))[:20]
            buttons.append([Button.inline(f"👤 {name}", data=f"adm_view_user_{u['user_id']}")])
        if nav:
            buttons.append(nav)
        buttons.append([Button.inline("🔙 بازگشت", data="adm_users")])

        await event.edit(text, buttons=buttons)

    # ── مشاهده پروفایل کاربر ────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"adm_view_user_"))
    @admin_only
    async def cb_view_user(event):
        target_id = int(event.data.decode().replace("adm_view_user_", ""))
        user = await MongoDB.get_user(target_id)
        if not user:
            await event.answer("کاربر پیدا نشد!", alert=True)
            return
        acc_active  = await MongoDB.count_user_accounts(target_id)
        acc_running = await MongoDB.count_user_accounts_running(target_id)
        acc_deleted = await MongoDB.count_user_accounts_deleted(target_id)
        acc_total   = await MongoDB.count_user_accounts_total(target_id)
        text = (
            fmt_user(user) +
            f"\n\n📊 **آمار اکانت‌ها**\n"
            f"🔑 فعال: `{acc_active}` | 🟢 روشن: `{acc_running}`\n"
            f"🗑 حذف‌شده: `{acc_deleted}` | 📦 کل: `{acc_total}`"
        )
        await event.edit(text, buttons=user_action_menu(target_id))

    # ── عملیات سریع روی کاربر از دکمه ──────────────────────────
    @client.on(events.CallbackQuery(pattern=b"adm_doban_"))
    @admin_only
    async def cb_do_ban(event):
        target_id = int(event.data.decode().replace("adm_doban_", ""))
        await MongoDB.ban_user(target_id)
        await RedisClient.invalidate_user(target_id)
        await MongoDB.log_action(event.sender_id, "ban_user", str(target_id))
        await event.answer("🚫 کاربر مسدود شد.", alert=True)
        user = await MongoDB.get_user(target_id)
        acc_count = await MongoDB.count_user_accounts(target_id)
        await event.edit(fmt_user(user) + f"\n🔑 اکانت‌ها: `{acc_count}`",
                         buttons=user_action_menu(target_id))

    @client.on(events.CallbackQuery(pattern=b"adm_dounban_"))
    @admin_only
    async def cb_do_unban(event):
        target_id = int(event.data.decode().replace("adm_dounban_", ""))
        await MongoDB.unban_user(target_id)
        await RedisClient.invalidate_user(target_id)
        await MongoDB.log_action(event.sender_id, "unban_user", str(target_id))
        await event.answer("✅ مسدودیت برداشته شد.", alert=True)
        user = await MongoDB.get_user(target_id)
        acc_count = await MongoDB.count_user_accounts(target_id)
        await event.edit(fmt_user(user) + f"\n🔑 اکانت‌ها: `{acc_count}`",
                         buttons=user_action_menu(target_id))

    @client.on(events.CallbackQuery(pattern=b"adm_doadmin_"))
    @admin_only
    async def cb_do_admin(event):
        target_id = int(event.data.decode().replace("adm_doadmin_", ""))
        user = await MongoDB.get_user(target_id)
        new_state = not user.get("is_admin", False)
        await MongoDB.set_admin(target_id, new_state)
        await RedisClient.invalidate_user(target_id)
        await MongoDB.log_action(event.sender_id, "toggle_admin", str(target_id))
        label = "👑 ادمین شد" if new_state else "❌ ادمین حذف شد"
        await event.answer(label, alert=True)
        user = await MongoDB.get_user(target_id)
        acc_count = await MongoDB.count_user_accounts(target_id)
        await event.edit(fmt_user(user) + f"\n🔑 اکانت‌ها: `{acc_count}`",
                         buttons=user_action_menu(target_id))

    # ── پیام به کاربر خاص از دکمه ───────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"adm_send_"))
    @admin_only
    async def cb_send_prompt(event):
        target_id = int(event.data.decode().replace("adm_send_", ""))
        uid = event.sender_id
        await RedisClient.set_state(uid, f"adm_msg_{target_id}")
        await event.edit(
            f"✉️ **ارسال پیام به کاربر** `{target_id}`\n\nپیام خود را بنویسید:",
            buttons=back_to_admin("adm_users"),
        )

    # ════════════════════════════════════════════════════════════
    #  بخش اکانت‌ها
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_accounts"))
    @admin_only
    async def cb_adm_accounts(event):
        total = await MongoDB.count_all_accounts()
        await event.edit(
            f"🔑 **مدیریت اکانت‌ها**\n\nمجموع اکانت‌های فعال: `{total}`",
            buttons=admin_accounts_menu(),
        )

    # ── همه اکانت‌ها (صفحه‌بندی) ────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"adm_all_accounts"))
    @admin_only
    async def cb_all_accounts(event):
        await _show_accounts_page(event, page=0)

    @client.on(events.CallbackQuery(pattern=b"adm_accounts_page_"))
    @admin_only
    async def cb_accounts_page(event):
        page = int(event.data.decode().replace("adm_accounts_page_", ""))
        await _show_accounts_page(event, page=page)

    async def _show_accounts_page(event, page: int):
        accounts = await MongoDB.get_all_accounts()
        total    = len(accounts)
        if not total:
            await event.edit("هیچ اکانتی ثبت نشده!", buttons=back_to_admin("adm_accounts"))
            return

        start = page * PAGE_SIZE
        end   = start + PAGE_SIZE
        chunk = accounts[start:end]

        lines = []
        for a in chunk:
            uname = f"@{a['tg_username']}" if a.get("tg_username") else "—"
            lines.append(
                f"🔑 `{a['account_id']}` | {a.get('tg_first_name','؟')} | "
                f"{uname} | 📱`{a.get('phone','—')}`"
            )

        text = (
            f"🔑 **همه اکانت‌ها** — صفحه {page+1}\n"
            f"📊 کل: `{total}` اکانت\n\n"
            + "\n".join(lines)
        )

        nav = []
        if page > 0:
            nav.append(Button.inline("◀️ قبلی", data=f"adm_accounts_page_{page-1}"))
        if end < total:
            nav.append(Button.inline("▶️ بعدی", data=f"adm_accounts_page_{page+1}"))

        buttons = []
        for a in chunk:
            label = f"🔑 {a.get('tg_first_name','؟')} — {a['account_id']}"
            buttons.append([Button.inline(label, data=f"adm_view_acc_{a['account_id']}")])
        if nav:
            buttons.append(nav)
        buttons.append([Button.inline("🔙 بازگشت", data="adm_accounts")])
        await event.edit(text, buttons=buttons)

    # ── مشاهده جزئیات اکانت ─────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"adm_view_acc_"))
    @admin_only
    async def cb_view_account(event):
        account_id = event.data.decode().replace("adm_view_acc_", "")
        acc = await MongoDB.get_account_by_id_admin(account_id)
        if not acc:
            await event.answer("اکانت پیدا نشد!", alert=True)
            return
        uname      = f"@{acc['tg_username']}" if acc.get("tg_username") else "ندارد"
        fullname   = f"{acc.get('tg_first_name','')} {acc.get('tg_last_name','')}".strip()
        created    = str(acc.get("created_at", ""))[:10]
        is_running = acc.get("is_running", True)
        status     = "🟢 روشن" if is_running else "🔴 خاموش"
        proxy      = acc.get("proxy_used")
        proxy_str  = f"`{proxy['host']}:{proxy['port']}`" if proxy else "ندارد"
        await event.edit(
            f"🔑 **جزئیات اکانت**\n\n"
            f"👤 نام: **{fullname or '—'}**\n"
            f"📌 یوزرنیم: {uname}\n"
            f"📱 شماره: `{acc.get('phone','—')}`\n"
            f"🆔 آیدی تلگرام: `{acc.get('tg_id','—')}`\n"
            f"🔖 کد اکانت: `{acc['account_id']}`\n"
            f"👤 مالک: `{acc.get('owner_id','—')}`\n"
            f"⚙️ API ID: `{acc.get('api_id','—')}`\n"
            f"🌐 پروکسی: {proxy_str}\n"
            f"⚡ وضعیت: {status}\n"
            f"📅 تاریخ ثبت: `{created}`",
            buttons=[
                [Button.inline("🗑 حذف اکانت", data=f"adm_del_acc_{account_id}")],
                [Button.inline("🔙 بازگشت",    data="adm_all_accounts")],
            ],
        )

    @client.on(events.CallbackQuery(pattern=b"adm_del_acc_"))
    @admin_only
    async def cb_adm_delete_account(event):
        account_id = event.data.decode().replace("adm_del_acc_", "")
        # دریافت اطلاعات اکانت قبل از حذف
        acc = await MongoDB.get_account_by_id_admin(account_id)
        if not acc:
            await event.answer("❌ اکانت پیدا نشد!", alert=True)
            return
        owner_id = acc.get("owner_id")
        # حذف از دیتابیس
        deleted = await MongoDB.delete_account(account_id, owner_id)
        if not deleted:
            await event.answer("❌ خطا در حذف!", alert=True)
            return
        # قطع اتصال از AccountManager
        from core.account_manager import AccountManager
        await AccountManager.get_instance().remove_account(account_id)
        # انتقال سشن فایل
        from utils.session_utils import move_session_to_deleted
        await move_session_to_deleted(acc.get("session_file", ""))
        await MongoDB.log_action(event.sender_id, "adm_delete_account", account_id)
        await event.answer("✅ اکانت حذف و سشن منتقل شد.", alert=True)
        await event.edit(
            f"🗑 **اکانت `{account_id}` حذف شد**\n\n"
            f"📱 شماره: `{acc.get('phone','—')}`\n"
            f"📁 سشن به پوشه deleted منتقل شد.",
            buttons=back_to_admin("adm_accounts"),
        )

    # ── آمار اکانت‌ها ────────────────────────────────────────────
    @client.on(events.CallbackQuery(data="adm_accounts_stats"))
    @admin_only
    async def cb_accounts_stats(event):
        from core.account_manager import AccountManager
        manager   = AccountManager.get_instance()
        total_db  = await MongoDB.count_all_accounts()
        loaded    = manager.count()
        connected = manager.connected_count()
        users     = await MongoDB.get_all_users()
        with_acc  = 0
        for u in users:
            cnt = await MongoDB.count_user_accounts(u["user_id"])
            if cnt > 0:
                with_acc += 1
        await event.edit(
            f"📊 **آمار اکانت‌ها**\n\n"
            f"📊 کل در دیتابیس: `{total_db}`\n"
            f"📦 لود شده: `{loaded}`\n"
            f"🟢 متصل: `{connected}`\n"
            f"🔴 قطع: `{loaded - connected}`\n"
            f"👥 کاربران دارای اکانت: `{with_acc}`",
            buttons=back_to_admin("adm_accounts"),
        )

    # ── جستجوی اکانت با شماره ───────────────────────────────────
    @client.on(events.CallbackQuery(data="adm_search_account"))
    @admin_only
    async def cb_search_account_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_search_account")
        await event.edit(
            "🔍 **جستجوی اکانت**\n\nشماره تلفن یا بخشی از آن را وارد کنید:",
            buttons=back_to_admin("adm_accounts"),
        )

    # ════════════════════════════════════════════════════════════
    #  وضعیت ربات (روشن/خاموش برای کاربران)
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_bot_status"))
    @admin_only
    async def cb_bot_status(event):
        active = await MongoDB.get_bot_status()
        status = "✅ روشن" if active else "❌ خاموش"
        await event.edit(
            f"⚡ **وضعیت ربات**\n\n"
            f"📌 وضعیت فعلی: {status}\n\n"
            f"وقتی خاموش باشه کاربران نمی‌تونن استفاده کنن.",
            buttons=[
                [Button.inline("🟢 روشن کردن",  data="adm_bot_on"),
                 Button.inline("🔴 خاموش کردن", data="adm_bot_off")],
                [Button.inline("🔙 بازگشت",     data="adm_home")],
            ],
        )

    @client.on(events.CallbackQuery(data="adm_bot_on"))
    @admin_only
    async def cb_bot_on(event):
        await MongoDB.set_bot_status(True)
        await MongoDB.log_action(event.sender_id, "bot_status", "on")
        await event.answer("✅ ربات روشن شد.", alert=True)
        await event.edit(
            "⚡ **وضعیت ربات**\n\n📌 وضعیت: ✅ روشن",
            buttons=[
                [Button.inline("🟢 روشن کردن",  data="adm_bot_on"),
                 Button.inline("🔴 خاموش کردن", data="adm_bot_off")],
                [Button.inline("🔙 بازگشت",     data="adm_home")],
            ],
        )

    @client.on(events.CallbackQuery(data="adm_bot_off"))
    @admin_only
    async def cb_bot_off(event):
        await MongoDB.set_bot_status(False)
        await MongoDB.log_action(event.sender_id, "bot_status", "off")
        await event.answer("🔴 ربات خاموش شد.", alert=True)
        await event.edit(
            "⚡ **وضعیت ربات**\n\n📌 وضعیت: ❌ خاموش",
            buttons=[
                [Button.inline("🟢 روشن کردن",  data="adm_bot_on"),
                 Button.inline("🔴 خاموش کردن", data="adm_bot_off")],
                [Button.inline("🔙 بازگشت",     data="adm_home")],
            ],
        )

    # ── وضعیت آنلاین اکانت‌ها ───────────────────────────────────
    @client.on(events.CallbackQuery(data="adm_accounts_online"))
    @admin_only
    async def cb_accounts_online(event):
        from core.account_manager import AccountManager
        manager   = AccountManager.get_instance()
        statuses  = manager.get_status()
        total     = len(statuses)
        connected = sum(1 for s in statuses if s["connected"])

        if not statuses:
            await event.edit(
                "🟢 **وضعیت اکانت‌ها**\n\nهیچ اکانتی لود نشده.",
                buttons=back_to_admin("adm_accounts"),
            )
            return

        lines = []
        for s in statuses[:30]:  # حداکثر ۳۰ تا نشون بده
            icon = "🟢" if s["connected"] else "🔴"
            lines.append(f"{icon} `{s['phone']}` — `{s['account_id']}`")

        text = (
            f"🟢 **وضعیت اکانت‌ها**\n\n"
            f"📦 کل لود شده: `{total}`\n"
            f"🟢 متصل: `{connected}` | 🔴 قطع: `{total - connected}`\n\n"
            + "\n".join(lines)
        )
        if total > 30:
            text += f"\n\n_... و {total - 30} اکانت دیگر_"

        await event.edit(text, buttons=back_to_admin("adm_accounts"))

    # ════════════════════════════════════════════════════════════
    #  آمار کامل
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_stats"))
    @admin_only
    async def cb_adm_stats(event):
        await event.edit("📊 **آمار ربات**\n\nنوع آمار را انتخاب کنید:",
                         buttons=admin_stats_menu())

    @client.on(events.CallbackQuery(data="adm_stats_users"))
    @admin_only
    async def cb_stats_users(event):
        total   = await MongoDB.count_users()
        banned  = await MongoDB.count_banned_users()
        admins  = await MongoDB.get_all_admins()
        online  = await RedisClient.count_online()
        await event.edit(
            f"👥 **آمار کاربران**\n\n"
            f"📊 کل کاربران: `{total}`\n"
            f"🟢 آنلاین: `{online}`\n"
            f"🚫 مسدود: `{banned}`\n"
            f"👑 ادمین‌ها: `{len(admins)}`\n"
            f"✅ فعال: `{total - banned}`",
            buttons=back_to_admin("adm_stats"),
        )

    @client.on(events.CallbackQuery(data="adm_stats_accounts"))
    @admin_only
    async def cb_stats_accounts(event):
        from core.account_manager import AccountManager
        manager   = AccountManager.get_instance()
        total_db  = await MongoDB.count_all_accounts()
        loaded    = manager.count()
        connected = manager.connected_count()
        await event.edit(
            f"🔑 **آمار اکانت‌ها**\n\n"
            f"📊 کل در دیتابیس: `{total_db}`\n"
            f"📦 لود شده: `{loaded}`\n"
            f"🟢 متصل: `{connected}`\n"
            f"🔴 قطع: `{loaded - connected}`",
            buttons=back_to_admin("adm_stats"),
        )

    @client.on(events.CallbackQuery(data="adm_online"))
    @admin_only
    async def cb_online(event):
        count = await RedisClient.count_online()
        await event.edit(
            f"🟢 **کاربران آنلاین**\n\nدر حال حاضر `{count}` کاربر آنلاین هستند.",
            buttons=back_to_admin("adm_stats"),
        )

    @client.on(events.CallbackQuery(data="adm_banned_list"))
    @admin_only
    async def cb_banned_list(event):
        banned = await MongoDB.get_banned_users()
        if not banned:
            await event.edit("هیچ کاربر مسدودی وجود ندارد.",
                             buttons=back_to_admin("adm_stats"))
            return
        lines = [
            f"🚫 `{u['user_id']}` — {u.get('full_name','؟')}"
            for u in banned[:20]
        ]
        await event.edit(
            f"🚫 **کاربران مسدود** ({len(banned)} نفر)\n\n" + "\n".join(lines),
            buttons=back_to_admin("adm_stats"),
        )

    # ════════════════════════════════════════════════════════════
    #  پیام همگانی
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_broadcast"))
    @admin_only
    async def cb_broadcast_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_broadcast")
        total = await MongoDB.count_users()
        await event.edit(
            f"📢 **ارسال پیام همگانی**\n\n"
            f"👥 پیام به `{total}` کاربر ارسال می‌شود.\n\n"
            f"پیام خود را بنویسید:",
            buttons=back_to_admin("adm_home"),
        )

    # ════════════════════════════════════════════════════════════
    #  پیام به کاربر خاص (از منوی اصلی)
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_msg_user"))
    @admin_only
    async def cb_msg_user_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_msg_ask_id")
        await event.edit(
            "✉️ **پیام به کاربر**\n\nآیدی عددی کاربر را وارد کنید:",
            buttons=back_to_admin("adm_home"),
        )

    # ════════════════════════════════════════════════════════════
    #  جستجوی کاربر / بن / آنبن / ادمین (از منوی کاربران)
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_search_user"))
    @seller_or_admin
    async def cb_search_user_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_search_user")
        await event.edit(
            "🔍 **جستجوی کاربر**\n\nآیدی عددی کاربر را وارد کنید:",
            buttons=back_to_admin("adm_users"),
        )

    @client.on(events.CallbackQuery(data="adm_ban_user"))
    @seller_or_admin
    async def cb_ban_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_ban_user")
        await event.edit(
            "🚫 **مسدود کردن کاربر**\n\nآیدی عددی کاربر را وارد کنید:",
            buttons=back_to_admin("adm_users"),
        )

    @client.on(events.CallbackQuery(data="adm_unban_user"))
    @seller_or_admin
    async def cb_unban_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_unban_user")
        await event.edit(
            "✅ **رفع مسدودیت**\n\nآیدی عددی کاربر را وارد کنید:",
            buttons=back_to_admin("adm_users"),
        )

    @client.on(events.CallbackQuery(data="adm_add_admin"))
    @admin_only
    async def cb_add_admin_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_add_admin")
        await event.edit(
            "👑 **افزودن ادمین**\n\nآیدی عددی کاربر را وارد کنید:",
            buttons=back_to_admin("adm_users"),
        )

    @client.on(events.CallbackQuery(data="adm_remove_admin"))
    @admin_only
    async def cb_remove_admin_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_remove_admin")
        await event.edit(
            "❌ **حذف ادمین**\n\nآیدی عددی ادمین را وارد کنید:",
            buttons=back_to_admin("adm_users"),
        )

    @client.on(events.CallbackQuery(data="adm_add_seller"))
    @admin_only
    async def cb_add_seller_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_add_seller")
        await event.edit(
            "🛒 **افزودن ادمین فروش**\n\nآیدی عددی کاربر را وارد کنید:",
            buttons=back_to_admin("adm_users"),
        )

    @client.on(events.CallbackQuery(data="adm_remove_seller"))
    @admin_only
    async def cb_remove_seller_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_remove_seller")
        await event.edit(
            "🗑 **حذف ادمین فروش**\n\nآیدی عددی کاربر را وارد کنید:",
            buttons=back_to_admin("adm_users"),
        )

    # ════════════════════════════════════════════════════════════
    #  بخش اشتراک‌ها
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_subs"))
    @admin_only
    async def cb_adm_subs(event):
        total_subs = await MongoDB.count_active_subscribers()
        total_users = await MongoDB.count_users()
        await event.edit(
            f"💎 **مدیریت اشتراک‌ها**\n\n"
            f"✅ مشترکین فعال: `{total_subs}`\n"
            f"👥 کل کاربران: `{total_users}`",
            buttons=admin_subs_menu(),
        )

    @client.on(events.CallbackQuery(data="adm_list_subs"))
    @seller_or_admin
    async def cb_list_subs(event):
        subs = await MongoDB.get_all_subscribers()
        if not subs:
            await event.edit("هیچ مشترک فعالی وجود ندارد.",
                             buttons=back_to_admin("adm_subs"))
            return
        from datetime import datetime, timezone
        from dateutil.parser import parse as dp
        now   = datetime.now(timezone.utc)
        lines = []
        for u in subs:
            exp = u.get("sub_expires_at")
            if exp:
                if isinstance(exp, str):
                    exp = dp(exp)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                days    = max(0, (exp - now).days)
                exp_str = str(exp)[:10]
            else:
                days, exp_str = 0, "—"
            uname = f"@{u['username']}" if u.get("username") else "—"
            lines.append(
                f"💎 `{u['user_id']}` | {u.get('full_name','؟')} | "
                f"{uname} | تا `{exp_str}` ({days} روز)"
            )
        await event.edit(
            f"💎 **مشترکین فعال** ({len(subs)} نفر)\n\n" + "\n".join(lines),
            buttons=back_to_admin("adm_subs"),
        )

    @client.on(events.CallbackQuery(data="adm_stats_subs"))
    @seller_or_admin
    async def cb_stats_subs(event):
        total_subs  = await MongoDB.count_active_subscribers()
        total_users = await MongoDB.count_users()
        no_sub      = total_users - total_subs
        await event.edit(
            f"📊 **آمار اشتراک‌ها**\n\n"
            f"💎 مشترکین فعال: `{total_subs}`\n"
            f"❌ بدون اشتراک: `{no_sub}`\n"
            f"👥 کل کاربران: `{total_users}`",
            buttons=back_to_admin("adm_subs"),
        )

    @client.on(events.CallbackQuery(data="adm_manual_sub"))
    @seller_or_admin
    async def cb_manual_sub_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_manual_sub_id")
        await event.edit(
            "➕ **اشتراک دستی**\n\nآیدی عددی کاربر را وارد کنید:",
            buttons=back_to_admin("adm_subs"),
        )

    # ── اشتراک سریع از پروفایل کاربر ───────────────────────────
    @client.on(events.CallbackQuery(pattern=b"adm_sub30_"))
    @admin_only
    async def cb_sub_30(event):
        target_id = int(event.data.decode().replace("adm_sub30_", ""))
        exp = await MongoDB.set_subscription(target_id, 30)
        await RedisClient.invalidate_user(target_id)
        await MongoDB.log_action(event.sender_id, "sub_30", str(target_id))
        await log_sale(event.sender_id, "sub_30", target_id, f"تا {str(exp)[:10]}")
        await event.answer(f"✅ اشتراک ۳۰ روزه فعال شد تا {str(exp)[:10]}", alert=True)
        user = await MongoDB.get_user(target_id)
        acc_count = await MongoDB.count_user_accounts(target_id)
        await event.edit(fmt_user(user) + f"\n🔑 اکانت‌ها: `{acc_count}`",
                         buttons=user_action_menu(target_id))

    @client.on(events.CallbackQuery(pattern=b"adm_sub90_"))
    @admin_only
    async def cb_sub_90(event):
        target_id = int(event.data.decode().replace("adm_sub90_", ""))
        exp = await MongoDB.set_subscription(target_id, 90)
        await RedisClient.invalidate_user(target_id)
        await MongoDB.log_action(event.sender_id, "sub_90", str(target_id))
        await log_sale(event.sender_id, "sub_90", target_id, f"تا {str(exp)[:10]}")
        await event.answer(f"✅ اشتراک ۹۰ روزه فعال شد تا {str(exp)[:10]}", alert=True)
        user = await MongoDB.get_user(target_id)
        acc_count = await MongoDB.count_user_accounts(target_id)
        await event.edit(fmt_user(user) + f"\n🔑 اکانت‌ها: `{acc_count}`",
                         buttons=user_action_menu(target_id))

    @client.on(events.CallbackQuery(pattern=b"adm_subrv_"))
    @admin_only
    async def cb_sub_revoke(event):
        target_id = int(event.data.decode().replace("adm_subrv_", ""))
        await MongoDB.revoke_subscription(target_id)
        await RedisClient.invalidate_user(target_id)
        await MongoDB.log_action(event.sender_id, "sub_revoke", str(target_id))
        await log_sale(event.sender_id, "sub_revoke", target_id)
        await event.answer("❌ اشتراک لغو شد.", alert=True)
        user = await MongoDB.get_user(target_id)
        acc_count = await MongoDB.count_user_accounts(target_id)
        await event.edit(fmt_user(user) + f"\n🔑 اکانت‌ها: `{acc_count}`",
                         buttons=user_action_menu(target_id))

    # ════════════════════════════════════════════════════════════
    #  دریافت کد از سشن اکانت
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_get_code"))
    @admin_only
    async def cb_get_code_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_get_code_phone")
        await event.edit(
            "📲 **دریافت کد از سشن**\n\n"
            "شماره اکانت را وارد کنید:\n_(مثلاً: `+989123456789`)_",
            buttons=back_to_admin("adm_home"),
        )

    # ════════════════════════════════════════════════════════════
    #  جوین اجباری
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_force_join"))
    @admin_only
    async def cb_force_join(event):
        cfg     = await MongoDB.get_force_join()
        enabled = cfg.get("enabled", False)
        channel = cfg.get("channel") or "ست نشده ❌"
        status  = "✅ فعال" if enabled else "❌ غیرفعال"
        await event.edit(
            f"📢 **جوین اجباری**\n\n"
            f"📌 کانال: `{channel}`\n"
            f"⚡ وضعیت: {status}",
            buttons=[
                [Button.inline("✏️ تنظیم کانال",      data="adm_fj_set")],
                [Button.inline("🟢 فعال کردن" if not enabled else "🔴 غیرفعال کردن",
                               data="adm_fj_toggle")],
                [Button.inline("🔙 بازگشت",            data="adm_home")],
            ],
        )

    @client.on(events.CallbackQuery(data="adm_fj_toggle"))
    @admin_only
    async def cb_fj_toggle(event):
        cfg     = await MongoDB.get_force_join()
        new_val = not cfg.get("enabled", False)
        await MongoDB.set_force_join(cfg.get("channel"), new_val)
        label = "✅ جوین اجباری فعال شد." if new_val else "❌ جوین اجباری غیرفعال شد."
        await event.answer(label, alert=True)
        # رفرش
        cfg     = await MongoDB.get_force_join()
        enabled = cfg.get("enabled", False)
        channel = cfg.get("channel") or "ست نشده ❌"
        status  = "✅ فعال" if enabled else "❌ غیرفعال"
        await event.edit(
            f"📢 **جوین اجباری**\n\n"
            f"📌 کانال: `{channel}`\n"
            f"⚡ وضعیت: {status}",
            buttons=[
                [Button.inline("✏️ تنظیم کانال",      data="adm_fj_set")],
                [Button.inline("🟢 فعال کردن" if not enabled else "🔴 غیرفعال کردن",
                               data="adm_fj_toggle")],
                [Button.inline("🔙 بازگشت",            data="adm_home")],
            ],
        )

    @client.on(events.CallbackQuery(data="adm_fj_set"))
    @admin_only
    async def cb_fj_set_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_fj_set_channel")
        await event.edit(
            "📢 **تنظیم کانال جوین اجباری**\n\n"
            "یوزرنیم یا آیدی کانال را وارد کنید:\n"
            "_(مثلاً: `@channel` یا `-1001234567890`)_",
            buttons=back_to_admin("adm_force_join"),
        )

    # ════════════════════════════════════════════════════════════
    #  تنظیم اسم ربات
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_set_botname"))
    @admin_only
    async def cb_set_botname(event):
        current = await MongoDB.get_bot_name()
        await RedisClient.set_state(event.sender_id, "adm_set_botname")
        await event.edit(
            f"🤖 **تنظیم اسم ربات**\n\n"
            f"اسم فعلی: **{current}**\n\n"
            f"اسم جدید را وارد کنید:",
            buttons=back_to_admin("adm_channels"),
        )

    # ════════════════════════════════════════════════════════════
    #  تنظیم پشتیبانی
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_set_support"))
    @admin_only
    async def cb_set_support(event):
        current  = await MongoDB.get_support_username()
        cur_text = f"`{current}`" if current else "ست نشده ❌"
        await RedisClient.set_state(event.sender_id, "adm_set_support")
        await event.edit(
            f"📞 **تنظیم پشتیبانی**\n\n"
            f"یوزرنیم فعلی: {cur_text}\n\n"
            f"یوزرنیم جدید را وارد کنید:\n_(مثلاً: `@username`)_",
            buttons=back_to_admin("adm_home"),
        )

    # ════════════════════════════════════════════════════════════
    #  تنظیم کانال‌ها
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_channels"))
    @admin_only
    async def cb_adm_channels(event):
        cfg = await MongoDB.get_channels()

        def val(key): return f"`{cfg[key]}`" if cfg.get(key) else "❌ ست نشده"

        text = (
            "📡 **تنظیمات کانال‌ها و ربات**\n\n"
            f"📸 سشن‌ها: {val('sessions_channel')}\n"
            f"🚨 ارورها: {val('errors_channel')}\n"
            f"💰 فروش: {val('sales_channel')}\n"
            f"💾 بکاپ: {val('backup_channel')}\n"
            f"📢 کانال جوین: {val('fj_channel')}\n"
            f"📞 پشتیبانی: {val('support')}\n"
            f"🤖 اسم ربات: `{await MongoDB.get_bot_name()}`"
        )
        await event.edit(text, buttons=admin_channels_menu(cfg))

    @client.on(events.CallbackQuery(data="adm_fj_toggle"))
    @admin_only
    async def cb_fj_toggle_from_channels(event):
        cfg     = await MongoDB.get_force_join()
        new_val = not cfg.get("enabled", False)
        await MongoDB.set_force_join(cfg.get("channel"), new_val)
        await MongoDB.log_action(event.sender_id, "force_join_toggle", str(new_val))
        label = "✅ جوین اجباری فعال شد." if new_val else "❌ جوین اجباری غیرفعال شد."
        await event.answer(label, alert=True)
        cfg = await MongoDB.get_channels()
        await event.edit("📡 **تنظیمات کانال‌ها و ربات**", buttons=admin_channels_menu(cfg))

    @client.on(events.CallbackQuery(data="adm_fj_set"))
    @admin_only
    async def cb_fj_set_from_channels(event):
        await RedisClient.set_state(event.sender_id, "adm_fj_set_channel")
        await event.edit(
            "📢 **کانال جوین اجباری**\n\nیوزرنیم یا آیدی کانال را وارد کنید:",
            buttons=back_to_admin("adm_channels"),
        )

    @client.on(events.CallbackQuery(data="adm_ch_sessions"))
    @admin_only
    async def cb_ch_sessions(event):
        await RedisClient.set_state(event.sender_id, "adm_ch_set_sessions")
        await event.edit(
            "📸 **کانال سشن‌ها**\n\nآیدی کانال را وارد کنید:\n_(مثلاً: `-1001234567890` یا `@channel`)_",
            buttons=back_to_admin("adm_channels"),
        )

    @client.on(events.CallbackQuery(data="adm_ch_errors"))
    @admin_only
    async def cb_ch_errors(event):
        await RedisClient.set_state(event.sender_id, "adm_ch_set_errors")
        await event.edit(
            "🚨 **کانال ارورها**\n\nآیدی کانال را وارد کنید:",
            buttons=back_to_admin("adm_channels"),
        )

    @client.on(events.CallbackQuery(data="adm_ch_sales"))
    @admin_only
    async def cb_ch_sales(event):
        await RedisClient.set_state(event.sender_id, "adm_ch_set_sales")
        await event.edit(
            "💰 **کانال فروش**\n\nآیدی کانال را وارد کنید:",
            buttons=back_to_admin("adm_channels"),
        )

    @client.on(events.CallbackQuery(data="adm_ch_backup"))
    @admin_only
    async def cb_ch_backup(event):
        await RedisClient.set_state(event.sender_id, "adm_ch_set_backup")
        await event.edit(
            "💾 **کانال بکاپ**\n\n"
            "آیدی کانال را وارد کنید:\n"
            "_(اگه ست نباشه بکاپ به ادمین فرستاده می‌شه)_",
            buttons=back_to_admin("adm_channels"),
        )

    @client.on(events.CallbackQuery(data="adm_ch_user_backup"))
    @admin_only
    async def cb_ch_user_backup_toggle(event):
        cfg     = await MongoDB.get_channels()
        new_val = not cfg.get("user_backup", False)
        await MongoDB.set_channel("user_backup", new_val)
        label = "✅ بکاپ کاربر فعال شد." if new_val else "❌ بکاپ کاربر غیرفعال شد."
        await event.answer(label, alert=True)
        cfg = await MongoDB.get_channels()
        await event.edit("📡 **تنظیمات کانال‌ها و ربات**", buttons=admin_channels_menu(cfg))

    @client.on(events.CallbackQuery(data="adm_ch_auto_backup"))
    @admin_only
    async def cb_ch_auto_backup_toggle(event):
        cfg     = await MongoDB.get_channels()
        new_val = not cfg.get("auto_backup", False)
        await MongoDB.set_channel("auto_backup", new_val)
        label = "✅ بکاپ خودکار فعال شد." if new_val else "❌ بکاپ خودکار غیرفعال شد."
        await event.answer(label, alert=True)
        cfg = await MongoDB.get_channels()
        await event.edit("📡 **تنظیمات کانال‌ها و ربات**", buttons=admin_channels_menu(cfg))

    @client.on(events.CallbackQuery(data="adm_backup_all"))
    @admin_only
    async def cb_backup_all(event):
        msg = await event.edit("⏳ در حال ساخت و ارسال بکاپ...")
        # اگه کانال ست نشده، مستقیم به ادمین بفرسته
        sent, failed = await send_backup_all(send_to=event.sender_id)
        if sent == 0 and failed == 0:
            await msg.edit(
                "❌ هیچ فایل سشنی پیدا نشد.",
                buttons=back_to_admin("adm_home"),
            )
        else:
            await msg.edit(
                f"💾 **بکاپ تمام شد**\n\n"
                f"✅ فایل‌های ارسال‌شده: `{sent}`\n"
                f"❌ خطا: `{failed}`",
                buttons=back_to_admin("adm_home"),
            )

    # ════════════════════════════════════════════════════════════
    #  تنظیم فوروارد کد
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_forward"))
    @admin_only
    async def cb_adm_forward(event):
        target = await MongoDB.get_forward_target()
        status = f"`{target}`" if target else "تنظیم نشده ❌"
        await event.edit(
            f"📨 **تنظیم فوروارد کد ورود**\n\n"
            f"📌 یوزرنیم فعلی: {status}\n\n"
            f"همه کدهای ورود اکانت‌ها به این یوزرنیم فوروارد می‌شن.\n"
            f"اگه چتی نداشته باشه، اکانت اول یه پیام می‌فرسته تا باز بشه.",
            buttons=[
                [Button.inline("✏️ تنظیم یوزرنیم",   data="adm_forward_set")],
                [Button.inline("❌ حذف تنظیم",        data="adm_forward_clear")],
                [Button.inline("🔙 بازگشت",           data="adm_home")],
            ],
        )

    @client.on(events.CallbackQuery(data="adm_forward_set"))
    @admin_only
    async def cb_forward_set_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_forward_set")
        await event.edit(
            "📨 **تنظیم یوزرنیم فوروارد**\n\n"
            "یوزرنیم مقصد را وارد کنید:\n"
            "_(مثلاً: `@username` یا `username`)_",
            buttons=back_to_admin("adm_forward"),
        )

    @client.on(events.CallbackQuery(data="adm_forward_clear"))
    @admin_only
    async def cb_forward_clear(event):
        await MongoDB.clear_forward_target()
        await MongoDB.log_action(event.sender_id, "forward_clear", "")
        await event.edit(
            "✅ **تنظیم فوروارد حذف شد**\n\nدیگه کدی فوروارد نمی‌شه.",
            buttons=back_to_admin("adm_home"),
        )

    # ════════════════════════════════════════════════════════════
    #  بخش API Credentials
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_apis"))
    @admin_only
    async def cb_adm_apis(event):
        creds = await MongoDB.get_all_api_credentials()
        await event.edit(
            f"⚙️ **مدیریت API Credentials**\n\n"
            f"📦 تعداد API فعال: `{len(creds)}`\n"
            f"🔄 ربات رندوم از اینها استفاده می‌کنه",
            buttons=admin_apis_menu(),
        )

    @client.on(events.CallbackQuery(data="adm_api_list"))
    @admin_only
    async def cb_api_list(event):
        creds = await MongoDB.get_all_api_credentials()
        if not creds:
            await event.edit(
                "⚙️ **API Credentials**\n\nهیچ API‌ای اضافه نشده!",
                buttons=back_to_admin("adm_apis"),
            )
            return
        buttons = []
        for c in creds:
            label = f"⚙️ {c['label']} — ID: {c['api_id']}"
            buttons.append([Button.inline(label, data=f"adm_api_view_{c['cred_id']}")])
        buttons.append([Button.inline("🔙 بازگشت", data="adm_apis")])
        lines = [f"• `{c['cred_id']}` | **{c['label']}** | api_id: `{c['api_id']}`"
                 for c in creds]
        await event.edit(
            f"⚙️ **لیست API Credentials** ({len(creds)} عدد)\n\n" + "\n".join(lines),
            buttons=buttons,
        )

    @client.on(events.CallbackQuery(pattern=b"adm_api_view_"))
    @admin_only
    async def cb_api_view(event):
        cred_id = event.data.decode().replace("adm_api_view_", "")
        cred    = await MongoDB.get_api_credential(cred_id)
        if not cred:
            await event.answer("❌ پیدا نشد!", alert=True)
            return
        await event.edit(
            f"⚙️ **جزئیات API**\n\n"
            f"🏷 لیبل: **{cred['label']}**\n"
            f"🆔 API ID: `{cred['api_id']}`\n"
            f"🔑 API Hash: `{cred['api_hash'][:8]}...`\n"
            f"🔖 Cred ID: `{cred['cred_id']}`\n"
            f"👤 اضافه‌کننده: `{cred.get('added_by','—')}`\n"
            f"📅 تاریخ: `{str(cred.get('created_at',''))[:10]}`",
            buttons=[
                [Button.inline("🗑 حذف این API", data=f"adm_api_del_{cred_id}")],
                [Button.inline("🔙 بازگشت",      data="adm_api_list")],
            ],
        )

    @client.on(events.CallbackQuery(pattern=b"adm_api_del_"))
    @admin_only
    async def cb_api_delete(event):
        cred_id = event.data.decode().replace("adm_api_del_", "")
        deleted = await MongoDB.delete_api_credential(cred_id)
        if deleted:
            await event.answer("✅ API حذف شد.", alert=True)
            await MongoDB.log_action(event.sender_id, "api_delete", cred_id)
        else:
            await event.answer("❌ خطا در حذف!", alert=True)
        creds = await MongoDB.get_all_api_credentials()
        await event.edit(
            f"⚙️ **API Credentials** — {len(creds)} عدد",
            buttons=admin_apis_menu(),
        )

    @client.on(events.CallbackQuery(data="adm_api_add"))
    @admin_only
    async def cb_api_add_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_api_add_label")
        await event.edit(
            "⚙️ **افزودن API جدید**\n\n"
            "**مرحله ۱/۳** — یک لیبل (نام) برای این API وارد کنید:\n"
            "_(مثلاً: API شخصی، API سرور ۱)_",
            buttons=back_to_admin("adm_apis"),
        )

    # ════════════════════════════════════════════════════════════
    #  بخش پروکسی
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_proxy"))
    @admin_only
    async def cb_adm_proxy(event):
        cfg     = await MongoDB.get_proxy_settings()
        enabled = cfg.get("enabled", False)
        has_key = bool(cfg.get("api_key"))
        key_preview = f"`{cfg['api_key'][:8]}...`" if has_key else "تنظیم نشده"
        await event.edit(
            f"🌐 **مدیریت پروکسی Webshare**\n\n"
            f"📌 وضعیت: {'✅ فعال' if enabled else '❌ غیرفعال'}\n"
            f"🔑 API Key: {key_preview}\n"
            f"📦 پروکسی‌های کش: `{len(cfg.get('proxies') or [])}`",
            buttons=admin_proxy_menu(enabled, has_key),
        )

    @client.on(events.CallbackQuery(data="adm_proxy_status"))
    @admin_only
    async def cb_proxy_status(event):
        cfg = await MongoDB.get_proxy_settings()
        await event.answer(
            f"وضعیت: {'✅ فعال' if cfg.get('enabled') else '❌ غیرفعال'}",
            alert=True,
        )

    @client.on(events.CallbackQuery(data="adm_proxy_toggle"))
    @admin_only
    async def cb_proxy_toggle(event):
        cfg     = await MongoDB.get_proxy_settings()
        new_val = not cfg.get("enabled", False)
        await MongoDB.set_proxy_enabled(new_val)
        await MongoDB.log_action(event.sender_id, "proxy_toggle", str(new_val))
        label = "✅ پروکسی فعال شد." if new_val else "❌ پروکسی غیرفعال شد."
        await event.answer(label, alert=True)
        # رفرش منو
        cfg     = await MongoDB.get_proxy_settings()
        has_key = bool(cfg.get("api_key"))
        await event.edit(
            f"🌐 **مدیریت پروکسی Webshare**\n\n"
            f"📌 وضعیت: {'✅ فعال' if new_val else '❌ غیرفعال'}\n"
            f"🔑 API Key: {'تنظیم شده' if has_key else 'تنظیم نشده'}\n"
            f"📦 پروکسی‌های کش: `{len(cfg.get('proxies') or [])}`",
            buttons=admin_proxy_menu(new_val, has_key),
        )

    @client.on(events.CallbackQuery(data="adm_proxy_setkey"))
    @admin_only
    async def cb_proxy_setkey_prompt(event):
        await RedisClient.set_state(event.sender_id, "adm_proxy_setkey")
        await event.edit(
            "🔑 **تنظیم API Key پروکسی**\n\n"
            "کلید API خود را از [webshare.io](https://proxy.webshare.io) دریافت کنید.\n\n"
            "API Key را وارد کنید:",
            buttons=back_to_admin("adm_proxy"),
        )

    @client.on(events.CallbackQuery(data="adm_proxy_test"))
    @admin_only
    async def cb_proxy_test(event):
        cfg     = await MongoDB.get_proxy_settings()
        api_key = cfg.get("api_key")
        if not api_key:
            await event.answer("❌ ابتدا API Key تنظیم کنید!", alert=True)
            return
        msg = await event.edit("⏳ در حال دریافت پروکسی از Webshare و تست...")
        try:
            import random
            proxies = await fetch_proxies_from_webshare(api_key)
            if not proxies:
                await event.edit("❌ هیچ پروکسی دریافت نشد.", buttons=back_to_admin("adm_proxy"))
                return
            p  = random.choice(proxies)
            ok = await test_proxy(p["host"], p["port"], p["username"], p["password"])
            result = "✅ پروکسی کار می‌کند!" if ok else "❌ پروکسی پاسخ نداد."
            await event.edit(
                f"🧪 **تست پروکسی**\n\n"
                f"🌐 `{p['host']}:{p['port']}`\n"
                f"📦 کل پروکسی‌های موجود: `{len(proxies)}`\n"
                f"نتیجه: {result}",
                buttons=back_to_admin("adm_proxy"),
            )
        except Exception as e:
            await event.edit(
                f"❌ **خطا**\n\n`{e}`",
                buttons=back_to_admin("adm_proxy"),
            )

    # ════════════════════════════════════════════════════════════
    #  لاگ‌ها
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="adm_logs"))
    @admin_only
    async def cb_logs(event):
        logs = await MongoDB.get_logs(limit=15)
        if not logs:
            await event.answer("لاگی وجود ندارد!", alert=True)
            return
        lines = [
            f"• `{l['user_id']}` — **{l['action']}**"
            f"{(' — ' + l['detail']) if l.get('detail') else ''}\n"
            f"  🕐 {str(l.get('created_at',''))[:16]}"
            for l in logs
        ]
        await event.edit(
            "📋 **آخرین لاگ‌ها** (۱۵ مورد)\n\n" + "\n".join(lines),
            buttons=back_to_admin("adm_home"),
        )

    # ════════════════════════════════════════════════════════════
    #  FSM — پردازش پیام‌های متنی ادمین
    # ════════════════════════════════════════════════════════════
    @client.on(events.NewMessage)
    async def handle_admin_fsm(event):
        if not event.is_private or event.via_bot:
            return

        uid   = event.sender_id
        state = await RedisClient.get_state(uid)

        if not state or not state.startswith("adm_"):
            return

        text = event.raw_text.strip()

        # ── جستجوی کاربر ────────────────────────────────────────
        if state == "adm_search_user":
            await RedisClient.clear_state(uid)
            if not text.isdigit():
                await event.respond("❌ آیدی باید عددی باشد.",
                                    buttons=back_to_admin("adm_users"))
                return
            user = await MongoDB.get_user(int(text))
            if not user:
                await event.respond("❌ کاربری با این آیدی پیدا نشد.",
                                    buttons=back_to_admin("adm_users"))
                return
            acc_count = await MongoDB.count_user_accounts(int(text))
            await event.respond(
                fmt_user(user) + f"\n🔑 اکانت‌ها: `{acc_count}`",
                buttons=user_action_menu(int(text)),
            )

        # ── مسدود کردن ──────────────────────────────────────────
        elif state == "adm_ban_user":
            await RedisClient.clear_state(uid)
            if not text.isdigit():
                await event.respond("❌ آیدی باید عددی باشد.",
                                    buttons=back_to_admin("adm_users"))
                return
            target = int(text)
            await MongoDB.ban_user(target)
            await RedisClient.invalidate_user(target)
            await MongoDB.log_action(uid, "ban_user", str(target))
            await event.respond(f"🚫 کاربر `{target}` مسدود شد.",
                                buttons=back_to_admin("adm_users"))

        # ── رفع مسدودیت ─────────────────────────────────────────
        elif state == "adm_unban_user":
            await RedisClient.clear_state(uid)
            if not text.isdigit():
                await event.respond("❌ آیدی باید عددی باشد.",
                                    buttons=back_to_admin("adm_users"))
                return
            target = int(text)
            await MongoDB.unban_user(target)
            await RedisClient.invalidate_user(target)
            await MongoDB.log_action(uid, "unban_user", str(target))
            await event.respond(f"✅ مسدودیت کاربر `{target}` برداشته شد.",
                                buttons=back_to_admin("adm_users"))

        # ── افزودن فروشنده ──────────────────────────────────────
        elif state == "adm_add_seller":
            await RedisClient.clear_state(uid)
            if not text.isdigit():
                await event.respond("❌ آیدی باید عددی باشد.",
                                    buttons=back_to_admin("adm_users"))
                return
            target = int(text)
            await MongoDB.set_seller(target, True)
            await RedisClient.invalidate_user(target)
            await MongoDB.log_action(uid, "add_seller", str(target))
            await event.respond(f"🛒 کاربر `{target}` ادمین فروش شد.",
                                buttons=back_to_admin("adm_users"))

        # ── حذف فروشنده ─────────────────────────────────────────
        elif state == "adm_remove_seller":
            await RedisClient.clear_state(uid)
            if not text.isdigit():
                await event.respond("❌ آیدی باید عددی باشد.",
                                    buttons=back_to_admin("adm_users"))
                return
            target = int(text)
            await MongoDB.set_seller(target, False)
            await RedisClient.invalidate_user(target)
            await MongoDB.log_action(uid, "remove_seller", str(target))
            await event.respond(f"🗑 ادمین فروش `{target}` حذف شد.",
                                buttons=back_to_admin("adm_users"))

        # ── افزودن ادمین ────────────────────────────────────────
        elif state == "adm_add_admin":
            await RedisClient.clear_state(uid)
            if not text.isdigit():
                await event.respond("❌ آیدی باید عددی باشد.",
                                    buttons=back_to_admin("adm_users"))
                return
            target = int(text)
            await MongoDB.set_admin(target, True)
            await RedisClient.invalidate_user(target)
            await MongoDB.log_action(uid, "add_admin", str(target))
            await event.respond(f"👑 کاربر `{target}` ادمین شد.",
                                buttons=back_to_admin("adm_users"))

        # ── حذف ادمین ───────────────────────────────────────────
        elif state == "adm_remove_admin":
            await RedisClient.clear_state(uid)
            if not text.isdigit():
                await event.respond("❌ آیدی باید عددی باشد.",
                                    buttons=back_to_admin("adm_users"))
                return
            target = int(text)
            await MongoDB.set_admin(target, False)
            await RedisClient.invalidate_user(target)
            await MongoDB.log_action(uid, "remove_admin", str(target))
            await event.respond(f"❌ ادمین `{target}` حذف شد.",
                                buttons=back_to_admin("adm_users"))

        # ── پیام همگانی ─────────────────────────────────────────
        elif state == "adm_broadcast":
            await RedisClient.clear_state(uid)
            users = await MongoDB.get_all_users()
            sent, failed = 0, 0
            msg = await event.respond("⏳ در حال ارسال...")
            for u in users:
                try:
                    await client.send_message(
                        u["user_id"],
                        f"📢 **پیام از مدیریت**\n\n{text}",
                    )
                    sent += 1
                except Exception:
                    failed += 1
            await msg.edit(
                f"📢 **ارسال همگانی تمام شد**\n\n"
                f"✅ موفق: `{sent}`\n"
                f"❌ ناموفق: `{failed}`",
                buttons=back_to_admin("adm_home"),
            )
            await MongoDB.log_action(uid, "broadcast", f"sent={sent} failed={failed}")

        # ── پیام به کاربر — دریافت آیدی ────────────────────────
        elif state == "adm_msg_ask_id":
            if not text.isdigit():
                await event.respond("❌ آیدی باید عددی باشد.",
                                    buttons=back_to_admin("adm_home"))
                return
            target = int(text)
            user = await MongoDB.get_user(target)
            if not user:
                await RedisClient.clear_state(uid)
                await event.respond("❌ کاربری با این آیدی پیدا نشد.",
                                    buttons=back_to_admin("adm_home"))
                return
            await RedisClient.set_state(uid, f"adm_msg_{target}")
            name = user.get("full_name", str(target))
            await event.respond(
                f"✉️ **ارسال پیام به {name}** (`{target}`)\n\nپیام خود را بنویسید:",
                buttons=back_to_admin("adm_home"),
            )

        # ── پیام به کاربر — ارسال پیام ──────────────────────────
        elif state.startswith("adm_msg_"):
            target = int(state.replace("adm_msg_", ""))
            await RedisClient.clear_state(uid)
            try:
                await client.send_message(
                    target,
                    f"✉️ **پیام از مدیریت**\n\n{text}",
                )
                await event.respond(
                    f"✅ پیام به کاربر `{target}` ارسال شد.",
                    buttons=back_to_admin("adm_home"),
                )
                await MongoDB.log_action(uid, "msg_user", str(target))
            except Exception as e:
                await event.respond(
                    f"❌ خطا در ارسال: `{e}`",
                    buttons=back_to_admin("adm_home"),
                )

        # ── جستجوی اکانت با شماره ───────────────────────────────
        elif state == "adm_search_account":
            await RedisClient.clear_state(uid)
            results = await MongoDB.search_account_by_phone(text)
            if not results:
                await event.respond("❌ اکانتی با این شماره پیدا نشد.",
                                    buttons=back_to_admin("adm_accounts"))
                return
            lines = []
            for a in results:
                uname = f"@{a['tg_username']}" if a.get("tg_username") else "—"
                lines.append(
                    f"🔑 `{a['account_id']}` | {a.get('tg_first_name','؟')} | "
                    f"{uname} | 📱`{a.get('phone','—')}` | مالک: `{a.get('owner_id','—')}`"
                )
            await event.respond(
                f"🔍 **نتایج جستجو** ({len(results)} مورد)\n\n" + "\n".join(lines),
                buttons=back_to_admin("adm_accounts"),
            )

        # ── دریافت کد از سشن — دریافت شماره ───────────────────
        elif state == "adm_get_code_phone":
            await RedisClient.clear_state(uid)
            phone = text.strip()
            if not phone.startswith("+"):
                phone = "+" + phone

            from core.account_manager import AccountManager
            manager = AccountManager.get_instance()
            managed = manager.get_account_by_phone(phone)

            if not managed:
                await event.respond(
                    f"❌ اکانت `{phone}` در سیستم پیدا نشد یا آنلاین نیست.",
                    buttons=back_to_admin("adm_home"),
                )
                return

            if not managed.client or not managed.client.is_connected():
                await event.respond(
                    f"❌ اکانت `{phone}` متصل نیست.",
                    buttons=back_to_admin("adm_home"),
                )
                return

            msg = await event.respond(f"⏳ `{phone}`")

            code = await managed.request_code_for_admin(uid, timeout=120)

            if code:
                await msg.edit(
                    f"✅ **کد دریافت شد!**\n\n"
                    f"📱 شماره: `{phone}`\n"
                    f"🔑 کد: `{code}`",
                    buttons=back_to_admin("adm_home"),
                )
                await MongoDB.log_action(uid, "get_code", phone)
            else:
                await msg.edit(
                    f"⏰ **کد دریافت نشد**\n\n"
                    f"تایم‌اوت شد. دوباره تلاش کنید.",
                    buttons=back_to_admin("adm_home"),
                )

        # ── تنظیم کانال جوین اجباری ────────────────────────────
        elif state == "adm_fj_set_channel":
            await RedisClient.clear_state(uid)
            channel = text.strip()
            if not channel:
                await event.respond("❌ کانال نامعتبر است.",
                                    buttons=back_to_admin("adm_force_join"))
                return
            cfg = await MongoDB.get_force_join()
            await MongoDB.set_force_join(channel, cfg.get("enabled", False))
            await MongoDB.log_action(uid, "set_force_join", channel)
            await event.respond(
                f"✅ کانال جوین اجباری ثبت شد: `{channel}`",
                buttons=back_to_admin("adm_force_join"),
            )

        # ── تنظیم کانال‌ها ──────────────────────────────────────
        elif state in ("adm_ch_set_sessions", "adm_ch_set_errors",
                       "adm_ch_set_sales", "adm_ch_set_backup"):
            await RedisClient.clear_state(uid)
            channel_map = {
                "adm_ch_set_sessions": "sessions_channel",
                "adm_ch_set_errors":   "errors_channel",
                "adm_ch_set_sales":    "sales_channel",
                "adm_ch_set_backup":   "backup_channel",
            }
            key = channel_map[state]
            val = text.strip()
            await MongoDB.set_channel(key, val)
            await MongoDB.log_action(uid, f"set_{key}", val)
            cfg = await MongoDB.get_channels()
            await event.respond(
                f"✅ کانال ثبت شد: `{val}`",
                buttons=back_to_admin("adm_channels"),
            )

        # ── تنظیم کانال جوین اجباری ────────────────────────────
        elif state == "adm_fj_set_channel":
            await RedisClient.clear_state(uid)
            channel = text.strip()
            # نرمال‌سازی — فقط @username نگه بدار
            if channel.startswith("https://t.me/"):
                channel = "@" + channel.replace("https://t.me/", "").split("/")[0].split("?")[0]
            if not channel.startswith("@"):
                channel = "@" + channel.lstrip("@")
            cfg = await MongoDB.get_force_join()
            await MongoDB.set_force_join(channel, cfg.get("enabled", False))
            await MongoDB.log_action(uid, "set_force_join", channel)
            await event.respond(
                f"✅ کانال جوین اجباری ثبت شد: `{channel}`",
                buttons=back_to_admin("adm_channels"),
            )

        # ── تنظیم اسم ربات ──────────────────────────────────────
        elif state == "adm_set_botname":
            await RedisClient.clear_state(uid)
            name = text.strip()
            if not name:
                await event.respond("❌ اسم نامعتبر است.",
                                    buttons=back_to_admin("adm_channels"))
                return
            await MongoDB.set_bot_name(name)
            await MongoDB.log_action(uid, "set_bot_name", name)
            await event.respond(
                f"✅ اسم ربات تغییر کرد: **{name}**",
                buttons=back_to_admin("adm_channels"),
            )

        # ── تنظیم پشتیبانی ──────────────────────────────────────
        elif state == "adm_set_support":
            await RedisClient.clear_state(uid)
            username = text.strip().lstrip("@")
            if not username:
                await event.respond("❌ یوزرنیم نامعتبر است.",
                                    buttons=back_to_admin("adm_channels"))
                return
            await MongoDB.set_support_username(f"@{username}")
            await MongoDB.log_action(uid, "set_support", f"@{username}")
            await event.respond(
                f"✅ یوزرنیم پشتیبانی ثبت شد: `@{username}`",
                buttons=back_to_admin("adm_channels"),
            )

        # ── تنظیم یوزرنیم فوروارد ──────────────────────────────
        elif state == "adm_forward_set":
            await RedisClient.clear_state(uid)
            target = text.strip().lstrip("@")
            if not target:
                await event.respond("❌ یوزرنیم نامعتبر است.",
                                    buttons=back_to_admin("adm_forward"))
                return
            await MongoDB.set_forward_target(f"@{target}")
            await MongoDB.log_action(uid, "forward_set", f"@{target}")
            await event.respond(
                f"✅ **یوزرنیم فوروارد تنظیم شد!**\n\n"
                f"📨 کدها به `@{target}` فوروارد می‌شن.\n\n"
                f"⚠️ مطمئن شو که اکانت‌ها با این یوزرنیم چت دارن\n"
                f"(موقع اتصال اکانت‌ها خودکار چت باز می‌شه)",
                buttons=back_to_admin("adm_forward"),
            )

        # ── افزودن API — مرحله ۱: لیبل ─────────────────────────
        elif state == "adm_api_add_label":
            await RedisClient.set_temp(uid, "api_label", text)
            await RedisClient.set_state(uid, "adm_api_add_id")
            await event.respond(
                f"✅ لیبل: **{text}**\n\n"
                "**مرحله ۲/۳** — API ID را وارد کنید:\n_(فقط عدد)_",
                buttons=back_to_admin("adm_apis"),
            )

        # ── افزودن API — مرحله ۲: API ID ────────────────────────
        elif state == "adm_api_add_id":
            if not text.isdigit():
                await event.respond("❌ API ID باید عددی باشد.",
                                    buttons=back_to_admin("adm_apis"))
                return
            await RedisClient.set_temp(uid, "api_id", text)
            await RedisClient.set_state(uid, "adm_api_add_hash")
            await event.respond(
                "**مرحله ۳/۳** — API Hash را وارد کنید:",
                buttons=back_to_admin("adm_apis"),
            )

        # ── افزودن API — مرحله ۳: API Hash ──────────────────────
        elif state == "adm_api_add_hash":
            await RedisClient.clear_state(uid)
            label   = await RedisClient.get_temp(uid, "api_label") or "بدون نام"
            api_id  = int(await RedisClient.get_temp(uid, "api_id") or "0")
            api_hash = text.strip()
            await RedisClient.clear_temp(uid)
            if not api_hash or len(api_hash) < 10:
                await event.respond("❌ API Hash نامعتبر است.",
                                    buttons=back_to_admin("adm_apis"))
                return
            cred_id = await MongoDB.add_api_credential(label, api_id, api_hash, uid)
            await MongoDB.log_action(uid, "api_add", cred_id)
            await event.respond(
                f"✅ **API اضافه شد!**\n\n"
                f"🏷 لیبل: **{label}**\n"
                f"🆔 API ID: `{api_id}`\n"
                f"🔖 Cred ID: `{cred_id}`",
                buttons=back_to_admin("adm_apis"),
            )

        # ── تنظیم API Key پروکسی ────────────────────────────────
        elif state == "adm_proxy_setkey":
            await RedisClient.clear_state(uid)
            api_key = text.strip()
            if len(api_key) < 10:
                await event.respond("❌ API Key نامعتبر است.",
                                    buttons=back_to_admin("adm_proxy"))
                return
            # تست اتصال به Webshare
            msg = await event.respond("⏳ در حال تأیید API Key...")
            try:
                proxies = await fetch_proxies_from_webshare(api_key)
                await MongoDB.set_proxy_api_key(api_key)
                await MongoDB.update_proxy_cache(proxies)
                await MongoDB.log_action(uid, "proxy_setkey", f"proxies={len(proxies)}")
                await msg.edit(
                    f"✅ **API Key تنظیم شد!**\n\n"
                    f"📦 تعداد پروکسی دریافت‌شده: `{len(proxies)}`\n\n"
                    f"برای فعال‌سازی از دکمه **فعال کردن** استفاده کنید.",
                    buttons=back_to_admin("adm_proxy"),
                )
            except Exception as e:
                await msg.edit(
                    f"❌ **خطا در تأیید API Key**\n\n`{e}`\n\nAPI Key ذخیره نشد.",
                    buttons=back_to_admin("adm_proxy"),
                )
        elif state == "adm_manual_sub_id":
            if not text.isdigit():
                await event.respond("❌ آیدی باید عددی باشد.",
                                    buttons=back_to_admin("adm_subs"))
                return
            target = int(text)
            user = await MongoDB.get_user(target)
            if not user:
                await RedisClient.clear_state(uid)
                await event.respond("❌ کاربری با این آیدی پیدا نشد.",
                                    buttons=back_to_admin("adm_subs"))
                return
            await RedisClient.set_temp(uid, "sub_target", str(target))
            await RedisClient.set_state(uid, "adm_manual_sub_days")
            name = user.get("full_name", str(target))
            await event.respond(
                f"💎 **اشتراک برای {name}** (`{target}`)\n\n"
                f"تعداد روز اشتراک را وارد کنید:\n_(مثلاً: 30 یا 90 یا 365)_",
                buttons=back_to_admin("adm_subs"),
            )

        # ── اشتراک دستی — دریافت تعداد روز ─────────────────────
        elif state == "adm_manual_sub_days":
            await RedisClient.clear_state(uid)
            if not text.isdigit() or int(text) <= 0:
                await event.respond("❌ تعداد روز باید عدد مثبت باشد.",
                                    buttons=back_to_admin("adm_subs"))
                return
            days       = int(text)
            target_str = await RedisClient.get_temp(uid, "sub_target")
            await RedisClient.clear_temp(uid)
            if not target_str:
                await event.respond("❌ خطا. دوباره تلاش کنید.",
                                    buttons=back_to_admin("adm_subs"))
                return
            target = int(target_str)

            # وضعیت قبل از تمدید
            from datetime import datetime, timezone
            old_info   = await MongoDB.get_subscription_info(target)
            old_active = old_info["active"]
            old_days   = old_info["days_left"]

            exp = await MongoDB.set_subscription(target, days)
            await RedisClient.invalidate_user(target)
            await MongoDB.log_action(uid, f"sub_{days}d", str(target))
            await log_sale(uid, "sub_manual", target, f"{days} روز — تا {str(exp)[:10]}")

            # متن وضعیت قبلی
            if old_active:
                prev_status = f"✅ فعال ({old_days} روز مانده)"
            else:
                prev_status = "❌ نداشت"

            # اطلاع به کاربر
            try:
                await client.send_message(
                    target,
                    f"🎉 **اشتراک شما {'تمدید' if old_active else 'فعال'} شد!**\n\n"
                    f"💎 مدت اضافه‌شده: `{days}` روز\n"
                    f"📅 تاریخ انقضا: `{str(exp)[:10]}`\n\n"
                    f"اکنون می‌توانید از تمام امکانات ربات استفاده کنید ✅",
                )
            except Exception:
                pass

            user = await MongoDB.get_user(target)
            name = user.get("full_name", str(target)) if user else str(target)

            await event.respond(
                f"✅ **اشتراک {'تمدید' if old_active else 'فعال'} شد**\n\n"
                f"👤 کاربر: **{name}** (`{target}`)\n"
                f"📊 وضعیت قبلی: {prev_status}\n"
                f"➕ اضافه‌شده: `{days}` روز\n"
                f"📅 انقضای جدید: `{str(exp)[:10]}`\n"
                f"⏳ کل روز مانده: `{old_days + days if old_active else days}` روز",
                buttons=back_to_admin("adm_subs"),
            )
