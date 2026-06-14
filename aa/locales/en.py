"""English"""

STRINGS = {
    # ── General ────────────────────────────────────────────────
    "btn_back":          "🔙 Back",
    "btn_cancel":        "❌ Cancel",
    "btn_home":          "🏠 Main Menu",
    "err_id_numeric":    "❌ ID must be a number.",
    "err_not_found":     "❌ No user found with this ID.",

    # ── Language selection ──────────────────────────────────────
    "choose_lang":       "🌐 زبان مورد نظر خود را انتخاب کنید:\nPlease choose your language:\n请选择您的语言:",
    "lang_set":          "✅ English language selected!",

    # ── Start ───────────────────────────────────────────────────
    "welcome":           "👋 Hello **{name}**!\n\nWelcome to {bot_name} 🎉\nChoose from the menu below:",

    # ── Main menu ───────────────────────────────────────────────
    "main_menu_text":    "🏠 **Main Menu**\n\nHello {name}, what can I do for you?",
    "btn_add_account":   "➕ Add Account",
    "btn_my_profile":    "👤 My Profile",
    "btn_my_accounts":   "📂 My Accounts",
    "btn_support":       "📞 Support",
    "btn_about":         "ℹ️ About",
    "btn_language":      "🌐 Change Language",
    "btn_api_select":    "⚙️ Select API",

    # ── Profile ─────────────────────────────────────────────────
    "profile_text":      "👤 **My Profile**\n\n📛 Name: **{name}**\n🆔 ID: `{uid}`\n📌 Username: {uname}\n📅 Joined: `{joined}`\n🔑 Accounts: `{acc_count}`\n💎 Subscription: {sub_status}",
    "sub_active":        "✅ Active ({days} days left)",
    "sub_expired":       "⏰ Expired",
    "sub_none":          "❌ None",

    # ── Accounts ────────────────────────────────────────────────
    "no_accounts":       "📂 **My Accounts**\n\nYou haven't added any accounts yet!\nPress **Add Account** to get started 👇",
    "accounts_list":     "📂 **My Accounts** ({count} accounts)\n\nSelect one to view details:",
    "account_detail":    "🔑 **Account Details**\n\n👤 Name: **{name}**\n📌 Username: {uname}\n📱 Phone: `{phone}`\n🆔 Telegram ID: `{tg_id}`\n🔖 Account Code: `{account_id}`\n📅 Added: `{created}`",
    "btn_delete_acc":    "🗑 Delete Account",
    "btn_back_accounts": "🔙 Back to Accounts",
    "acc_deleted":       "✅ Account deleted.",
    "acc_delete_err":    "❌ Error deleting account!",
    "no_accounts_left":  "📂 **My Accounts**\n\nNo accounts remaining!",

    # ── Login ───────────────────────────────────────────────────
    "login_enter_phone": "➕ **Add Telegram Account**\n\n📱 Enter phone number in international format:\n\nExample: `+989123456789`",
    "login_phone_fmt":   "❌ Invalid phone format.\nExample: `+989123456789`",
    "login_phone_dup":   "⛔ **This number is already registered!**\n\nCannot add it again.",
    "login_sending":     "⏳ Sending verification code...",
    "login_code_sent":   "✅ **Code sent!**\n\n📩 Enter the code Telegram sent you:\n_(You can also paste the full Telegram message, I'll extract the code)_",
    "login_code_bad":    "❌ No code found in your message. Please send the code number:",
    "login_verifying":   "⏳ Verifying code...",
    "login_need_pass":   "🔐 **Two-Factor Authentication**\n\nThis account has a password.\nEnter your Telegram password:",
    "login_verif_pass":  "⏳ Verifying password...",
    "login_pass_retry":  "❌ **{error}**\n\nPlease enter your password again:",
    "login_error":       "❌ **Error**\n\n{error}",
    "login_expired":     "⚠️ Login session expired. Please start again from the menu.",
    "login_success":     "🎉 **Account added successfully!**\n\n👤 Name: **{name}**\n📌 Username: {uname}\n📱 Phone: `{phone}`\n🆔 ID: `{tg_id}`\n🔖 Code: `{account_id}`\n\n✅ Session saved.",
    "btn_my_accounts2":  "📂 My Accounts",

    # ── Subscription ────────────────────────────────────────────
    "sub_required":      "🔒 **This feature requires a subscription!**\n\nPlease purchase a subscription to use the bot.\nContact support to buy 👇",
    "sub_expired_msg":   "⏰ **Your subscription has expired!**\n\nContact support to renew 👇",

    # ── Support ─────────────────────────────────────────────────
    "support_text":      "📞 **Support**\n\nContact us:\n📧 Email: support@example.com\n💬 Telegram: @support",

    # ── About ───────────────────────────────────────────────────
    "about_text":        "ℹ️ **About**\n\nThis bot is designed to protect your Telegram accounts.\nBy adding your account, whenever a login code is sent to it, the bot receives and expires it so no one can log into your account.",

    # ── Ban ─────────────────────────────────────────────────────
    "banned_msg":        "🚫 You have been banned from this bot.",
    "rate_limit_msg":    "⏳ Too fast! Please wait {window} seconds.",
}
