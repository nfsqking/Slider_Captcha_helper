import io
from PIL import Image
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import ddddocr
import time

def recognize_and_input_checkcode(wait, img_xpath, input_xpath):
    time.sleep(3)
    """
    识别验证码图片并自动输入到指定输入框
    
    Args:
        wait: WebDriverWait 实例
        img_xpath: 验证码图片元素的XPath，默认值为原代码中的路径
        input_xpath: 验证码输入框的XPath，默认值为原代码中的路径
    
    Returns:
        str: 识别出的验证码字符串
    """
    # 获取验证码图片元素
    checkCode_img = wait.until(EC.visibility_of_element_located((By.XPATH, img_xpath)))
    
    # 截取验证码图片并转换为PIL对象
    img_bytes = checkCode_img.screenshot_as_png
    img = Image.open(io.BytesIO(img_bytes))
    
    # 初始化OCR并识别验证码
    ocr = ddddocr.DdddOcr()
    check_code = ocr.classification(img)
    print(f"识别到的验证码：{check_code}")
    
    # 输入验证码到输入框
    checkCode_input = wait.until(EC.element_to_be_clickable((By.XPATH, input_xpath)))
    checkCode_input.send_keys(check_code)
    time.sleep(0.5)
    
    return check_code