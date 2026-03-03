"""
capture_template.py - 模板截图工具
========================================
用途：截取游戏窗口画面，保存为图片文件。
你可以从保存的截图中裁剪出需要的按钮模板。

使用方法:
    python capture_template.py

运行后会：
1. 列出所有可见窗口，帮你确认游戏窗口标题
2. 截取游戏窗口画面
3. 保存到 templates/screenshot.png
"""

import os
import sys

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(__file__))

from controller import find_game_window, capture_window, list_all_windows
from config import TEMPLATE_DIR


def main():
    print("=" * 50)
    print("  明日方舟 - 模板截图工具")
    print("=" * 50)

    # --- 第1步：列出所有窗口，帮助用户确认窗口标题 ---
    print("\n当前系统中的可见窗口：")
    print("-" * 50)
    windows = list_all_windows()
    for hwnd, title in windows:
        print(f"  [{hwnd}] {title}")
    print("-" * 50)

    # --- 第2步：查找游戏窗口 ---
    print(f"\n正在查找游戏窗口...")
    hwnd = find_game_window()

    if hwnd == 0:
        print("\n❌ 未找到游戏窗口！")
        print("请检查：")
        print("  1. 游戏是否已启动")
        print("  2. config.py 中的 WINDOW_TITLE 是否与上面列出的标题一致")
        print("\n你可以在上面的窗口列表中找到正确的标题，")
        print("然后修改 config.py 中的 WINDOW_TITLE。")
        return

    # --- 第3步：截图 ---
    print("正在截图...")
    screenshot = capture_window(hwnd)

    if screenshot is None:
        print("❌ 截图失败！请确保游戏窗口没有被最小化。")
        return

    # --- 第4步：保存截图 ---
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    save_path = os.path.join(TEMPLATE_DIR, "screenshot.png")
    screenshot.save(save_path)
    print(f"\n✅ 截图已保存: {save_path}")
    print(f"   截图尺寸: {screenshot.size[0]} x {screenshot.size[1]}")

    # --- 提示后续操作 ---
    print("\n" + "=" * 50)
    print("  接下来你需要做：")
    print("=" * 50)
    print(f"""
1. 用图片编辑工具打开 {save_path}

2. 从截图中裁剪出以下区域，分别保存：
   - templates/main_screen.png   → 主界面上的某个特征区域
                                    （用于判断是否在主界面）
   - templates/mission_btn.png   → "任务" 按钮
   - templates/mission_panel.png → 任务面板的特征区域
   - templates/collect_all_btn.png → "收集全部" 按钮

3. 裁剪技巧：
   - 选择有特色的区域，避免纯色块
   - 按钮裁剪要精确，不要包含太多背景
   - 保持与游戏相同的分辨率

4. 裁剪完成后，运行 python main.py 开始自动化
""")


if __name__ == "__main__":
    main()