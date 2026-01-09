# slider_verify.py - 独立的滑块验证模块
import time
import base64
from io import BytesIO
from PIL import Image
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import io
import ddddocr

def slider_verification(browser, wait,img_elem_xpath,whole_img_elem_xpath,drag_element_xpath,verify_container_xpath):
    """
    滑块验证核心函数
    :param browser: 已初始化的webdriver对象
    :param wait: WebDriverWait对象
    :param img_elem_xpath: 滑块图片元素XPath
    :param whole_img_elem_xpath: 整张图片元素XPath
    :param drag_element_xpath: 滑块元素XPath
    :param verify_container_xpath: 验证图片容器元素XPath
    :return: bool - 验证是否成功（简化返回，可根据实际需求扩展）
    """
    try:
        # 1. 获取滑块图片，提取左上角+左下角关键像素
        img_elem = wait.until(EC.presence_of_element_located(
            (By.XPATH, img_elem_xpath)
        ))
        img_src = img_elem.get_attribute('src')
        if not img_src.startswith('data:image/'):
            print("滑块图片不是Base64格式，验证失败")
            return False
        
        # 解码滑块图片
        base64_data = img_src.split(',')[1]
        img_data = base64.b64decode(base64_data)
        img = Image.open(BytesIO(img_data)).convert("RGBA")
        width, height = img.size
        opaque_pixels = []

        # 筛选不透明像素（alpha>128）
        for y in range(height):
            for x in range(width):
                r, g, b, a = img.getpixel((x, y))
                if a > 128:
                    opaque_pixels.append((x, y, r, g, b))

        if not opaque_pixels:
            print("滑块图片无有效不透明像素")
            return False

        # 提取左上角（x最小y最小）和左下角（x最小y最大）
        p1 = sorted(opaque_pixels, key=lambda p: (p[0], p[1]))[0]  # 左上角
        p2 = sorted(opaque_pixels, key=lambda p: (p[0], -p[1]))[0] # 左下角
        target_p1 = (p1[0], p1[1], p1[2], p1[3], p1[4])
        target_p2 = (p2[0], p2[1], p2[2], p2[3], p2[4])
        print(f"滑块左上角：坐标({p1[0]},{p1[1]})，RGB({p1[2]},{p1[3]},{p1[4]})")
        print(f"滑块左下角：坐标({p2[0]},{p2[1]})，RGB({p2[2]},{p2[3]},{p2[4]})")

        # 2. 获取整张验证图片并解码
        whole_img_elem = wait.until(EC.presence_of_element_located(
            (By.XPATH, whole_img_elem_xpath)
        ))
        whole_img_src = whole_img_elem.get_attribute('src')
        whole_img_data = base64.b64decode(whole_img_src.split(',')[1])
        whole_img = Image.open(BytesIO(whole_img_data)).convert("RGBA")
        whole_w, whole_h = whole_img.size

        # 3. 匹配两个关键点的目标X坐标
        y_diff = target_p2[1] - target_p1[1]
        match_x = None
        for x in range(whole_w):
            # 验证左上角对应点
            if target_p1[1] >= whole_h:
                continue
            r1, g1, b1, a1 = whole_img.getpixel((x, target_p1[1]))
            # 验证左下角对应点
            y2 = target_p1[1] + y_diff
            if y2 >= whole_h:
                continue
            r2, g2, b2, a2 = whole_img.getpixel((x, y2))
            # 双点匹配条件
            if (a1 > 128 and (r1, g1, b1) == (target_p1[2], target_p1[3], target_p1[4])) and \
               (a2 > 128 and (r2, g2, b2) == (target_p2[2], target_p2[3], target_p2[4])):
                match_x = x
                break

        if match_x is None:
            print("未找到匹配的目标X坐标")
            return False
        print(f"\n图片像素目标X坐标：{match_x}")

        # 4. 计算页面缩放比例和实际滑动距离
        # 获取验证图页面显示尺寸
        whole_img_rect = whole_img_elem.rect
        page_img_w = whole_img_rect['width']
        scale_x = page_img_w / whole_w
        print(f"图片缩放比例X：{scale_x:.2f}")

        # 获取滑块和容器位置
        drag_element = wait.until(EC.element_to_be_clickable(
            (By.XPATH, drag_element_xpath)
        ))
        drag_rect = drag_element.rect
        drag_init_x = drag_rect['x']
        verify_container = browser.find_element(By.XPATH, verify_container_xpath)
        container_x = verify_container.rect['x']

        # 计算最终滑动偏移
        target_page_x = container_x + (match_x * scale_x)
        drag_offset_x = target_page_x - drag_init_x
        drag_offset_x += 3  # 补偿值，可微调
        print(f"滑块初始X：{drag_init_x}，目标页面X：{target_page_x}，实际滑动偏移：{drag_offset_x:.2f}")

        # 5. 模拟人类缓慢滑动滑块
        action = ActionChains(browser)
        action.click_and_hold(drag_element)
        # 分阶段滑动（加速→匀速→减速）
        action.move_by_offset(drag_offset_x * 0.7, 0).pause(0.1)
        action.move_by_offset(drag_offset_x * 0.25, 0).pause(0.05)
        action.move_by_offset(drag_offset_x * 0.05, 0).pause(0.1)
        action.release()
        action.perform()

        time.sleep(2)  # 等待验证结果
        print("滑块验证执行完成")
        return True

    except Exception as e:
        print(f"滑块验证过程出错：{str(e)}")
        return False

