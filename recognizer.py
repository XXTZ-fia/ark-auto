"""
recognizer.py - 识别层
========================================
负责从截图中识别游戏界面元素：
  1. 模板匹配 —— 在截图中查找预先截好的按钮/图标图片
  2. 界面状态判断 —— 判断当前处于哪个界面

核心原理（模板匹配）：
  模板匹配就是拿一张小图（模板），在大图（截图）上滑动比较，
  找到最相似的位置。OpenCV 的 matchTemplate 函数帮我们完成计算，
  返回每个位置的"相似度分数"，我们取分数最高的位置。
"""

import os
import cv2
import numpy as np
from PIL import Image
from config import MATCH_THRESHOLD, TEMPLATE_DIR, DEBUG


def log(msg: str):
    """调试日志输出"""
    if DEBUG:
        print(f"[Recognizer] {msg}")


def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """
    将 PIL Image 转为 OpenCV 格式（numpy 数组）。

    PIL 和 OpenCV 的图像格式有两个主要区别：
    - PIL 用 RGB 通道顺序，OpenCV 用 BGR
    - OpenCV 用 numpy 数组存储图像

    Args:
        pil_image: PIL Image 对象

    Returns:
        numpy 数组格式的图像（BGR 颜色空间）
    """
    rgb_array = np.array(pil_image)            # PIL -> numpy (RGB)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)  # RGB -> BGR
    return bgr_array


def find_template(
    screenshot: Image.Image,
    template_path: str,
    threshold: float = None
) -> tuple | None:
    """
    在截图中查找模板图片的位置。

    这是整个识别系统的核心函数。

    原理：
    1. 将截图和模板都转为灰度图（去掉颜色信息，加快匹配速度）
    2. 用 cv2.matchTemplate 在截图上滑动模板，计算每个位置的相似度
    3. 找到相似度最高的位置
    4. 如果最高相似度 >= 阈值，认为匹配成功

    Args:
        screenshot:     PIL Image 格式的游戏截图
        template_path:  模板图片的文件路径
        threshold:      匹配阈值（0~1），None 时使用 config 中的默认值

    Returns:
        匹配成功: (center_x, center_y) 模板中心在截图中的坐标
        匹配失败: None
    """
    if threshold is None:
        threshold = MATCH_THRESHOLD

    # --- 检查模板文件是否存在 ---
    if not os.path.exists(template_path):
        log(f"模板文件不存在: {template_path}")
        return None

    # --- 将截图和模板都转为灰度图 ---
    # 灰度图只有亮度信息，单通道，匹配速度更快
    screenshot_gray = cv2.cvtColor(pil_to_cv2(screenshot), cv2.COLOR_BGR2GRAY)
    template_gray = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if template_gray is None:
        log(f"模板图片读取失败: {template_path}")
        return None

    template_h, template_w = template_gray.shape  # 模板的高度和宽度

    # --- 执行模板匹配 ---
    # TM_CCOEFF_NORMED: 归一化的相关系数匹配法
    # 返回一个"热力图"，每个像素值代表该位置的匹配分数（-1 ~ 1）
    result = cv2.matchTemplate(
        screenshot_gray,
        template_gray,
        cv2.TM_CCOEFF_NORMED
    )

    # 找到匹配分数最高的位置
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    template_name = os.path.basename(template_path)
    log(f"模板 '{template_name}' 最高匹配度: {max_val:.3f} (阈值: {threshold})")

    # --- 判断是否匹配成功 ---
    if max_val >= threshold:
        # max_loc 是匹配区域的左上角坐标
        # 我们需要返回中心坐标（因为点击应该点在按钮中间）
        center_x = max_loc[0] + template_w // 2
        center_y = max_loc[1] + template_h // 2
        log(f"  ✓ 匹配成功！中心坐标: ({center_x}, {center_y})")
        return (center_x, center_y)
    else:
        log(f"  ✗ 未匹配到")
        return None


def find_all_templates(
    screenshot: Image.Image,
    template_path: str,
    threshold: float = None
) -> list:
    """
    在截图中查找模板图片的所有匹配位置（不只是最佳匹配）。
    适用于界面上有多个相同按钮的场景。

    Args:
        screenshot:     PIL Image 格式的截图
        template_path:  模板图片路径
        threshold:      匹配阈值

    Returns:
        匹配位置列表: [(x1, y1), (x2, y2), ...]
    """
    if threshold is None:
        threshold = MATCH_THRESHOLD

    if not os.path.exists(template_path):
        return []

    screenshot_gray = cv2.cvtColor(pil_to_cv2(screenshot), cv2.COLOR_BGR2GRAY)
    template_gray = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if template_gray is None:
        return []

    template_h, template_w = template_gray.shape

    result = cv2.matchTemplate(
        screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED
    )

    # np.where 找到所有超过阈值的位置
    locations = np.where(result >= threshold)
    points = []

    for pt in zip(*locations[::-1]):  # 注意：np.where 返回 (y, x)，需要反转
        center_x = pt[0] + template_w // 2
        center_y = pt[1] + template_h // 2
        points.append((center_x, center_y))

    # 去除重叠的匹配点（距离太近的只保留一个）
    points = _remove_duplicates(points, min_distance=20)

    log(f"模板 '{os.path.basename(template_path)}' 找到 {len(points)} 个匹配")
    return points


def _remove_duplicates(points: list, min_distance: int = 20) -> list:
    """
    去除距离过近的重复匹配点。
    模板匹配经常在同一个按钮附近产生多个匹配结果，需要合并。

    Args:
        points: 坐标列表
        min_distance: 最小间距，小于此距离的点被视为重复

    Returns:
        去重后的坐标列表
    """
    if not points:
        return []

    filtered = [points[0]]
    for pt in points[1:]:
        # 检查新点是否与已有点距离过近
        is_duplicate = False
        for existing in filtered:
            distance = ((pt[0] - existing[0]) ** 2 +
                        (pt[1] - existing[1]) ** 2) ** 0.5
            if distance < min_distance:
                is_duplicate = True
                break
        if not is_duplicate:
            filtered.append(pt)

    return filtered


def check_screen_state(screenshot: Image.Image, templates: dict) -> str | None:
    """
    判断当前游戏处于哪个界面状态。

    通过尝试匹配多个界面的特征模板来判断。
    这是 MAA 中"状态机"的基础 —— 先知道"我在哪"，才能决定"做什么"。

    Args:
        screenshot:  当前截图
        templates:   状态名 -> 模板路径 的字典
                     例如: {"main_screen": "templates/main_screen.png", ...}

    Returns:
        匹配到的状态名，未识别返回 None
    """
    for state_name, template_path in templates.items():
        if find_template(screenshot, template_path) is not None:
            log(f"当前界面状态: {state_name}")
            return state_name

    log("未能识别当前界面状态")
    return None