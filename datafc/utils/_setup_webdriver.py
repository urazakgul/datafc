import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import SessionNotCreatedException
from webdriver_manager.chrome import ChromeDriverManager

def setup_webdriver() -> webdriver.Chrome:
    driver = None
    try:
        chrome_options = Options()

        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')

        system_platform = platform.system()

        if system_platform == "Linux":
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')

        elif system_platform == "Darwin":
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-popup-blocking')

        elif system_platform == "Windows":
            chrome_options.add_argument('--disable-extensions')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get("https://www.google.com")
        if "Google" not in driver.title:
            raise RuntimeError("WebDriver failed to load a test page.")

        return driver

    except SessionNotCreatedException as e:
        raise RuntimeError(
            f"WebDriver version mismatch: {e}. "
            "Try updating Chrome or WebDriver."
        )
    except Exception as e:
        if driver:
            driver.quit()
        raise RuntimeError(
            f"Failed to set up WebDriver: {e}. "
            "Ensure Google Chrome is installed and compatible with the WebDriver version."
        )