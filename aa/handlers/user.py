"""
handlers/user.py
هندلرهای async کاربر — چندزبانه (فارسی / English / 中文)
"""

from telethon import TelegramClient, events, Button
from keyboards.user_kb import accounts_list_menu, account_detail_menu
from utils.helpers import get_or_register_user, ban_check, rate_limit, subscription_required, get_user_lang, check_force_join, get_bot_name
from utils.tg_login import LoginSession
from database.mongo import MongoDB
from database.redis_client import RedisClient
from locales import t, LANGUAGES
from config import BOT_NAME, BOT_VERSION


def _main_menu(lang: str) -> list:
    return [
        [Button.inline(t(lang,"btn_add_account"), data="user_add_account"),
         Button.inline(t(lang,"btn_my_profile"),  data="user_profile")],
        [Button.inline(t(lang,"btn_my_accounts"), data="user_accounts")],
        [Button.inline(t(lang,"btn_support"),     data="user_support"),
         Button.inline(t(lang,"btn_about"),       data="user_about")],
        [Button.inline(t(lang,"btn_api_select"),  data="user_api_select"),
         Button.inline(t(lang,"btn_language"),    data="user_lang")],
    ]


def _lang_keyboard() -> list:
    return [[Button.inline(f"{v['flag']} {v['name']}", data=f"setlang_{k}")]
            for k, v in LANGUAGES.items()]


