# 洛克王国世界远行商人提醒系统

一个自动检测远行商人商品刷新并推送微信通知的工具。

## 功能特点

- ✅ **自动检测**：每天在刷新后 2 分钟自动检测（08:02, 12:02, 16:02, 20:02）
- ✅ **微信推送**：通过 Server 酱推送到微信
- ✅ **珍贵道具提醒**：检测到珍贵道具时特殊标记
- ✅ **去重机制**：同一批货物只推送一次
- ✅ **日志记录**：详细记录每次检测和推送结果

---

## 快速开始（3 分钟完成配置）

### 第一步：获取 Server 酱 SendKey（1 分钟）

1. 微信关注"方糖"公众号
2. 访问 https://sct.ftqq.com/
3. 微信扫码登录
4. 点击"发送消息"，复制 SendKey

### 第二步：配置 SendKey（30 秒）

打开 `config.ini` 文件，填入你的 SendKey：

```ini
[serverchan]
sckey = 你的 SendKey
```

### 第三步：测试推送（30 秒）

运行命令测试推送：

```bash
python main.py --test-push
```

如果微信收到消息，配置成功！

### 第四步：启动程序

```bash
python main.py
```

程序启动后会：

1. **立即检测一次**当前商人商品
2. 之后在以下时间自动检测：
   - 08:02（检测 8:00 刷新）
   - 12:02（检测 12:00 刷新）
   - 16:02（检测 16:00 刷新）
   - 20:02（检测 20:00 刷新）

---

## 命令说明

| 命令                           | 说明                 |
| ------------------------------ | -------------------- |
| `python main.py`             | 自动运行（定时检测） |
| `python main.py --manual`    | 手动检测一次         |
| `python main.py --test-push` | 测试推送功能         |
| `python main.py --help`      | 查看帮助             |

---

## 珍贵道具列表

默认珍贵道具：

- 国王球
- 棱镜球
- 炫彩精灵蛋
- 奇异血脉秘药
- 祝福项坠
- 血脉秘药（包含各种血脉秘药）

---

## 日常使用

### 查看日志

日志文件位置：`logs/reminder.log`

实时查看日志（Windows PowerShell）：

```bash
Get-Content logs\reminder.log -Tail 50 -Wait
```

### 停止程序

按 `Ctrl + C` 停止运行

---

## 高级配置

### 多账户推送

支持同时向多个微信账户推送消息，只需在 `config.ini` 中添加多个 SendKey，用逗号分隔：

```ini
[serverchan]
sckey = 你的第一个SendKey, 你的第二个SendKey, 你的第三个SendKey
```

推送时会自动向所有账户发送，日志中会显示成功发送的数量。

### 修改珍贵道具列表

打开 `config.py`，找到 `PRECIOUS_ITEMS` 列表：

```python
self.PRECIOUS_ITEMS = [
    "国王球",
    "棱镜球",
    "炫彩精灵蛋",
    "血脉秘药",
    "祝福项坠",
]
```

添加或删除你想要的道具。

### 修改检测时间

打开 `config.py`，找到 `CHECK_TIMES` 列表：

```python
self.CHECK_TIMES = [
    {"hour": 8, "minute": 2},
    {"hour": 12, "minute": 2},
    {"hour": 16, "minute": 2},
    {"hour": 20, "minute": 2},
]
```

修改为你想要的时间（格式：小时，分钟）。

### 修改日志清理周期

打开 `database.py`，找到 `clear_old_records` 方法：

```python
def clear_old_records(self, days=3):  # 修改这里的数字
```

默认保留 3 天的记录。

---

## 开机自启动（可选）

### Windows 任务计划程序

1. 按 `Win + S`，搜索"任务计划程序"
2. 点击"创建基本任务"
3. 名称：输入"洛克王国商人提醒"
4. 触发器：选择"计算机启动时"
5. 操作：选择"启动程序"
6. 程序：填写 Python 路径，例如：
   ```
   D:\Python\Python311\pythonw.exe
   ```
7. 参数：填写
   ```
   main.py
   ```
8. 起始于：填写项目路径，例如：
   ```
   E:\yx_merchant_reminder
   ```
9. 点击"完成"

---

## 常见问题

### Q: 程序启动后立即退出？

**A:**

1. 检查 Python 版本：`python --version`（需要 3.10+）
2. 安装依赖：`pip install -r requirements.txt`
3. 查看日志：`logs/reminder.log`

### Q: 收不到微信推送？

**A:**

1. 确认 `config.ini` 中的 SCKEY 正确
2. 访问 https://sct.ftqq.com/ 确认 SendKey 有效
3. 运行 `python main.py --test-push` 测试

### Q: 如何停止程序？

**A:** 按 `Ctrl + C` 或关闭命令行窗口

### Q: 程序占用很多内存？

**A:**

- 正常占用：< 50MB
- 如果过高：重启程序或清理日志文件

### Q: 可以部署到云服务器吗？

**A:** 可以！推荐配置：

- 系统：Ubuntu 20.04 或 CentOS 7+
- CPU：1 核
- 内存：512MB
- 存储：10GB

部署步骤：

1. 安装 Python 3.10+
2. 上传项目文件
3. `pip install -r requirements.txt`
4. 配置 Server 酱
5. 使用 systemd 或 supervisor 管理进程

---

## 项目结构

```
yx_merchant_reminder/
── main.py              # 主程序入口
── config.py            # 配置管理
├── config.ini           # 配置文件
├── scraper.py           # API 抓取模块
├── notifier.py          # 微信推送模块
├── database.py          # 数据库模块
├── scheduler.py         # 定时任务模块
├── requirements.txt     # Python 依赖
├── logs/                # 日志文件夹
│   └── reminder.log
── data/                # 数据文件夹
    ── merchant.db
```

---

## 技术栈

- Python 3.10+
- requests: HTTP 请求
- apscheduler: 定时任务调度
- sqlite3: 数据存储
- Server 酱：微信推送服务

---

## 注意事项

1. 程序需要 24 小时运行才能定时检测
2. 首次运行请先测试推送功能
3. 定期检查日志文件确保程序正常运行

---
