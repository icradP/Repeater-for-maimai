import base64
import os
import re
from typing import Any, List, Set, Tuple, Type

from src.chat.utils.utils import is_bot_self
from src.plugin_system import ActionActivationType, BaseAction, BasePlugin, ComponentInfo, ConfigField, register_plugin
from src.plugin_system.apis import message_api


class RepeaterAction(BaseAction):
    action_name = "repeater_action"
    action_description = "在群聊中满足复读条件时，复读上一个人的发言（文本或图片）"
    activation_type = ActionActivationType.ALWAYS
    associated_types = ["text", "image"]
    action_parameters = {}
    action_require = [
        "当最近连续消息是同一内容（文本或图片）时使用",
        "当同一内容的发送者中不同用户数达到两人及以上时使用",
        "统计时不包含机器人自己",
        "发送内容为上一个人的原始发言（文本或图片）",
    ]
    parallel_action = False

    _PICID_RE = re.compile(r"^\[picid:([^\]]+)\]$")

    async def execute(self) -> Tuple[bool, str]:
        if not self.get_config("repeater.enabled", True):
            return False, "复读器已禁用"

        recent_limit = int(self.get_config("repeater.recent_limit", 20))
        min_distinct_users = int(self.get_config("repeater.min_distinct_users", 2))
        recent_messages = message_api.get_recent_messages(
            chat_id=self.chat_id,
            hours=1.0,
            limit=recent_limit,
            limit_mode="latest",
            filter_mai=False,
        )
        if not recent_messages:
            return False, "无可用消息"

        recent_non_bot_texts: List[Tuple[str, str]] = []
        for msg in reversed(recent_messages):
            text = (msg.processed_plain_text or "").strip()
            if not text:
                continue
            platform = msg.user_info.platform
            user_id = str(msg.user_info.user_id)
            if is_bot_self(platform, user_id):
                continue
            recent_non_bot_texts.append((text, user_id))

        if not recent_non_bot_texts:
            return False, "无可复读内容"

        target_text = recent_non_bot_texts[0][0]
        distinct_users: Set[str] = set()
        for text, user_id in recent_non_bot_texts:
            if text != target_text:
                break
            distinct_users.add(user_id)

        if len(distinct_users) < min_distinct_users:
            return False, "未达到复读触发条件"

        # 检测是否为图片消息
        picid_match = self._PICID_RE.match(target_text)
        if picid_match:
            return await self._repeat_image(picid_match.group(1))

        send_ok = await self.send_text(target_text, storage_message=False)
        if send_ok:
            return True, "复读成功"
        return False, "复读发送失败"

    async def _repeat_image(self, picid: str) -> Tuple[bool, str]:
        """根据 picid 查找图片并发送"""
        from src.common.database.database_model import Images

        image_record = Images.get_or_none(Images.image_id == picid)
        if not image_record or not image_record.path or not os.path.exists(image_record.path):
            return False, "图片数据不可用"

        with open(image_record.path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        send_ok = await self.send_image(image_base64, storage_message=False)
        if send_ok:
            return True, "复读图片成功"
        return False, "复读图片发送失败"


@register_plugin
class RepeaterPlugin(BasePlugin):
    plugin_name: str = "repeater_plugin"
    enable_plugin: bool = True
    dependencies: List[str] = []
    python_dependencies: List[str] = []
    config_file_name: str = "config.toml"
    config_section_descriptions = {"plugin": "插件基本信息", "repeater": "复读器配置"}
    config_schema: dict = {
        "plugin": {
            "name": ConfigField(type=str, default="repeater_plugin", description="插件名称"),
            "version": ConfigField(type=str, default="1.0.0", description="插件版本"),
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
        },
        "repeater": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用复读"),
            "min_distinct_users": ConfigField(type=int, default=2, description="触发复读所需的最少不同用户数"),
            "recent_limit": ConfigField(type=int, default=20, description="统计最近消息条数"),
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        components: List[Tuple[ComponentInfo, Type]] = []
        if self.config.get("repeater", {}).get("enabled", True):
            components.append((RepeaterAction.get_action_info(), RepeaterAction))
        return components
