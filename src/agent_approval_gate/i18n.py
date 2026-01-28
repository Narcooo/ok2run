"""国际化支持 - 中英文自动切换"""

TEXTS = {
    "zh": {
        "click_button": "点击下方按钮进行操作",
        "click_to_select": "点击下方按钮选择",
        "approve": "批准",
        "deny": "拒绝",
        "approve_with_note": "批准+备注",
        "always_allow": "永久允许",
        "custom_reply": "自定义回复",
        "approved": "已批准",
        "denied": "已拒绝",
        "selected": "已选择",
        "action": "操作",
        "no_permission": "无权限操作",
        "invalid_action": "无效的操作",
        "failed": "处理失败",
        "enter_note": "请输入备注内容",
        "enter_custom": "请输入自定义回复",
        "reply_received": "已收到回复",
        "content": "内容",
        "reply_below": "请回复下方消息输入备注",
    },
    "en": {
        "click_button": "Click button below to proceed",
        "click_to_select": "Click button below to select",
        "approve": "Approve",
        "deny": "Deny",
        "approve_with_note": "Approve+Note",
        "always_allow": "Always Allow",
        "custom_reply": "Custom Reply",
        "approved": "Approved",
        "denied": "Denied",
        "selected": "Selected",
        "action": "Action",
        "no_permission": "No permission",
        "invalid_action": "Invalid action",
        "failed": "Failed",
        "enter_note": "Please enter your note",
        "enter_custom": "Please enter custom reply",
        "reply_received": "Reply received",
        "content": "Content",
        "reply_below": "Please reply to enter note",
    }
}


def get_lang(language_code: str | None) -> str:
    """根据 Telegram language_code 返回语言代码"""
    if language_code and language_code.startswith("zh"):
        return "zh"
    return "en"


def t(key: str, language_code: str | None = None) -> str:
    """获取翻译文本"""
    lang = get_lang(language_code)
    return TEXTS.get(lang, TEXTS["en"]).get(key, key)
