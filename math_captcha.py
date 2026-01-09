# math_captcha.py
import base64
import re
import random
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from zai import ZhipuAiClient

# -------------------------- 验证码配置项(纯时间配置，无任何xpath/页面配置) --------------------------
INITIAL_RETRY_DELAY = 2    # 初始重试等待时间（秒）
MAX_RETRY_DELAY = 10       # 最大重试等待时间（秒）
BACKOFF_FACTOR = 1.5       # 等待时间递增系数
# --------------------------------------------------------------------------------------------------

def refresh_captcha(browser, captcha_img_elem=None, captcha_img_xpath=None):
    """
    刷新验证码图片（点击图片父级a标签实现刷新，失败则刷新整个页面）
    :param browser: selenium浏览器驱动对象
    :param captcha_img_elem: 验证码图片元素对象，有则优先使用
    :param captcha_img_xpath: 验证码图片的XPATH【必填】
    :return: None
    """
    try:
        if captcha_img_elem:
            # 点击验证码图片的父级标签刷新
            captcha_link = captcha_img_elem.find_element(By.XPATH, './..')
            captcha_link.click()
            time.sleep(1)
            print("✅ 验证码图片已刷新")
        else:
            # 重新定位验证码图片后刷新
            captcha_img = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.XPATH, captcha_img_xpath))
            )
            captcha_link = captcha_img.find_element(By.XPATH, './..')
            captcha_link.click()
            time.sleep(1)
            print("✅ 验证码图片已刷新")
    except Exception as e:
        # 点击刷新失败，降级策略：刷新整个页面
        browser.refresh()
        time.sleep(2)
        print(f"⚠️ 验证码刷新失败，已刷新页面 | 异常: {e}")

def get_captcha_base64(browser, captcha_img_elem):
    """
    将验证码图片转换为base64编码（纯工具方法，无页面参数）
    :param browser: selenium浏览器驱动对象
    :param captcha_img_elem: 验证码图片元素对象
    :return: 成功返回(base64编码字符串, 图片格式)，失败返回(None, None)
    """
    # 等待图片完全加载完成，避免获取空白图片
    WebDriverWait(browser, 10).until(
        lambda d: captcha_img_elem.get_attribute('complete') == 'true'
    )
    
    img_src = captcha_img_elem.get_attribute('src')
    try:
        if img_src.startswith('data:image'):
            img_format = img_src.split(';')[0].split('/')[1]
            base64_data = img_src.split(',')[1]
        else:
            captcha_screenshot = captcha_img_elem.screenshot_as_png
            base64_data = base64.b64encode(captcha_screenshot).decode('utf-8')
            img_format = 'png'
        return base64_data, img_format
    except Exception as e:
        print(f"❌ 图片转Base64失败: {e}")
        return None, None

def clean_captcha_result(raw_result):
    """
    清洗LLM返回的验证码结果，只保留纯数字计算结果（纯数据处理）
    :param raw_result: 智谱AI返回的原始识别结果
    :return: 清洗后的纯数字/None
    """
    if not raw_result:
        return None

    abnormal_markers = ["<|observation|>", "识别失败", "无法识别", "错误", "异常", "无结果"]
    if any(marker in raw_result for marker in abnormal_markers):
        print(f"⚠️ 识别结果异常: {raw_result}")
        return None

    numbers = re.findall(r'\d+', raw_result)
    if numbers:
        return numbers[-1]
    else:
        print(f"⚠️ 未提取到有效数字: {raw_result}")
        return None

def recognize_captcha_with_llm(base64_img, img_format, zhipu_api_key):
    """
    调用智谱AI GLM-4V 识别算术验证码（纯接口调用，无页面参数）
    :param base64_img: 验证码图片base64编码
    :param img_format: 图片格式 png/jpg
    :param zhipu_api_key: 智谱AI的API_KEY
    :return: 识别后的纯数字结果/None
    """
    if not base64_img:
        print("❌ 图片编码为空，无法调用识别接口")
        return None

    client = ZhipuAiClient(api_key=zhipu_api_key)
    messages = [
        {
            "role": "system",
            "content": "你是算术验证码识别专家，仅返回计算结果的纯数字，无任何多余文字、符号、空格。例如8+5返回13，12-7返回5，9×6返回54。"
        },
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/{img_format};base64,{base64_img}"}},
                {"type": "text", "text": "识别图片中的算术表达式，只返回最终计算结果的数字，不要任何其他内容。"}
            ]
        }
    ]

    try:
        response = client.chat.completions.create(
            model="glm-4v",
            messages=messages,
            temperature=0.0,
            timeout=30
        )
        raw_result = response.choices[0].message.content.strip()
        print(f"ℹ️ AI原始返回: {raw_result}")
        return clean_captcha_result(raw_result)
    except Exception as e:
        print(f"❌ AI调用异常: {type(e).__name__} - {e}")
        return None

