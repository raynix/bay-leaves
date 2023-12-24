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
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SELENIUM_HUB_URL = environ.get('SELENIUM_HUB_URL', 'localhost')
TARGETS = environ.get('TARGETS', 'https://www.google.com.au').split(',')

"""
counters = {
    'https://www.google.com.au': 1
}
"""
counters_200 = {}
counters_500 = {}


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

    url_input = driver.find_element(By.ID, 'unique-form-control')
    url_input.send_keys(url)
    send = driver.find_element(By.ID, 'unique-btn-blue')
    send.click()
    sleep(10)

def random_scroll(driver):
    height = 0
    for _ in range(0, random.randint(2, 5)):
        height += random.randint(500, 1000)
        driver.execute_script(f"window.scrollTo(0, {height});")
        sleep(10)

def crawl():
    global counters_200, counters_500
    driver = get_driver()
    try:
        for target in TARGETS:
            launch_proxyium(driver, target)
            random_scroll(driver)
            counters_200[target] = counters_200.get(target, 0) + 1
    except Exception as e:
        logger.error(e)
        counters_500[target] = counters_500.get(target, 0) + 1
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

@app.route('/metrics')
def metrics():
    result = """
# HELP bayleaves Number of http responses done by bay-leaves
# TYPE bayleaves counter
"""
    for target, count in counters_200.items():
        result += f"bayleaves{{url=\"{target}\", proxy=\"proxyium\", status=200}} {count}\n"
    for target, count in counters_500.items():
        result += f"bayleaves{{url=\"{target}\", proxy=\"proxyium\", status=500}} {count}\n"
    return result
