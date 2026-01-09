# 用于在selenium自动化中处理各类验证码

## 1.使用slider_captcha.py时，需在slider_verification函数中传入以下变量：
* browser: 已初始化的webdriver对象
* wait: WebDriverWait对象
* img_elem_xpath: 滑块图片元素XPath
* whole_img_elem_xpath: 整张图片元素XPath
* drag_element_xpath: 滑块元素XPath
* verify_container_xpath: 验证图片容器元素XPath
<hr>

## 2.使用math_captcha.py时，示例代码如下：

```python
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

if __name__ == '__main__':
    # ======================== 这里是你唯一需要修改的配置区 ========================
    ZHIPU_API_KEY = "你的智谱AI_API_KEY"          # 你的智谱秘钥
    TARGET_URL = "你的目标网站登录/注册地址"       # 目标网站地址
    CAPTCHA_IMG_XPATH = "验证码图片的xpath"        # 必填：验证码图片
    CAPTCHA_INPUT_XPATH = "验证码输入框的xpath"    # 必填：验证码输入框
    SUBMIT_BTN_XPATH = "登录/提交按钮的xpath"      # 必填：登录按钮
    # ============================================================================

    # 初始化浏览器和等待对象
    browser = webdriver.Chrome()
    browser.maximize_window()
    browser.get(TARGET_URL)
    wait = WebDriverWait(browser, 10)

    try:
        # 调用核心函数：识别+填入+提交
        original_url = auto_fill_captcha_and_submit(
            browser=browser,
            wait=wait,
            zhipu_api_key=ZHIPU_API_KEY,
            captcha_img_xpath=CAPTCHA_IMG_XPATH,
            captcha_input_xpath=CAPTCHA_INPUT_XPATH,
            submit_btn_xpath=SUBMIT_BTN_XPATH
        )

        # 校验登录是否成功
        login_status = is_login_successful(browser, original_url, wait)
        
        # 登录成功后的业务逻辑写在这里
        if login_status:
            print("全部流程完成，开始执行业务逻辑...")
            # browser.find_element(...) 你的后续操作

    except Exception as e:
        print(f"程序执行异常: {e}")
    finally:
        # 可选：是否关闭浏览器
        # browser.quit()
        pass
```
__！！！注意：账号密码等其他必须流程需自行完成！！！__

<hr>

## 3.使用img_captcha.py时，需在recognize_and_input_checkcode函数中传入以下变量：
* wait: WebDriverWait 实例
* img_xpath: 验证码图片元素的XPath，默认值为原代码中的路径
* input_xpath: 验证码输入框的XPath，默认值为原代码中的路径


