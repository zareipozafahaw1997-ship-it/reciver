"""中文"""

STRINGS = {
    # ── 通用 ────────────────────────────────────────────────────
    "btn_back":          "🔙 返回",
    "btn_cancel":        "❌ 取消",
    "btn_home":          "🏠 主菜单",
    "err_id_numeric":    "❌ ID必须是数字。",
    "err_not_found":     "❌ 未找到该ID的用户。",

    # ── 语言选择 ────────────────────────────────────────────────
    "choose_lang":       "🌐 زبان مورد نظر خود را انتخاب کنید:\nPlease choose your language:\n请选择您的语言:",
    "lang_set":          "✅ 已选择中文！",

    # ── 开始 ────────────────────────────────────────────────────
    "welcome":           "👋 你好 **{name}**！\n\n欢迎使用 {bot_name} 🎉\n请从下方菜单选择：",

    # ── 主菜单 ──────────────────────────────────────────────────
    "main_menu_text":    "🏠 **主菜单**\n\n你好 {name}，我能为你做什么？",
    "btn_add_account":   "➕ 添加账号",
    "btn_my_profile":    "👤 我的资料",
    "btn_my_accounts":   "📂 我的账号",
    "btn_support":       "📞 客服支持",
    "btn_about":         "ℹ️ 关于",
    "btn_language":      "🌐 切换语言",
    "btn_api_select":    "⚙️ 选择API",

    # ── 个人资料 ────────────────────────────────────────────────
    "profile_text":      "👤 **我的资料**\n\n📛 姓名：**{name}**\n🆔 ID：`{uid}`\n📌 用户名：{uname}\n📅 注册时间：`{joined}`\n🔑 账号数量：`{acc_count}`\n💎 订阅状态：{sub_status}",
    "sub_active":        "✅ 有效（剩余 {days} 天）",
    "sub_expired":       "⏰ 已过期",
    "sub_none":          "❌ 无",

    # ── 账号 ────────────────────────────────────────────────────
    "no_accounts":       "📂 **我的账号**\n\n您还没有添加任何账号！\n点击 **添加账号** 开始 👇",
    "accounts_list":     "📂 **我的账号** （{count} 个账号）\n\n选择一个查看详情：",
    "account_detail":    "🔑 **账号详情**\n\n👤 姓名：**{name}**\n📌 用户名：{uname}\n📱 电话：`{phone}`\n🆔 Telegram ID：`{tg_id}`\n🔖 账号代码：`{account_id}`\n📅 添加时间：`{created}`",
    "btn_delete_acc":    "🗑 删除账号",
    "btn_back_accounts": "🔙 返回账号列表",
    "acc_deleted":       "✅ 账号已删除。",
    "acc_delete_err":    "❌ 删除账号时出错！",
    "no_accounts_left":  "📂 **我的账号**\n\n没有剩余账号！",

    # ── 登录 ────────────────────────────────────────────────────
    "login_enter_phone": "➕ **添加 Telegram 账号**\n\n📱 请以国际格式输入电话号码：\n\n示例：`+989123456789`",
    "login_phone_fmt":   "❌ 电话格式无效。\n示例：`+989123456789`",
    "login_phone_dup":   "⛔ **该号码已注册！**\n\n无法重复添加。",
    "login_sending":     "⏳ 正在发送验证码...",
    "login_code_sent":   "✅ **验证码已发送！**\n\n📩 请输入 Telegram 发送的验证码：\n_（可以直接粘贴完整的 Telegram 消息，我会自动提取验证码）_",
    "login_code_bad":    "❌ 消息中未找到验证码，请直接发送验证码数字：",
    "login_verifying":   "⏳ 正在验证...",
    "login_need_pass":   "🔐 **两步验证**\n\n该账号设有密码。\n请输入您的 Telegram 密码：",
    "login_verif_pass":  "⏳ 正在验证密码...",
    "login_pass_retry":  "❌ **{error}**\n\n请重新输入密码：",
    "login_error":       "❌ **错误**\n\n{error}",
    "login_expired":     "⚠️ 登录会话已过期，请从菜单重新开始。",
    "login_success":     "🎉 **账号添加成功！**\n\n👤 姓名：**{name}**\n📌 用户名：{uname}\n📱 电话：`{phone}`\n🆔 ID：`{tg_id}`\n🔖 代码：`{account_id}`\n\n✅ 会话已保存。",
    "btn_my_accounts2":  "📂 我的账号",

    # ── 订阅 ────────────────────────────────────────────────────
    "sub_required":      "🔒 **此功能需要订阅！**\n\n请购买订阅以使用机器人。\n联系客服购买 👇",
    "sub_expired_msg":   "⏰ **您的订阅已过期！**\n\n请联系客服续订 👇",

    # ── 客服 ────────────────────────────────────────────────────
    "support_text":      "📞 **客服支持**\n\n联系我们：\n📧 邮箱：support@example.com\n💬 Telegram：@support",

    # ── 关于 ────────────────────────────────────────────────────
    "about_text":        "ℹ️ **关于**\n\n本机器人旨在保护您的 Telegram 账号安全。\n添加账号后，每当有人尝试登录您的账号并发送验证码时，机器人会自动接收并使其失效，防止他人登录您的账号。",

    # ── 封禁 ────────────────────────────────────────────────────
    "banned_msg":        "🚫 您已被封禁。",
    "rate_limit_msg":    "⏳ 操作太频繁！请等待 {window} 秒。",
}
