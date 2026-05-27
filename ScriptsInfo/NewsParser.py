from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

def parse_igromania_news_selenium():
    chrome_options = Options()

    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://www.igromania.ru/news/')

    time.sleep(5)

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    title = soup.title.string if soup.title else 'No title found'
    print(f'Заголовок страницы: {title}')

    driver.quit()
    return []

if __name__ == '__main__':
    parse_igromania_news_selenium()