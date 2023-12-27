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
INTERVAL = int(environ.get('INTERVAL', 400))

"""
counters = {
    'https://www.google.com.au:::proxy-name:::200': 1
}
"""
counters = {}

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

def launch_bypass(driver, url):
    driver.get('https://bypasszone.net/')
    sleep(10)
    select = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, 'unique-nice-select')))
    select.click()
    option = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, '/html/body/main/div/div/div[2]/div/form/div[1]/div/ul/li[2]')))
    option.click()
    url_input = driver.find_element(By.ID, 'unique-form-control')
    url_input.send_keys(url)
    send = driver.find_element(By.ID, 'unique-btn-blue')
    send.click()
    sleep(10)

def launch_direct(driver, url):
    driver.get(url)
    sleep(10)

def launch(driver, url):

    global counters
    channels = [launch_bypass, launch_proxyium, launch_direct]
    chosen_channel = random.choice(channels)
    key = f"{url}:::{chosen_channel.__name__}"
    try:
        chosen_channel(driver, url)
        key_200 = f"{key}:::200"
        counters[key_200] = counters.get(key_200, 0) + 1
    except Exception as e:
        logger.error(e)
        key_500 = f"{key}:::500"
        counters[key_500] = counters.get(key_200, 0) + 1

def random_scroll(driver):
    height = 0
    for _ in range(0, random.randint(2, 5)):
        height += random.randint(500, 1000)
        driver.execute_script(f"window.scrollTo(0, {height});")
        sleep(random.randint(1, 5))

def crawl():
    global counters_200, counters_500
    driver = get_driver()
    try:
        for target in TARGETS:
            launch(driver, target)
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
            'seconds': INTERVAL
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
    for k, v in counters.items():
        result += "bayleaves{{url=\"{}\", proxy=\"{}\", status=\"{}\"}} {}\n".format(*k.split(":::"), v)
    return result
