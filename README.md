# Repeater Plugin (复读器插件)

这是一个 MaiBot 的复读器插件，用于在群聊中自动检测并参与复读。

## 功能

当检测到连续的、相同内容的发言，并且发送者数量达到设定阈值时，机器人会自动参与复读，发送相同的内容。

*   **智能检测**：自动检测连续的相同消息（支持文本和图片）。
*   **用户去重**：只统计不同的用户，且会自动排除机器人自己的发言。
*   **可配置阈值**：可以设置触发复读所需的最少不同用户数量。
*   **Action 驱动**：使用 MaiBot 的 Action 机制实现，与 LLM 决策系统无缝集成。

## 配置

配置文件位于 `config.toml`。

```toml
[plugin]
name = "repeater_plugin"
version = "1.0.0"
enabled = true  # 是否启用插件

[repeater]
enabled = true  # 是否启用复读功能
min_distinct_users = 2  # 触发复读所需的最少不同用户数（默认 2，即第 3 个不同的人发言时触发，或者检测到前两个不同的人发言后触发？具体逻辑见代码：len(distinct_users) < min_distinct_users 则不复读，意味着需要 >= min_distinct_users）
# 注意：代码逻辑是 if len(distinct_users) < min_distinct_users: return False。
# 所以如果 min_distinct_users = 2，那么需要 distinct_users >= 2 才会复读。
# 即：只要有 2 个不同的用户发送了相同内容，机器人就会尝试复读（如果还没复读过）。
recent_limit = 20  # 统计最近消息的条数
```

## 逻辑说明

1.  插件会获取最近 `recent_limit` 条群聊消息。
2.  筛选出非机器人的消息。
3.  统计最近连续的一段相同内容的消息。
4.  计算这段相同内容的发送者中，有多少个不同的用户（`distinct_users`）。
5.  如果 `distinct_users` 的数量 **大于等于** `min_distinct_users`，则触发复读。
    *   例如 `min_distinct_users = 2`，A 说 "1"，B 说 "1"，此时不同用户数为 2，满足条件，机器人复读 "1"。

## 安装

将本插件文件夹放置在 MaiBot 的 `plugins` 目录下即可。
