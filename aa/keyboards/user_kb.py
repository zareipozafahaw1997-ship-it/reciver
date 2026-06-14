"""
keyboards/user_kb.py
کیبوردهای شیشه‌ای (Inline) کاربر عادی
"""

from telethon import Button


def accounts_list_menu(accounts: list[dict]) -> list:
    buttons = []
    for acc in accounts:
        fullname = f"{acc.get('tg_first_name','')} {acc.get('tg_last_name','')}".strip()
        label = f"🔑 {fullname or acc.get('phone','—')} — {acc['account_id']}"
        buttons.append([Button.inline(label, data=f"acc_view_{acc['account_id']}")])
    buttons.append([Button.inline("🔙 بازگشت", data="user_home")])
    return buttons


def account_detail_menu(account_id: str, lang: str = "fa", is_running: bool = True) -> list:
    from locales import t
    toggle_label = ("🔴 خاموش کردن" if is_running else "🟢 روشن کردن") if lang == "fa" else \
                   ("🔴 Turn Off"    if is_running else "🟢 Turn On")    if lang == "en" else \
                   ("🔴 关闭"         if is_running else "🟢 开启")
    toggle_data  = f"acc_off_{account_id}" if is_running else f"acc_on_{account_id}"
    backup_label = "💾 بکاپ سشن" if lang == "fa" else ("💾 Backup Session" if lang == "en" else "💾 备份会话")
    return [
        [Button.inline(toggle_label,                    data=toggle_data)],
        [Button.inline(backup_label,                    data=f"acc_backup_{account_id}")],
        [Button.inline(t(lang,"btn_delete_acc"),        data=f"acc_del_{account_id}")],
        [Button.inline(t(lang,"btn_back_accounts"),     data="user_accounts")],
    ]


def back_btn(cb: str = "user_home") -> list:
    return [[Button.inline("🔙 بازگشت", data=cb)]]
