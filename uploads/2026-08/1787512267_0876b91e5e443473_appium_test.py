from appium import webdriver
from appium.options.android import UiAutomator2Options

options = UiAutomator2Options()
options.platform_name = "Android"
options.automation_name = "UiAutomator2"
options.device_name = "Z5R87DU8V4LBSOVG"
options.no_reset = True

driver = webdriver.Remote(
    "http://127.0.0.1:4723",
    options=options
)

print("Appium telefona başarıyla bağlandı!")
print("Cihaz:", driver.capabilities.get("deviceModel"))
print("Android:", driver.capabilities.get("platformVersion"))

print("\nEkran boyutu:", driver.get_window_size())

driver.quit()
print("Test tamamlandı.")