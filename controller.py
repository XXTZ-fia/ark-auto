"""
controller.py - 控制层
========================================
负责与 Windows 系统交互：
  1. 查找游戏窗口
  2. 截取游戏画面
  3. 模拟鼠标点击

所有与操作系统相关的操作都封装在这里。
如果将来要适配其他平台（比如 ADB 模拟器），只需替换这个文件。
"""

import time
import ctypes
import win32gui
import win32ui
import win32con
import win32api
from PIL import Image
from config import WINDOW_TITLE, CLICK_DELAY, DEBUG


def log(msg: str):
    """调试日志输出"""
    if DEBUG:
        print(f"[Controller] {msg}")


# ==================== 窗口管理 ====================

def find_game_window() -> int:
    """
    通过窗口标题查找游戏窗口，返回窗口句柄 (hwnd)。

    hwnd 是 Windows 中每个窗口的唯一标识符（一个整数），
    后续的截图和点击操作都需要通过它来定位窗口。

    Returns:
        int: 窗口句柄。找不到时返回 0。
    """
    hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
    if hwnd == 0:
        log(f"未找到窗口: '{WINDOW_TITLE}'")
        log("请确保游戏已启动，或在 config.py 中修改 WINDOW_TITLE")
    else:
        log(f"找到游戏窗口: hwnd={hwnd}")
    return hwnd


def list_all_windows():
    """
    列出当前系统中所有可见窗口的标题。
    用于帮助你找到游戏窗口的准确标题。
    """
    windows = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():  # 过滤掉没有标题的窗口
                windows.append((hwnd, title))

    # EnumWindows 会遍历所有顶层窗口，对每个窗口调用 callback
    win32gui.EnumWindows(callback, None)
    return windows


def get_window_rect(hwnd: int) -> tuple:
    """
    获取窗口的位置和大小。

    Returns:
        tuple: (left, top, right, bottom) 坐标
    """
    return win32gui.GetWindowRect(hwnd)


def bring_window_to_front(hwnd: int):
    """
    将游戏窗口置于最前面（激活窗口）。
    某些点击方式需要窗口在前台才能生效。
    """
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.3)
    except Exception as e:
        log(f"置前窗口失败: {e}")


# ==================== 截图功能 ====================

def capture_window(hwnd: int) -> Image.Image | None:
    """
    截取指定窗口的画面，返回 PIL Image 对象。

    工作原理:
    1. 获取窗口的设备上下文 (DC) —— 可以理解为窗口的"画布"
    2. 创建一个兼容的位图对象
    3. 使用 BitBlt 将窗口画面拷贝到位图中
    4. 将位图数据转为 PIL Image

    Args:
        hwnd: 游戏窗口句柄

    Returns:
        PIL.Image 对象，截图失败时返回 None
    """
    try:
        # --- 第1步：获取窗口尺寸 ---
        rect = win32gui.GetClientRect(hwnd)  # 获取客户区（不含标题栏）大小
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]

        if width <= 0 or height <= 0:
            log("窗口尺寸异常，可能窗口已最小化")
            return None

        # --- 第2步：创建设备上下文和位图 ---
        # DC (Device Context) 是 Windows GDI 绘图的基础概念
        hwnd_dc = win32gui.GetWindowDC(hwnd)          # 获取窗口的 DC
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)   # 包装成 MFC DC 对象
        save_dc = mfc_dc.CreateCompatibleDC()           # 创建兼容的内存 DC

        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)

        # --- 第3步：截图 ---
        # PrintWindow 可以截取窗口内容，即使窗口被部分遮挡
        # 参数 3 表示使用 PW_RENDERFULLCONTENT 标志
        ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

        # --- 第4步：转为 PIL Image ---
        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        img = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )

        # --- 第5步：清理资源（很重要，防止内存泄漏） ---
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        log(f"截图成功: {width}x{height}")
        return img

    except Exception as e:
        log(f"截图失败: {e}")
        return None


# ==================== 模拟点击 ====================

def click_at(hwnd: int, x: int, y: int):
    """
    在游戏窗口的指定坐标处模拟鼠标左键点击。

    使用 PostMessage 发送鼠标消息，这种方式的优势是：
    - 不需要移动真实鼠标
    - 窗口不需要在最前面（"后台点击"）

    但注意：部分游戏/程序可能屏蔽 PostMessage 点击，
    如果后台点击无效，需要改用前台点击方式（见 click_at_foreground）。

    Args:
        hwnd: 游戏窗口句柄
        x: 点击位置的 X 坐标（相对于窗口客户区左上角）
        y: 点击位置的 Y 坐标
    """
    # MAKELONG 将两个 16 位整数打包成一个 32 位整数
    # 这是 Windows 消息机制的标准传参方式
    lparam = win32api.MAKELONG(x, y)

    # 发送鼠标按下消息
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN,
                         win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)  # 短暂间隔，模拟真实的按下→松开过程

    # 发送鼠标松开消息
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    log(f"点击坐标: ({x}, {y})")
    time.sleep(CLICK_DELAY)  # 等待游戏响应


def click_at_foreground(hwnd: int, x: int, y: int):
    """
    前台点击方式（备用方案）。
    会真正移动鼠标并点击，需要窗口在最前面。
    如果后台点击 (click_at) 对你的游戏不生效，改用这个。

    Args:
        hwnd: 游戏窗口句柄
        x, y: 相对于窗口客户区的坐标
    """
    # 将窗口坐标转为屏幕坐标
    rect = win32gui.GetWindowRect(hwnd)
    screen_x = rect[0] + x
    screen_y = rect[1] + y

    bring_window_to_front(hwnd)

    # 移动鼠标到目标位置
    win32api.SetCursorPos((screen_x, screen_y))
    time.sleep(0.1)

    # 模拟点击
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    log(f"前台点击坐标: ({x}, {y}) -> 屏幕({screen_x}, {screen_y})")
    time.sleep(CLICK_DELAY)