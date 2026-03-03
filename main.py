"""
main.py - 主入口 & 任务调度引擎
========================================
这是脚本的核心，负责：
  1. 初始化：找到游戏窗口
  2. 任务调度：按照定义好的流程自动执行任务
  3. 异常处理：超时重试、未知界面恢复

设计思路（借鉴 MAA 的 Pipeline / 状态机模式）：
  - 每个"任务节点"定义了：我期望看到什么界面 → 我要做什么操作 → 成功后去哪
  - 任务引擎不断循环：截图 → 识别当前界面 → 执行对应操作 → 跳转下一节点
  - 这种设计的好处是：添加新功能只需添加新的任务节点，不需要改引擎代码
"""

import time
import sys
from controller import find_game_window, capture_window, click_at
from recognizer import find_template
from config import (
    TEMPLATES, LOOP_INTERVAL, TASK_TIMEOUT, DEBUG
)


def log(msg: str):
    """日志输出"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")


# ==================== 任务定义 ====================
# 每个任务节点是一个字典，描述：
#   - "template": 期望看到的界面（用于确认"我到了正确的位置"）
#   - "action":   要执行的动作类型
#   - "target":   要点击的按钮模板
#   - "next":     操作成功后跳转到的下一个任务
#   - "timeout":  等待超时秒数
#   - "on_timeout": 超时后跳转到的任务（用于异常恢复）
#
# 你可以不断扩展这个字典来添加更多自动化功能

TASK_PIPELINE = {
    # ---- 任务1: 从主界面点击"任务"按钮 ----
    "click_mission_btn": {
        "description": "在主界面点击任务按钮",
        "template": TEMPLATES["main_screen"],       # 前提：我在主界面
        "action": "click",
        "target": TEMPLATES["mission_btn"],          # 点击：任务按钮
        "next": "click_collect_all",                 # 成功后：去收集奖励
        "timeout": TASK_TIMEOUT,
        "on_timeout": "click_mission_btn",           # 超时：重试自己
    },

    # ---- 任务2: 在任务面板点击"收集全部" ----
    "click_collect_all": {
        "description": "在任务面板点击收集全部",
        "template": TEMPLATES["mission_panel"],      # 前提：我在任务面板
        "action": "click",
        "target": TEMPLATES["collect_all_btn"],      # 点击：收集全部
        "next": "done",                              # 成功后：完成
        "timeout": TASK_TIMEOUT,
        "on_timeout": "click_mission_btn",           # 超时：回主界面重试
    },

    # ---- 结束标记 ----
    "done": {
        "description": "所有任务完成",
        "action": "finish",
    },
}


# ==================== 任务执行引擎 ====================

def run_task(task_name: str, hwnd: int) -> str:
    """
    执行单个任务节点。

    工作流程：
    1. 不断截图检测
    2. 等待看到期望的界面 (template)
    3. 在界面中找到目标按钮 (target) 并点击
    4. 返回下一个任务的名称

    Args:
        task_name: 任务节点的名称（TASK_PIPELINE 中的 key）
        hwnd:      游戏窗口句柄

    Returns:
        下一个要执行的任务名称
    """
    task = TASK_PIPELINE[task_name]

    # 如果是结束任务，直接返回
    if task.get("action") == "finish":
        log("✅ 所有任务已完成！")
        return None

    log(f"\n{'='*40}")
    log(f"执行任务: {task['description']}")
    log(f"{'='*40}")

    start_time = time.time()
    timeout = task.get("timeout", TASK_TIMEOUT)

    while True:
        # --- 检查超时 ---
        elapsed = time.time() - start_time
        if elapsed > timeout:
            log(f"⏰ 任务超时 ({timeout}s)，跳转到: {task['on_timeout']}")
            return task["on_timeout"]

        # --- 截图 ---
        screenshot = capture_window(hwnd)
        if screenshot is None:
            log("截图失败，等待重试...")
            time.sleep(LOOP_INTERVAL)
            continue

        # --- 检查是否到达期望的界面 ---
        template_pos = find_template(screenshot, task["template"])
        if template_pos is None:
            # 还没到期望界面，继续等待
            log(f"等待界面加载... ({elapsed:.0f}s/{timeout}s)")
            time.sleep(LOOP_INTERVAL)
            continue

        # --- 到达期望界面！执行操作 ---
        if task["action"] == "click":
            # 查找要点击的按钮
            target_pos = find_template(screenshot, task["target"])
            if target_pos:
                log(f"🖱️ 点击目标: ({target_pos[0]}, {target_pos[1]})")
                click_at(hwnd, target_pos[0], target_pos[1])
                time.sleep(1)  # 等待界面切换
                return task["next"]  # 跳转到下一个任务
            else:
                log("找到了界面但未找到目标按钮，重试...")

        time.sleep(LOOP_INTERVAL)


def run_pipeline(start_task: str = "click_mission_btn"):
    """
    运行整个任务流水线。

    从指定的起始任务开始，按照每个任务的 "next" 字段
    依次执行，直到到达 "done" 或出错。

    Args:
        start_task: 起始任务的名称
    """
    # --- 初始化：找到游戏窗口 ---
    log("正在查找游戏窗口...")
    hwnd = find_game_window()
    if hwnd == 0:
        log("❌ 未找到游戏窗口，请先启动游戏！")
        log("提示：运行 python capture_template.py 可查看所有窗口标题")
        sys.exit(1)

    log(f"✅ 找到游戏窗口 (hwnd={hwnd})")
    log(f"开始执行任务流水线，起始任务: {start_task}\n")

    # --- 任务调度循环 ---
    current_task = start_task
    max_retries = 10       # 最大重试次数，防止无限循环
    retry_count = 0

    while current_task is not None:
        # 防止死循环
        retry_count += 1
        if retry_count > max_retries:
            log("❌ 超过最大重试次数，脚本终止")
            log("可能原因：模板图片不匹配、游戏界面发生变化")
            break

        # 检查任务是否存在
        if current_task not in TASK_PIPELINE:
            log(f"❌ 未知任务: {current_task}")
            break

        # 执行当前任务，获取下一个任务名称
        next_task = run_task(current_task, hwnd)

        # 如果成功前进到新任务（不是重试），重置重试计数
        if next_task != current_task:
            retry_count = 0

        current_task = next_task

    log("\n脚本运行结束")


# ==================== 程序入口 ====================

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════╗
    ║   明日方舟 - 自动化日常助手          ║
    ║   最小可运行版本 v0.1                ║
    ╚══════════════════════════════════════╝
    """)

    # 检查模板文件是否准备好
    import os
    missing_templates = []
    for name, path in TEMPLATES.items():
        if not os.path.exists(path):
            missing_templates.append(f"  - {name}: {path}")

    if missing_templates:
        print("⚠️  以下模板图片尚未准备：")
        for t in missing_templates:
            print(t)
        print()
        print("请先运行 python capture_template.py 截图，")
        print("然后从截图中裁剪出对应的按钮图片。")
        print("详细说明见 README.md")
        print()

        # 询问是否继续（方便调试）
        choice = input("是否仍然继续运行？(y/N): ").strip().lower()
        if choice != 'y':
            print("已退出。")
            sys.exit(0)

    # 启动任务流水线
    try:
        run_pipeline()
    except KeyboardInterrupt:
        # Ctrl+C 优雅退出
        print("\n\n用户中断，脚本已停止。")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()