def register_user_handlers(client: TelegramClient) -> None:

    # ════════════════════════════════════════════════════════════
    #  /start
    # ════════════════════════════════════════════════════════════
    @client.on(events.NewMessage(pattern="/start"))
    async def cmd_start(event):
        if not event.is_private:
            return
        user = await get_or_register_user(event)
        if not user:
            return
        if user.get("is_banned"):
            lang = await get_user_lang(event.sender_id)
            await event.respond(t(lang, "banned_msg"))
            return

        uid = event.sender_id

        # ۱. اول انتخاب زبان
        if not user.get("lang"):
            await event.respond(t("fa", "choose_lang"), buttons=_lang_keyboard())
            return

        lang = user["lang"]

        # ۲. چک وضعیت ربات
        bot_active = await MongoDB.get_bot_status()
        if not bot_active:
            msg = "🔴 ربات در حال حاضر غیرفعال است." if lang == "fa" else \
                  "🔴 Bot is currently unavailable." if lang == "en" else \
                  "🔴 机器人暂时不可用。"
            await event.respond(msg)
            return

        # ۳. جوین اجباری
        from config import ADMIN_IDS as _AIDS
        if uid not in _AIDS and not await MongoDB.is_admin(uid):
            is_member, channel = await check_force_join(client, uid)
            if not is_member:
                ch_clean = channel.lstrip("@") if channel else ""
                msg = (
                    "⚠️ **برای استفاده از ربات باید عضو کانال ما باشید!**"
                    if lang == "fa" else
                    "⚠️ **You must join our channel to use this bot!**"
                    if lang == "en" else
                    "⚠️ **您必须加入我们的频道才能使用此机器人！**"
                )
                await event.respond(msg, buttons=[
                    [Button.url("📢 عضویت" if lang == "fa" else ("📢 Join" if lang == "en" else "📢 加入"),
                                f"https://t.me/{ch_clean}")],
                    [Button.inline("✅ عضو شدم" if lang == "fa" else ("✅ I joined" if lang == "en" else "✅ 我已加入"),
                                   data="check_join")],
                ])
                return

        # ۴. خوش‌آمدگویی
        bot_name = await get_bot_name()
        name = user.get("full_name", "کاربر")
        await event.respond(
            t(lang, "welcome", name=name, bot_name=bot_name),
            buttons=_main_menu(lang),
        )
        await MongoDB.log_action(event.sender_id, "start")

    # ── چک عضویت بعد از کلیک "عضو شدم" ────────────────────────
    @client.on(events.CallbackQuery(data="check_join"))
    async def cb_check_join(event):
        uid  = event.sender_id
        lang = await get_user_lang(uid)
        is_member, channel = await check_force_join(client, uid)
        if not is_member:
            msg = "❌ هنوز عضو نشدی!" if lang == "fa" else ("❌ You haven't joined yet!" if lang == "en" else "❌ 您还没有加入！")
            await event.answer(msg, alert=True)
            return
        # عضو شد — ادامه
        user = await get_or_register_user(event)
        if not user.get("lang"):
            await event.edit(t("fa", "choose_lang"), buttons=_lang_keyboard())
            return
        lang = user["lang"]
        name = user.get("full_name", "")
        bot_name = await get_bot_name()
        await event.edit(
            t(lang, "welcome", name=name, bot_name=bot_name),
            buttons=_main_menu(lang),
        )

    # ════════════════════════════════════════════════════════════
    #  انتخاب زبان
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(pattern=b"setlang_"))
    async def cb_set_lang(event):
        lang = event.data.decode().replace("setlang_", "")
        if lang not in LANGUAGES:
            await event.answer("❌", alert=True)
            return
        uid = event.sender_id
        await MongoDB.set_language(uid, lang)
        await RedisClient.set_lang(uid, lang)
        await RedisClient.invalidate_user(uid)

        user = await get_or_register_user(event)
        name = user.get("full_name", "") if user else ""
        await event.edit(
            t(lang, "lang_set") + "\n\n" +
            t(lang, "welcome", name=name, bot_name=BOT_NAME),
            buttons=_main_menu(lang),
        )
        await MongoDB.log_action(uid, "set_lang", lang)

    # ── تغییر زبان از منو ───────────────────────────────────────
    @client.on(events.CallbackQuery(data="user_lang"))
    @ban_check
    async def cb_change_lang(event):
        await event.edit(t("fa", "choose_lang"), buttons=_lang_keyboard())

    # ════════════════════════════════════════════════════════════
    #  خانه
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="user_home"))
    @ban_check
    async def cb_home(event):
        uid  = event.sender_id
        await LoginSession.destroy(uid)
        await RedisClient.clear_state(uid)
        await RedisClient.clear_temp(uid)

        # چک جوین اجباری
        from config import ADMIN_IDS as _AIDS
        if uid not in _AIDS and not await MongoDB.is_admin(uid):
            is_member, channel = await check_force_join(client, uid)
            if not is_member:
                lang     = await get_user_lang(uid)
                ch_clean = channel.lstrip("@") if channel else ""
                msg = (
                    "⚠️ **برای استفاده از ربات باید عضو کانال ما باشید!**"
                    if lang == "fa" else
                    "⚠️ **You must join our channel to use this bot!**"
                    if lang == "en" else
                    "⚠️ **您必须加入我们的频道才能使用此机器人！**"
                )
                await event.edit(msg, buttons=[
                    [Button.url("📢 عضویت" if lang == "fa" else ("📢 Join" if lang == "en" else "📢 加入"),
                                f"https://t.me/{ch_clean}")],
                    [Button.inline("✅ عضو شدم" if lang == "fa" else ("✅ I joined" if lang == "en" else "✅ 我已加入"),
                                   data="check_join")],
                ])
                return

        user = await get_or_register_user(event)
        lang = await get_user_lang(uid)
        name = user.get("full_name", "") if user else ""
        await event.edit(
            t(lang, "main_menu_text", name=name),
            buttons=_main_menu(lang),
        )

    # ════════════════════════════════════════════════════════════
    #  مشخصات من
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="user_profile"))
    @ban_check
    @rate_limit("profile", max_calls=10, window=60)
    async def cb_profile(event):
        uid  = event.sender_id
        lang = await get_user_lang(uid)
        user = await get_or_register_user(event)
        if not user:
            await event.answer("❌", alert=True)
            return
        from datetime import datetime, timezone
        exp = user.get("sub_expires_at")
        if exp:
            now = datetime.now(timezone.utc)
            if isinstance(exp, str):
                from dateutil.parser import parse
                exp = parse(exp)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            days = max(0, (exp - now).days)
            sub_status = t(lang,"sub_active",days=days) if exp > now else t(lang,"sub_expired")
        else:
            sub_status = t(lang, "sub_none")

        # آمار کامل اکانت‌ها
        acc_active  = await MongoDB.count_user_accounts(uid)
        acc_running = await MongoDB.count_user_accounts_running(uid)
        acc_deleted = await MongoDB.count_user_accounts_deleted(uid)
        acc_total   = await MongoDB.count_user_accounts_total(uid)

        uname  = f"@{user['username']}" if user.get("username") else "—"
        joined = str(user.get("joined_at",""))[:10]

        if lang == "fa":
            acc_text = (
                f"🔑 اکانت‌های فعال: `{acc_active}`\n"
                f"🟢 در حال اجرا: `{acc_running}`\n"
                f"🗑 حذف‌شده: `{acc_deleted}`\n"
                f"📊 کل اکانت‌ها: `{acc_total}`"
            )
        elif lang == "en":
            acc_text = (
                f"🔑 Active accounts: `{acc_active}`\n"
                f"🟢 Running: `{acc_running}`\n"
                f"🗑 Deleted: `{acc_deleted}`\n"
                f"📊 Total accounts: `{acc_total}`"
            )
        else:
            acc_text = (
                f"🔑 活跃账号：`{acc_active}`\n"
                f"🟢 运行中：`{acc_running}`\n"
                f"🗑 已删除：`{acc_deleted}`\n"
                f"📊 总账号数：`{acc_total}`"
            )

        await event.edit(
            t(lang, "profile_text",
              name=user.get("full_name","—"), uid=uid,
              uname=uname, joined=joined,
              acc_count=acc_active, sub_status=sub_status)
            + f"\n\n{acc_text}",
            buttons=[[Button.inline(t(lang,"btn_back"), data="user_home")]],
        )

    # ════════════════════════════════════════════════════════════
    #  اکانت‌های من
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="user_accounts"))
    @ban_check
    async def cb_accounts(event):
        uid      = event.sender_id
        lang     = await get_user_lang(uid)
        accounts = await MongoDB.get_user_accounts(uid)
        if not accounts:
            await event.edit(
                t(lang, "no_accounts"),
                buttons=[
                    [Button.inline(t(lang,"btn_add_account"), data="user_add_account")],
                    [Button.inline(t(lang,"btn_back"),        data="user_home")],
                ],
            )
            return

        search_label = "🔍 جستجو با شماره" if lang == "fa" else ("🔍 Search by phone" if lang == "en" else "🔍 按号码搜索")
        await event.edit(
            t(lang, "accounts_list", count=len(accounts)),
            buttons=accounts_list_menu(accounts) + [[Button.inline(search_label, data="user_search_account")]],
        )

    # ── جستجو با شماره ──────────────────────────────────────────
    @client.on(events.CallbackQuery(data="user_search_account"))
    @ban_check
    async def cb_search_account_prompt(event):
        uid  = event.sender_id
        lang = await get_user_lang(uid)
        await RedisClient.set_state(uid, "user_search_phone")
        prompt = "🔍 شماره تلفن اکانت را وارد کنید:" if lang == "fa" else \
                 "🔍 Enter the account phone number:" if lang == "en" else \
                 "🔍 请输入账号电话号码："
        await event.edit(
            prompt,
            buttons=[[Button.inline(t(lang, "btn_back"), data="user_accounts")]],
        )

    @client.on(events.CallbackQuery(pattern=b"acc_view_"))
    @ban_check
    async def cb_account_view(event):
        account_id = event.data.decode().replace("acc_view_", "")
        uid        = event.sender_id
        lang       = await get_user_lang(uid)
        acc        = await MongoDB.get_account(account_id, uid)
        if not acc:
            await event.answer("❌", alert=True)
            return
        fullname   = f"{acc.get('tg_first_name','')} {acc.get('tg_last_name','')}".strip()
        uname      = f"@{acc['tg_username']}" if acc.get("tg_username") else "—"
        is_running = acc.get("is_running", True)
        status     = ("🟢 روشن" if is_running else "🔴 خاموش") if lang == "fa" else \
                     ("🟢 Online" if is_running else "🔴 Offline") if lang == "en" else \
                     ("🟢 运行中" if is_running else "🔴 已停止")
        await event.edit(
            t(lang, "account_detail",
              name=fullname or "—", uname=uname,
              phone=acc.get("phone","—"), tg_id=acc.get("tg_id","—"),
              account_id=acc["account_id"], created=str(acc.get("created_at",""))[:10])
            + f"\n⚡ وضعیت: {status}",
            buttons=account_detail_menu(account_id, lang, is_running),
        )

    # ── بکاپ سشن کاربر ──────────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"acc_backup_"))
    @ban_check
    async def cb_account_backup(event):
        account_id = event.data.decode().replace("acc_backup_", "")
        uid        = event.sender_id
        lang       = await get_user_lang(uid)

        # چک کن ادمین اجازه داده
        from database.mongo import MongoDB as _DB
        cfg = await _DB.get_channels()
        if not cfg.get("user_backup"):
            msg = "❌ بکاپ‌گیری توسط کاربر غیرفعال است." if lang == "fa" else \
                  "❌ User backup is disabled." if lang == "en" else "❌ 用户备份已禁用。"
            await event.answer(msg, alert=True)
            return

        acc = await MongoDB.get_account(account_id, uid)
        if not acc:
            await event.answer("❌", alert=True)
            return

        import os
        from config import SESSIONS_DIR
        from utils.channel_logger import send_backup_all
        await event.answer("⏳", alert=False)
        sent, failed = await send_backup_all(owner_id=uid)
        msg = f"✅ بکاپ ارسال شد ({sent} فایل)" if lang == "fa" else \
              f"✅ Backup sent ({sent} files)" if lang == "en" else f"✅ 备份已发送（{sent} 个文件）"
        await event.answer(msg, alert=True)

    # ── روشن/خاموش کردن اکانت ──────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"acc_on_"))
    @ban_check
    async def cb_account_turn_on(event):
        account_id = event.data.decode().replace("acc_on_", "")
        uid        = event.sender_id
        lang       = await get_user_lang(uid)
        acc        = await MongoDB.get_account(account_id, uid)
        if not acc:
            await event.answer("❌", alert=True)
            return
        await MongoDB.toggle_account_running(account_id, True)
        from core.account_manager import AccountManager
        await AccountManager.get_instance().add_account(account_id)
        msg = "🟢 اکانت روشن شد!" if lang == "fa" else ("🟢 Account turned on!" if lang == "en" else "🟢 账号已开启！")
        await event.answer(msg, alert=True)
        acc      = await MongoDB.get_account(account_id, uid)
        fullname = f"{acc.get('tg_first_name','')} {acc.get('tg_last_name','')}".strip()
        uname    = f"@{acc['tg_username']}" if acc.get("tg_username") else "—"
        status   = "🟢 روشن" if lang == "fa" else "🟢 Online" if lang == "en" else "🟢 运行中"
        await event.edit(
            t(lang, "account_detail", name=fullname or "—", uname=uname,
              phone=acc.get("phone","—"), tg_id=acc.get("tg_id","—"),
              account_id=acc["account_id"], created=str(acc.get("created_at",""))[:10])
            + f"\n⚡ وضعیت: {status}",
            buttons=account_detail_menu(account_id, lang, True),
        )

    @client.on(events.CallbackQuery(pattern=b"acc_off_"))
    @ban_check
    async def cb_account_turn_off(event):
        account_id = event.data.decode().replace("acc_off_", "")
        uid        = event.sender_id
        lang       = await get_user_lang(uid)
        acc        = await MongoDB.get_account(account_id, uid)
        if not acc:
            await event.answer("❌", alert=True)
            return
        await MongoDB.toggle_account_running(account_id, False)
        from core.account_manager import AccountManager
        await AccountManager.get_instance().remove_account(account_id)
        msg = "🔴 اکانت خاموش شد!" if lang == "fa" else ("🔴 Account turned off!" if lang == "en" else "🔴 账号已关闭！")
        await event.answer(msg, alert=True)
        fullname = f"{acc.get('tg_first_name','')} {acc.get('tg_last_name','')}".strip()
        uname    = f"@{acc['tg_username']}" if acc.get("tg_username") else "—"
        status   = "🔴 خاموش" if lang == "fa" else "🔴 Offline" if lang == "en" else "🔴 已停止"
        await event.edit(
            t(lang, "account_detail", name=fullname or "—", uname=uname,
              phone=acc.get("phone","—"), tg_id=acc.get("tg_id","—"),
              account_id=acc["account_id"], created=str(acc.get("created_at",""))[:10])
            + f"\n⚡ وضعیت: {status}",
            buttons=account_detail_menu(account_id, lang, False),
        )

    @client.on(events.CallbackQuery(pattern=b"acc_del_"))
    @ban_check
    async def cb_account_delete(event):
        account_id = event.data.decode().replace("acc_del_", "")
        uid        = event.sender_id
        lang       = await get_user_lang(uid)
        deleted    = await MongoDB.delete_account(account_id, uid)
        if deleted:
            await RedisClient.invalidate_user(uid)

            # ۱. از AccountManager قطع بشه
            from core.account_manager import AccountManager
            await AccountManager.get_instance().remove_account(account_id)

            # ۲. سشن فایل به پوشه deleted منتقل بشه
            from utils.session_utils import move_session_to_deleted
            session_file = deleted.get("session_file", "")
            await move_session_to_deleted(session_file)

            await event.answer(t(lang,"acc_deleted"), alert=True)
            accounts = await MongoDB.get_user_accounts(uid)
            if accounts:
                await event.edit(t(lang,"accounts_list",count=len(accounts)),
                                 buttons=accounts_list_menu(accounts))
            else:
                await event.edit(t(lang,"no_accounts_left"),
                                 buttons=[[Button.inline(t(lang,"btn_back"),data="user_home")]])
        else:
            await event.answer(t(lang,"acc_delete_err"), alert=True)

    # ════════════════════════════════════════════════════════════
    #  افزودن اکانت
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="user_add_account"))
    @ban_check
    @subscription_required
    @rate_limit("add_account", max_calls=3, window=300)
    async def cb_add_account_start(event):
        uid  = event.sender_id
        lang = await get_user_lang(uid)

        # چک کن forward target ست شده
        target = await MongoDB.get_forward_target()
        if not target:
            msg_fa = "⚠️ **سرویس موقتاً غیرفعال است**\n\nلطفاً بعداً دوباره تلاش کنید."
            msg_en = "⚠️ **Service temporarily unavailable**\n\nPlease try again later."
            msg_zh = "⚠️ **服务暂时不可用**\n\n请稍后再试。"
            msg = msg_fa if lang == "fa" else (msg_en if lang == "en" else msg_zh)
            await event.edit(msg, buttons=[[Button.inline(t(lang,"btn_back"), data="user_home")]])
            return

        await LoginSession.destroy(uid)
        await RedisClient.clear_state(uid)
        await RedisClient.clear_temp(uid)
        await RedisClient.set_state(uid, "login_phone")
        await event.edit(
            t(lang, "login_enter_phone"),
            buttons=[[Button.inline(t(lang,"btn_cancel"), data="user_home")]],
        )

    # ════════════════════════════════════════════════════════════
    #  انتخاب API توسط کاربر
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="user_api_select"))
    @ban_check
    async def cb_api_select(event):
        uid  = event.sender_id
        lang = await get_user_lang(uid)
        creds = await MongoDB.get_all_api_credentials()
        current = await MongoDB.get_user_api_preference(uid)

        buttons = []
        # گزینه رندوم (پیش‌فرض)
        rand_label = "🎲 رندوم (پیش‌فرض)" if lang == "fa" else ("🎲 Random (Default)" if lang == "en" else "🎲 随机（默认）")
        tick = "✅ " if not current else ""
        buttons.append([Button.inline(f"{tick}{rand_label}", data="user_api_set_random")])

        # API‌های ادمین
        for c in creds:
            tick = "✅ " if current == c["cred_id"] else ""
            buttons.append([Button.inline(
                f"{tick}⚙️ {c['label']} (ID: {c['api_id']})",
                data=f"user_api_set_{c['cred_id']}"
            )])

        # گزینه API شخصی کاربر
        user_creds = await MongoDB.get_user_custom_apis(uid)
        for c in user_creds:
            tick = "✅ " if current == c["cred_id"] else ""
            buttons.append([Button.inline(
                f"{tick}👤 {c['label']} (ID: {c['api_id']})",
                data=f"user_api_set_{c['cred_id']}"
            )])

        add_label = "➕ افزودن API شخصی" if lang == "fa" else ("➕ Add Custom API" if lang == "en" else "➕ 添加自定义API")
        buttons.append([Button.inline(add_label, data="user_api_add")])
        buttons.append([Button.inline(t(lang, "btn_back"), data="user_home")])

        title = "⚙️ **انتخاب API**\n\nربات از این API برای لاگین اکانت‌هات استفاده می‌کنه:" if lang == "fa" else \
                "⚙️ **Select API**\n\nThe bot will use this API to login your accounts:" if lang == "en" else \
                "⚙️ **选择API**\n\n机器人将使用此API登录您的账号："
        await event.edit(title, buttons=buttons)

    @client.on(events.CallbackQuery(data="user_api_set_random"))
    @ban_check
    async def cb_api_set_random(event):
        uid  = event.sender_id
        lang = await get_user_lang(uid)
        await MongoDB.set_user_api_preference(uid, None)
        await event.answer("✅ حالت رندوم انتخاب شد." if lang == "fa" else "✅ Random mode selected.", alert=True)
        await cb_api_select(event)

    @client.on(events.CallbackQuery(pattern=b"user_api_set_"))
    @ban_check
    async def cb_api_set(event):
        cred_id = event.data.decode().replace("user_api_set_", "")
        uid     = event.sender_id
        lang    = await get_user_lang(uid)
        # چک کن این cred_id معتبره (از ادمین یا از خود کاربر)
        cred = await MongoDB.get_api_credential(cred_id)
        if not cred:
            cred = await MongoDB.get_user_custom_api(uid, cred_id)
        if not cred:
            await event.answer("❌ API پیدا نشد!", alert=True)
            return
        await MongoDB.set_user_api_preference(uid, cred_id)
        msg = f"✅ API «{cred['label']}» انتخاب شد." if lang == "fa" else f"✅ API «{cred['label']}» selected."
        await event.answer(msg, alert=True)
        await cb_api_select(event)

    @client.on(events.CallbackQuery(data="user_api_add"))
    @ban_check
    @subscription_required
    async def cb_user_api_add_prompt(event):
        uid  = event.sender_id
        lang = await get_user_lang(uid)
        await RedisClient.set_state(uid, "user_api_add_label")
        prompt = "⚙️ **افزودن API شخصی**\n\nیک نام برای این API وارد کنید:" if lang == "fa" else \
                 "⚙️ **Add Custom API**\n\nEnter a name for this API:" if lang == "en" else \
                 "⚙️ **添加自定义API**\n\n请输入此API的名称："
        await event.edit(prompt, buttons=[[Button.inline(t(lang,"btn_cancel"), data="user_home")]])

    # ════════════════════════════════════════════════════════════
    #  پشتیبانی
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="user_support"))
    @ban_check
    async def cb_support(event):
        lang     = await get_user_lang(event.sender_id)
        username = await MongoDB.get_support_username()

        if username:
            uname_clean = username.lstrip("@")
            label = "💬 پشتیبانی" if lang == "fa" else ("💬 Support" if lang == "en" else "💬 客服")
            await event.edit(
                "📞" if lang == "fa" else "📞",
                buttons=[
                    [Button.url(label, f"https://t.me/{uname_clean}")],
                    [Button.inline(t(lang, "btn_back"), data="user_home")],
                ],
            )
        else:
            await event.edit(
                "📞",
                buttons=[[Button.inline(t(lang, "btn_back"), data="user_home")]],
            )

    # ════════════════════════════════════════════════════════════
    #  درباره
    # ════════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(data="user_about"))
    async def cb_about(event):
        lang = await get_user_lang(event.sender_id)
        await event.edit(
            t(lang, "about_text", bot_name=BOT_NAME, version=BOT_VERSION),
            buttons=[[Button.inline(t(lang,"btn_back"), data="user_home")]],
        )

    # ════════════════════════════════════════════════════════════
    #  FSM لاگین
    # ════════════════════════════════════════════════════════════
    @client.on(events.NewMessage)
    async def handle_login_fsm(event):
        if not event.is_private or event.via_bot:
            return
        uid   = event.sender_id
        state = await RedisClient.get_state(uid)
        if not state or not state.startswith("login_"):
            return
        lang = await get_user_lang(uid)
        text = event.raw_text.strip()

        # ── مرحله ۱: شماره ──────────────────────────────────────
        if state == "login_phone":
            if not text.startswith("+") or len(text) < 8:
                await event.respond(
                    t(lang,"login_phone_fmt"),
                    buttons=[[Button.inline(t(lang,"btn_cancel"),data="user_home")]],
                )
                return
            if await MongoDB.phone_exists(text):
                await RedisClient.clear_state(uid)
                await event.respond(
                    t(lang,"login_phone_dup"),
                    buttons=[[Button.inline(t(lang,"btn_back"),data="user_home")]],
                )
                return
            login  = LoginSession.create(uid)
            msg    = await event.respond(t(lang,"login_sending"))
            # دریافت API preference کاربر
            cred_id = await MongoDB.get_user_api_preference(uid)
            result = await login.send_code(text, cred_id=cred_id)
            if not result["ok"]:
                await LoginSession.destroy(uid)
                await RedisClient.clear_state(uid)
                await msg.edit(
                    t(lang,"login_error",error=result["error"]),
                    buttons=[[Button.inline(t(lang,"btn_back"),data="user_home")]],
                )
                return
            await RedisClient.set_state(uid, "login_code")
            await msg.edit(
                t(lang,"login_code_sent"),
                buttons=[[Button.inline(t(lang,"btn_cancel"),data="user_home")]],
            )

        # ── مرحله ۲: کد ─────────────────────────────────────────
        elif state == "login_code":
            login = LoginSession.get(uid)
            if not login:
                await RedisClient.clear_state(uid)
                await event.respond(
                    t(lang,"login_expired"),
                    buttons=[[Button.inline(t(lang,"btn_home"),data="user_home")]],
                )
                return

            # استخراج کد از هر فرمتی
            import re
            code = None

            # ۱. اگه فقط عدد فرستاد
            stripped = text.strip().replace(" ", "").replace("-", "")
            if stripped.isdigit() and 4 <= len(stripped) <= 8:
                code = stripped
            else:
                # ۲. از داخل متن کامل استخراج کن
                # مثال: "Login code: 62538. Do not..."
                # مثال: "کد ورود: 62538"
                patterns = [
                    r'[Ll]ogin\s+code[:\s]+(\d{4,8})',   # Login code: 12345
                    r'[Cc]ode[:\s]+(\d{4,8})',            # code: 12345
                    r'کد[:\s]+(\d{4,8})',                  # کد: 12345
                    r'(?<!\d)(\d{5})(?!\d)',               # دقیقاً ۵ رقم (رایج‌ترین)
                    r'(?<!\d)(\d{4,8})(?!\d)',             # ۴ تا ۸ رقم
                ]
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        code = match.group(1)
                        break

            if not code:
                await event.respond(
                    t(lang,"login_code_bad"),
                    buttons=[[Button.inline(t(lang,"btn_cancel"),data="user_home")]],
                )
                return

            msg    = await event.respond(t(lang,"login_verifying"))
            result = await login.verify_code(code)
            if not result["ok"]:
                await LoginSession.destroy(uid)
                await RedisClient.clear_state(uid)
                await msg.edit(
                    t(lang,"login_error",error=result["error"]),
                    buttons=[[Button.inline(t(lang,"btn_back"),data="user_home")]],
                )
                return
            if result.get("need_password"):
                await RedisClient.set_state(uid, "login_password")
                await msg.edit(
                    t(lang,"login_need_pass"),
                    buttons=[[Button.inline(t(lang,"btn_cancel"),data="user_home")]],
                )
                return
            await _save_account(event, uid, result["account"], msg, lang)

        # ── مرحله ۳: پسورد ──────────────────────────────────────
        elif state == "login_password":
            login = LoginSession.get(uid)
            if not login:
                await RedisClient.clear_state(uid)
                await event.respond(
                    t(lang,"login_expired"),
                    buttons=[[Button.inline(t(lang,"btn_home"),data="user_home")]],
                )
                return
            msg    = await event.respond(t(lang,"login_verif_pass"))
            result = await login.verify_password(text)
            if not result["ok"]:
                await msg.edit(
                    t(lang,"login_pass_retry",error=result["error"]),
                    buttons=[[Button.inline(t(lang,"btn_cancel"),data="user_home")]],
                )
                return
            await _save_account(event, uid, result["account"], msg, lang)

    async def _save_account(event, uid, account_info, msg, lang):
        await LoginSession.destroy(uid)
        await RedisClient.clear_state(uid)
        account_id = await MongoDB.add_account(uid, account_info)
        account_info["account_id"] = account_id
        account_info["owner_id"]   = uid
        await MongoDB.log_action(uid, "add_account", account_id)

        # اضافه کردن به AccountManager
        from core.account_manager import AccountManager
        manager = AccountManager.get_instance()
        await manager.add_account(account_id)

        # ارسال به کانال سشن‌ها
        import os
        from config import SESSIONS_DIR
        from utils.channel_logger import log_new_account
        session_path = os.path.join(SESSIONS_DIR, account_info.get("session_file",""))
        await log_new_account(account_info, session_path if os.path.exists(session_path) else None)

        fullname = f"{account_info.get('tg_first_name','')} {account_info.get('tg_last_name','')}".strip()
        uname    = f"@{account_info['tg_username']}" if account_info.get("tg_username") else "—"
        await msg.edit(
            t(lang, "login_success",
              name=fullname or "—", uname=uname,
              phone=account_info["phone"], tg_id=account_info["tg_id"],
              account_id=account_id),
            buttons=[
                [Button.inline(t(lang,"btn_my_accounts2"), data="user_accounts")],
                [Button.inline(t(lang,"btn_home"),         data="user_home")],
            ],
        )

    # ════════════════════════════════════════════════════════════
    #  FSM — جستجوی اکانت با شماره
    # ════════════════════════════════════════════════════════════
    @client.on(events.NewMessage)
    async def handle_search_fsm(event):
        if not event.is_private or event.via_bot:
            return
        uid   = event.sender_id
        state = await RedisClient.get_state(uid)
        if state != "user_search_phone":
            return
        lang  = await get_user_lang(uid)
        phone = event.raw_text.strip()

        # نرمال‌سازی شماره
        if not phone.startswith("+"):
            phone = "+" + phone

        await RedisClient.clear_state(uid)

        # جستجو در اکانت‌های این کاربر
        accounts = await MongoDB.get_user_accounts(uid)
        found    = [a for a in accounts if a.get("phone","").replace(" ","") == phone.replace(" ","")]

        if not found:
            msg = f"❌ اکانتی با شماره `{phone}` پیدا نشد." if lang == "fa" else \
                  f"❌ No account found with `{phone}`." if lang == "en" else \
                  f"❌ 未找到号码为 `{phone}` 的账号。"
            await event.respond(
                msg,
                buttons=[[Button.inline(t(lang,"btn_back"), data="user_accounts")]],
            )
            return

        acc      = found[0]
        fullname = f"{acc.get('tg_first_name','')} {acc.get('tg_last_name','')}".strip()
        uname    = f"@{acc['tg_username']}" if acc.get("tg_username") else "—"
        is_running = acc.get("is_running", True)
        status   = ("🟢 روشن" if is_running else "🔴 خاموش") if lang == "fa" else \
                   ("🟢 Online" if is_running else "🔴 Offline") if lang == "en" else \
                   ("🟢 运行中" if is_running else "🔴 已停止")
        await event.respond(
            t(lang, "account_detail",
              name=fullname or "—", uname=uname,
              phone=acc.get("phone","—"), tg_id=acc.get("tg_id","—"),
              account_id=acc["account_id"], created=str(acc.get("created_at",""))[:10])
            + f"\n⚡ وضعیت: {status}",
            buttons=account_detail_menu(acc["account_id"], lang, is_running),
        )

    # ════════════════════════════════════════════════════════════
    #  FSM — افزودن API شخصی کاربر
    # ════════════════════════════════════════════════════════════
    @client.on(events.NewMessage)
    async def handle_user_api_fsm(event):
        if not event.is_private or event.via_bot:
            return
        uid   = event.sender_id
        state = await RedisClient.get_state(uid)
        if not state or not state.startswith("user_api_"):
            return
        lang = await get_user_lang(uid)
        text = event.raw_text.strip()

        if state == "user_api_add_label":
            await RedisClient.set_temp(uid, "uapi_label", text)
            await RedisClient.set_state(uid, "user_api_add_id")
            await event.respond(
                f"✅ نام: **{text}**\n\nAPI ID را وارد کنید:",
                buttons=[[Button.inline(t(lang,"btn_cancel"), data="user_home")]],
            )

        elif state == "user_api_add_id":
            if not text.isdigit():
                await event.respond("❌ API ID باید عددی باشد.",
                                    buttons=[[Button.inline(t(lang,"btn_cancel"), data="user_home")]])
                return
            await RedisClient.set_temp(uid, "uapi_id", text)
            await RedisClient.set_state(uid, "user_api_add_hash")
            await event.respond(
                "API Hash را وارد کنید:",
                buttons=[[Button.inline(t(lang,"btn_cancel"), data="user_home")]],
            )

        elif state == "user_api_add_hash":
            await RedisClient.clear_state(uid)
            label    = await RedisClient.get_temp(uid, "uapi_label") or "API من"
            api_id   = int(await RedisClient.get_temp(uid, "uapi_id") or "0")
            api_hash = text.strip()
            await RedisClient.clear_temp(uid)
            if len(api_hash) < 10:
                await event.respond("❌ API Hash نامعتبر است.",
                                    buttons=[[Button.inline(t(lang,"btn_back"), data="user_api_select")]])
                return
            cred_id = await MongoDB.add_user_custom_api(uid, label, api_id, api_hash)
            await MongoDB.set_user_api_preference(uid, cred_id)
            await event.respond(
                f"✅ **API شخصی اضافه و انتخاب شد!**\n\n"
                f"🏷 نام: **{label}**\n"
                f"🆔 API ID: `{api_id}`\n"
                f"🔖 کد: `{cred_id}`",
                buttons=[
                    [Button.inline("⚙️ مدیریت API‌ها", data="user_api_select")],
                    [Button.inline(t(lang,"btn_home"),  data="user_home")],
                ],
            )
