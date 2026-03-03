"""
config.py - 全局配置文件
========================================
在这里集中管理所有可调节的参数。
首次使用时，你可能需要修改 WINDOW_TITLE 来匹配你的游戏窗口标题。
"""

# ==================== 游戏窗口配置 ====================

# 游戏窗口标题（用于定位窗口）
# 提示：如果脚本找不到窗口，请打开游戏后运行 capture_template.py，
#       它会列出所有可见窗口的标题，帮你找到正确的名称
WINDOW_TITLE = "明日方舟"

# ==================== 识别配置 ====================

# 模板匹配的置信度阈值（0.0 ~ 1.0）
# 越高越严格：太高可能识别不到，太低可能误识别
# 建议范围：0.75 ~ 0.90
MATCH_THRESHOLD = 0.8

# ==================== 时间配置（单位：秒） ====================

# 每次截图+识别的间隔时间
# 太短会占用 CPU，太长会反应迟钝
LOOP_INTERVAL = 1.0

# 点击后的等待时间（等待游戏响应）
CLICK_DELAY = 1.5

# 单个任务的超时时间
TASK_TIMEOUT = 15

# ==================== 模板图片路径 ====================

import os

# 模板图片目录
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

# 各模板图片的路径（你需要自己截图并放到 templates/ 目录下）
TEMPLATES = {
    # 主界面特征图（用于判断"当前是否在主界面"）
    "main_screen": os.path.join(TEMPLATE_DIR, "main_screen.png"),

    # 主界面上的"任务"按钮
    "mission_btn": os.path.join(TEMPLATE_DIR, "mission_btn.png"),

    # 任务面板中的"收集全部"按钮
    "collect_all_btn": os.path.join(TEMPLATE_DIR, "collect_all_btn.png"),

    # 任务面板特征图（用于判断"当前是否在任务面板"）
    "mission_panel": os.path.join(TEMPLATE_DIR, "mission_panel.png"),
}

# ==================== 日志配置 ====================

# 是否在控制台输出详细日志
DEBUG = True