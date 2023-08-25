import re
import time
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service


BASE_SEARCH_URL = "https://info.51.ca/search?q="


class URLFetch51ca:
    def __init__(self, driver):
        self.driver = driver
        self.search_term = ''

    def _multi_image_checker(self):
            is_multi_image = False
            try:
                driver.find_element(By.CSS_SELECTOR, ".img-wrap")
                is_multi_image = True 
            except NoSuchElementException:
                pass
            
            return is_multi_image
    
    # XXX Should probably use URLlib
    def _get_url(self, page_num=None):
        url = f"{BASE_SEARCH_URL}/{self.search_term}"
        if page_num:
            url = f"{url}&page={page_num}"
        return url


    def _fetch_urls_from_page(self, page_num):
        urls = []
        #XXX SHould use URLlib
        driver.get(self._get_url(page_num=page_num))

        # First objective is to get the urls from the ten search results per-page, with the following variation:
        if (
                self._multi_image_checker() == False
        ):  # Multi-picture results not present in search results
            urls = list(
                filter(
                    None,
                    [
                        x.get_attribute("href")
                        for x in driver.find_elements(
                        By.XPATH, './/ul[@class="news-list"]/li/*'
                    )
                    ],
                )
            )

        else:
            # Multi-picture results present in search results
            urls = list(
                filter(
                    None,
                    [
                        x.get_attribute("href")
                        for x in driver.find_elements(
                        By.XPATH, './/ul[@class="news-list"]/li/*'
                    )
                    ],
                )
            )
            urls += list(
                filter(
                    None,
                    [
                        x.get_attribute("href")
                        for x in driver.find_elements(
                        By.XPATH, './/ul[@class="news-list"]/li/h3/*'
                    )
                    ],
                )
            )

        return urls

    # Get the URLs for a search result
    def url_fetch(self, keyword, max_page_depth=None):
        self.search_term = keyword

        time.sleep(1)
        self.driver.get(self._get_url())
        logging.info(f"started web driver:{driver.current_url}")
        result_pages = driver.find_element(By.ID, "pagination")
        max_page = max_page_depth or int(
            re.search(r".*?(?=\s*›)", result_pages.text).group(0)) + 1
          # The last page of search results

        for i in range(
            1, max_page): #Loop to harvest all of the results (based on max page)
            for url in self._fetch_urls_from_page(i):
                yield url
            time.sleep(0.25)


if __name__ == '__main__':

    service = Service()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=service, options=options)

    u = URLFetch51ca(driver)

    for url in u.url_fetch("Pumpkin", max_page_depth=5):
        print(url)

