from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from os import environ
from time import sleep

from flask import Flask
from flask_apscheduler import APScheduler

import random

SELENIUM_HUB_URL = environ.get('SELENIUM_HUB_URL', 'localhost')
TARGETS = environ.get('TARGETS', 'https://www.google.com.au').split(',')

def get_driver():
    return webdriver.Remote(
        command_executor=f"http://{SELENIUM_HUB_URL}:4444/wd/hub",
        options=webdriver.FirefoxOptions(),
    )

def launch_proxyium(driver, url):
    driver.get('https://proxyium.com')
    sleep(10)
    # the drop down
    select = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, 'unique-nice-select')))
    select.click()
    # the singapore option
    option = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, '/html/body/main/div/div/div[2]/div/form/div[1]/div/ul/li[3]')))
    option.click()

    url_input = driver.find_element(By.XPATH, '//*[@id="unique-form-control"]')
    url_input.send_keys(url)
    send = driver.find_element(By.XPATH, '//*[@id="unique-btn-blue"]')
    send.click()

def random_scroll(driver):
    height = 0
    for _ in range(0, random.randint(2, 5)):
        height += random.randint(500, 1000)
        driver.execute_script(f"window.scrollTo(0, {height});")
        sleep(5)

def crawl():
    driver = get_driver()
    try:
        for target in TARGETS:
            launch_proxyium(driver, target)
            random_scroll(driver)
    finally:
        driver.quit()

class Config(object):
    JOBS = [
        {
            'id': 'proxyium',
            'func': 'app:crawl',
            'args': (),
            'trigger': 'interval',
            'seconds': 400
        }
    ]

app = Flask(__name__)
app.config.from_object(Config())

scheduler = APScheduler()
scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()

@app.route('/health')
def health():
    return 'OK'
