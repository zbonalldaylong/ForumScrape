import re
import time
import logging
import pickle

import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.events import AbstractEventListener

"""
###WHAT THIS IS: Scrapes website www.51.ca to allow for textual analysis
###WHAT THIS OUTPUTS: A df/pickle containing the headline, url, article body, top 5 comments, date, and number of comments for a given search term on www.51.ca
"""

DATAFRAME_FILE = "51ca-NDP.pickle"
SEARCH_TERM = "NDP"  # Term to search

INITIAL_SITE_URL = str("https://info.51.ca/search?q=" + '"' + SEARCH_TERM + '"')

logging.basicConfig(
    format="%(asctime)s, %(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=logging.INFO,
)



#Get the URLs for a search result
def url_fetch(keyword, url):
    def multi_checker(): #This function checks for multi-image returns in search results
        try:
            class_check = driver.find_element(By.CSS_SELECTOR,'.img-wrap')
        except NoSuchElementException:
            return False
        return True

    url_list = []
    time.sleep(1)
    driver.get(url)
    result_pages = driver.find_element(By.ID, 'pagination')
    max_page = int(re.search(r".*?(?=\s*›)", result_pages.text).group(0))  # The last page of search results

    for outer_ring in range(1, 5):#max_page + 1): #Loop to harvest all of the results (based on max page)
        driver.get(url + '&page=' + str(outer_ring))
        time.sleep(0.25)

        # First objective is to get the urls from the ten search results per-page, with the following variation:
        if multi_checker() == False:  # Multi-picture results not present in search results
            next_url_list = list(filter(None, [x.get_attribute('href') for x in
                                               driver.find_elements(By.XPATH, './/ul[@class="news-list"]/li/*')]))

        if multi_checker() == True:  # Multi-picture results present in search results
            next_url_list = list(filter(None, [x.get_attribute('href') for x in
                                               driver.find_elements(By.XPATH, './/ul[@class="news-list"]/li/*')]))
            additionals = list(filter(None, [x.get_attribute('href') for x in
                                             driver.find_elements(By.XPATH, './/ul[@class="news-list"]/li/h3/*')]))
            next_url_list = next_url_list + additionals

        for x in next_url_list:
            url_list.append(x)

    return url_list

def url_scraper(input):
    driver.get(input)
    try:
        article_headline = driver.find_element(By.TAG_NAME, 'h1') #Article headline
        article_headline = article_headline.text
    except: article_headline = 'None'
    try:
        article_meta = driver.find_element(By.CLASS_NAME, 'article-meta') #Meta data (author, date, comments)
    except: article_meta = 'None'
    try:
        article_author = re.search(r"(?<=作者：\s).*(?=\s*)", article_meta.text).group(0) #Article author
    except: article_author = 'None'
    try:
        article_date = re.search(r"(?<=发布：\s).*", article_meta.text).group(0) #Article date
    except: article_date = 'None'
    try:
        article_comments = re.search(r".*(?=\s评论)", article_meta.text).group(0) #Number of comments left on an article
    except: article_comments = 'None'
    try:
        article_body = driver.find_element(By.ID, 'arcbody') #Article body text (without pictures)
        article_body = article_body.text
    except: article_body = 'None'
    try:
        comment_link = driver.find_element(By.CSS_SELECTOR, '.view-all-section > div:nth-child(1) > a:nth-child(1)') #Link to comments on another website (useful in other scripts)
        comment_link = comment_link.get_attribute('href')
    except:
        comment_link = 'None'

    new_entry = [article_headline, article_body, article_author, article_date, comment_link]
    logging.info(f"new_entry: {new_entry}") #level denotes floor for displaying the message
    return new_entry

#Formats dataframe (standardize dates, convert to datetime)
def formatter(input):
    # Convert Chinese dates to datetime
    input["article_date"] = (
        input["article_date"]
        .str.replace("年", "-")
        .str.replace("月", "-")
        .str.replace("日", "X")
    )

    def datecut(input):  # Formatting for datetime conversion
        try:
            return re.findall(r".*?(?=X)", input)[0]
        except:
            return "None"

    input["article_date"] = input["article_date"].apply(datecut)
    # Get rid of 'None' entries (these are brief posts of daily headlines without comments; eg> https://info.51.ca/articles/1226208?wyacs=
    input = input[input["article_date"] != "None"]
    input["article_date"] = pd.to_datetime(input["article_date"])
    return input


if __name__ == "__main__":
    pd.set_option("mode.chained_assignment", None)
    pd.set_option("display.max_rows", None)

    service = Service()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=service, options=options)

    # Save to pickle
    #df.to_pickle(DATAFRAME_FILE)


    #Get the URL list for the search term
    final_list = url_fetch(SEARCH_TERM, INITIAL_SITE_URL)

    #Create empty DF
    df = pd.DataFrame(columns=['article_headline', 'article_body', 'article_author', 'article_date', 'comment_link'])

    #Fill DF with scrape function
    for entry in final_list:
        df = pd.concat([df, pd.DataFrame([url_scraper(entry)], columns=df.columns)], ignore_index=True)

    #Format the DF 
    df = formatter(df)


#with open ('url_list.pickle', 'wb') as f:
#    pickle.dump(final_list, f)


