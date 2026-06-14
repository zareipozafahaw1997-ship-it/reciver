"""
keyboards/admin_kb.py
کیبوردهای شیشه‌ای (Inline) پنل ادمین
"""

from telethon import Button


def admin_main_menu() -> list:
    return [
        # ── مدیریت کاربران و اکانت‌ها ──────────────────────────
        [
            Button.inline("👥 کاربران",            data="adm_users"),
            Button.inline("🔑 اکانت‌ها",            data="adm_accounts"),
        ],
        # ── ارتباط با کاربران ───────────────────────────────────
        [
            Button.inline("📢 پیام همگانی",         data="adm_broadcast"),
            Button.inline("✉️ پیام به کاربر",        data="adm_msg_user"),
        ],
        # ── مالی ────────────────────────────────────────────────
        [
            Button.inline("💎 اشتراک‌ها",            data="adm_subs"),
            Button.inline("📊 آمار کامل",            data="adm_stats"),
        ],
        # ── تنظیمات فنی ─────────────────────────────────────────
        [
            Button.inline("🌐 پروکسی",              data="adm_proxy"),
            Button.inline("⚙️ API Credentials",     data="adm_apis"),
        ],
        # ── تنظیمات ربات ────────────────────────────────────────
        [
            Button.inline("📡 تنظیمات کانال‌ها",    data="adm_channels"),
            Button.inline("📲 دریافت کد سشن",       data="adm_get_code"),
        ],
        [
            Button.inline("📨 فوروارد کد",          data="adm_forward"),
            Button.inline("💾 بکاپ سشن‌ها",         data="adm_backup_all"),
        ],
        [
            Button.inline("📋 لاگ‌ها",               data="adm_logs"),
            Button.inline("⚡ وضعیت ربات",            data="adm_bot_status"),
        ],
    ]


def admin_apis_menu() -> list:
    return [
        [Button.inline("📋 لیست API‌ها",          data="adm_api_list")],
        [Button.inline("➕ افزودن API جدید",       data="adm_api_add")],
        [Button.inline("🔙 بازگشت",               data="adm_home")],
    ]


def admin_proxy_menu(enabled: bool, has_key: bool) -> list:
    status = "✅ فعال" if enabled else "❌ غیرفعال"
    toggle_label = "🔴 غیرفعال کردن" if enabled else "🟢 فعال کردن"
    buttons = [
        [Button.inline(f"وضعیت: {status}",        data="adm_proxy_status")],
        [Button.inline(toggle_label,               data="adm_proxy_toggle")],
        [Button.inline("🔑 تنظیم API Key",         data="adm_proxy_setkey")],
    ]
    if has_key:
        buttons.append([Button.inline("🧪 تست پروکسی", data="adm_proxy_test")])
    buttons.append([Button.inline("🔙 بازگشت", data="adm_home")])
    return buttons


def admin_users_menu() -> list:
    return [
        [
            Button.inline("📋 لیست کاربران",      data="adm_list_users"),
            Button.inline("🔍 جستجوی کاربر",      data="adm_search_user"),
        ],
        [
            Button.inline("🚫 مسدود کردن",        data="adm_ban_user"),
            Button.inline("✅ رفع مسدودیت",        data="adm_unban_user"),
        ],
        [
            Button.inline("👑 افزودن ادمین",       data="adm_add_admin"),
            Button.inline("❌ حذف ادمین",          data="adm_remove_admin"),
        ],
        [
            Button.inline("🛒 افزودن فروشنده",     data="adm_add_seller"),
            Button.inline("🗑 حذف فروشنده",        data="adm_remove_seller"),
        ],
        [
            Button.inline("🔙 بازگشت",            data="adm_home"),
        ],
    ]


def admin_accounts_menu() -> list:
    return [
        [
            Button.inline("📋 همه اکانت‌ها",       data="adm_all_accounts"),
            Button.inline("📊 آمار اکانت‌ها",       data="adm_accounts_stats"),
        ],
        [
            Button.inline("🟢 وضعیت آنلاین",        data="adm_accounts_online"),
            Button.inline("🔍 جستجوی اکانت",        data="adm_search_account"),
        ],
        [
            Button.inline("🔙 بازگشت",            data="adm_home"),
        ],
    ]


def admin_stats_menu() -> list:
    return [
        [
            Button.inline("👥 آمار کاربران",       data="adm_stats_users"),
            Button.inline("🔑 آمار اکانت‌ها",       data="adm_stats_accounts"),
        ],
        [
            Button.inline("🟢 کاربران آنلاین",     data="adm_online"),
            Button.inline("🚫 کاربران بن‌شده",      data="adm_banned_list"),
        ],
        [
            Button.inline("🔙 بازگشت",            data="adm_home"),
        ],
    ]