def get_valid_captcha_result(browser, wait, zhipu_api_key, captcha_img_xpath):
    """
    无限重试获取有效的验证码结果（核心函数，直到识别成功为止）
    :param browser: selenium浏览器驱动对象
    :param wait: WebDriverWait显式等待对象
    :param zhipu_api_key: 智谱AI的API_KEY
    :param captcha_img_xpath: 验证码图片的XPATH 【必填，无默认值】
    :return: (有效验证码结果, 验证码图片元素对象)
    """
    retry_delay = INITIAL_RETRY_DELAY
    retry_count = 0

    while True:
        retry_count += 1
        print(f"\n=============== 第 {retry_count} 次识别验证码 ===============")
        # 1. 定位验证码图片元素
        try:
            captcha_img = wait.until(EC.presence_of_element_located((By.XPATH, captcha_img_xpath)))
        except Exception as e:
            print(f"❌ 定位验证码图片失败: {e}")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * BACKOFF_FACTOR + random.uniform(0, 1), MAX_RETRY_DELAY)
            browser.refresh()
            continue

        # 2. 转Base64编码
        base64_img, img_format = get_captcha_base64(browser, captcha_img)
        if not base64_img:
            print("⚠️ 图片编码失败，准备重试")
            refresh_captcha(browser, captcha_img, captcha_img_xpath)
            retry_delay = min(retry_delay * BACKOFF_FACTOR + random.uniform(0, 1), MAX_RETRY_DELAY)
            time.sleep(retry_delay)
            continue

        # 3. 调用AI识别
        captcha_result = recognize_captcha_with_llm(base64_img, img_format, zhipu_api_key)
        if captcha_result:
            print(f"🎉 识别成功！验证码结果: {captcha_result}")
            return captcha_result, captcha_img

        # 4. 识别失败，刷新重试
        print(f"❌ 识别失败，{round(retry_delay,2)}秒后重试...")
        refresh_captcha(browser, captcha_img, captcha_img_xpath)
        retry_delay = min(retry_delay * BACKOFF_FACTOR + random.uniform(0, 1), MAX_RETRY_DELAY)
        time.sleep(retry_delay)

def auto_fill_captcha_and_submit(browser, wait, zhipu_api_key, captcha_img_xpath, captcha_input_xpath, submit_btn_xpath):
    """
    【一站式核心主函数】整合所有流程：获取验证码 → 输入验证码 → 点击提交按钮
    无任何硬编码，所有xpath均外部传入，这是你最常调用的函数！
    :param browser: selenium浏览器驱动对象
    :param wait: WebDriverWait显式等待对象
    :param zhipu_api_key: 智谱AI的API_KEY
    :param captcha_img_xpath: 验证码图片XPATH 【必填】
    :param captcha_input_xpath: 验证码输入框XPATH 【必填】
    :param submit_btn_xpath: 登录/提交按钮XPATH 【必填】
    :return: 提交前的原始URL（用于后续校验登录状态）
    """
    # 1. 获取有效验证码结果
    captcha_result, _ = get_valid_captcha_result(browser, wait, zhipu_api_key, captcha_img_xpath)
    
    # 2. 定位输入框，清空并输入验证码
    try:
        captcha_input = wait.until(EC.visibility_of_element_located((By.XPATH, captcha_input_xpath)))
        captcha_input.clear()
        captcha_input.send_keys(captcha_result)
        print(f"✅ 验证码[{captcha_result}]已填入输入框")
    except Exception as e:
        print(f"❌ 定位/输入验证码输入框失败: {e}")
        browser.refresh()
        raise e

    # 3. 定位提交按钮并点击
    try:
        submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, submit_btn_xpath)))
        submit_btn.click()
        print("✅ 已点击提交/登录按钮")
    except Exception as e:
        print(f"❌ 定位/点击提交按钮失败: {e}")
        browser.refresh()
        raise e

    # 返回原始URL，用于校验登录是否成功
    original_url = browser.current_url
    return original_url

def is_login_successful(browser, original_url, wait, timeout=5):
    """
    校验登录/提交是否成功（通过URL是否跳转判断）
    :param browser: selenium浏览器驱动对象
    :param original_url: 提交前的原始页面URL
    :param wait: WebDriverWait显式等待对象
    :param timeout: 等待跳转超时时间
    :return: True=成功，False=失败
    """
    try:
        wait.until(EC.url_changes(original_url))
        print("🎉 登录/提交成功！页面已跳转")
        return True
    except:
        print("❌ 登录/提交失败！页面未跳转")
        return False