def user_action_menu(target_id: int) -> list:
    return [
        [
            Button.inline("✉️ ارسال پیام",         data=f"adm_send_{target_id}"),
            Button.inline("🚫 مسدود کردن",         data=f"adm_doban_{target_id}"),
        ],
        [
            Button.inline("✅ رفع مسدودیت",         data=f"adm_dounban_{target_id}"),
            Button.inline("👑 ادمین کردن",          data=f"adm_doadmin_{target_id}"),
        ],
        [
            Button.inline("💎 اشتراک ۳۰ روزه",     data=f"adm_sub30_{target_id}"),
            Button.inline("💎 اشتراک ۹۰ روزه",     data=f"adm_sub90_{target_id}"),
        ],
        [
            Button.inline("❌ لغو اشتراک",          data=f"adm_subrv_{target_id}"),
        ],
        [
            Button.inline("🔙 بازگشت",             data="adm_list_users"),
        ],
    ]


def admin_subs_menu() -> list:
    return [
        [
            Button.inline("📋 لیست مشترکین",       data="adm_list_subs"),
            Button.inline("📊 آمار اشتراک‌ها",      data="adm_stats_subs"),
        ],
        [
            Button.inline("➕ اشتراک دستی",         data="adm_manual_sub"),
        ],
        [
            Button.inline("🔙 بازگشت",             data="adm_home"),
        ],
    ]


def back_to_admin(cb: str = "adm_home") -> list:
    return [[Button.inline("🔙 بازگشت", data=cb)]]


def seller_main_menu() -> list:
    return [
        [
            Button.inline("💎 فروش اشتراک",       data="sel_sub"),
            Button.inline("👥 مدیریت کاربران",    data="sel_users"),
        ],
        [
            Button.inline("✉️ پیام به کاربر",      data="adm_msg_user"),
        ],
    ]


def seller_users_menu() -> list:
    return [
        [
            Button.inline("🔍 جستجوی کاربر",      data="adm_search_user"),
        ],
        [
            Button.inline("🚫 مسدود کردن",        data="adm_ban_user"),
            Button.inline("✅ رفع مسدودیت",        data="adm_unban_user"),
        ],
        [
            Button.inline("🔙 بازگشت",            data="sel_home"),
        ],
    ]


def seller_sub_menu() -> list:
    return [
        [
            Button.inline("➕ اشتراک دستی",        data="adm_manual_sub"),
        ],
        [
            Button.inline("📋 لیست مشترکین",       data="adm_list_subs"),
            Button.inline("📊 آمار اشتراک‌ها",      data="adm_stats_subs"),
        ],
        [
            Button.inline("🔙 بازگشت",            data="sel_home"),
        ],
    ]


def admin_channels_menu(cfg: dict) -> list:
    def ch(key): return "✅ ست شده" if cfg.get(key) else "❌ ست نشده"
    ub  = "✅ فعال" if cfg.get("user_backup")  else "❌ غیرفعال"
    ab  = "✅ فعال" if cfg.get("auto_backup")  else "❌ غیرفعال"
    fj  = "✅ فعال" if cfg.get("fj_enabled")   else "❌ غیرفعال"
    return [
        [Button.inline(f"📸 کانال سشن‌ها: {ch('sessions_channel')}",  data="adm_ch_sessions")],
        [Button.inline(f"🚨 کانال ارورها: {ch('errors_channel')}",    data="adm_ch_errors")],
        [Button.inline(f"💰 کانال فروش: {ch('sales_channel')}",       data="adm_ch_sales")],
        [Button.inline(f"💾 کانال بکاپ: {ch('backup_channel')}",      data="adm_ch_backup")],
        [Button.inline(f"👤 بکاپ کاربر: {ub}",                        data="adm_ch_user_backup"),
         Button.inline(f"⏰ بکاپ خودکار: {ab}",                       data="adm_ch_auto_backup")],
        [Button.inline(f"📢 جوین اجباری: {fj}",                       data="adm_fj_toggle"),
         Button.inline("📢 کانال جوین",                                data="adm_fj_set")],
        [Button.inline("📞 پشتیبانی",                                  data="adm_set_support")],
        [Button.inline("🤖 اسم ربات",                                  data="adm_set_botname")],
        [Button.inline("🔙 بازگشت",                                    data="adm_home")],
    ]
