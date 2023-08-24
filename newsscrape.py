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
import logging 
import pandas as pd
import re
import time

###WHAT THIS IS: Scrapes website www.51.ca to allow for textual analysis
###WHAT THIS OUTPUTS: A df/pickle containing the headline, url, article body, top 5 comments, date, and number of comments for a given search term on www.51.ca

pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', None)

service = Service()
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(service=service, options=options)
# ...

#driver = webdriver.Chrome(r"chromedriver")


search_term = "NDP" #Term to search
initial_site_url = str('https://info.51.ca/search?q=' + '\"' + search_term + '\"')

logging.basicConfig(
        format="%(asctime)s, %(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d:%H:%M:%S",
        level=logging.INFO,
    )


def harvester(keyword, url):
    def multi_checker(): #This function checks for multi-image returns in search results
        try:
            class_check = driver.find_element(By.CSS_SELECTOR,'.img-wrap')
        except NoSuchElementException:
            return False
        return True

    df_list = []

    driver.get(url) #Search URL; gets the pagination and the headlines
    time.sleep(1)
    result_pages = driver.find_element(By.ID, 'pagination')
    max_page = int(re.search(r".*?(?=\s*›)", result_pages.text).group(0)) #The last page of search results

    for outer_ring in range(1, 2):#(max_page + 1)): #Loop to harvest all of the results (based on max page)
        driver.get(url + '&page=' + str(outer_ring))
        time.sleep(1)
        #First objective is to get the urls from the ten search results per-page, with the following variation:
        if multi_checker() == False: #Multi-picture results not present in search results
            next_url_list = list(filter(None, [x.get_attribute('href') for x in driver.find_elements(By.XPATH, './/ul[@class="news-list"]/li/*')]))
            time.sleep(1)
        if multi_checker() == True: #Multi-picture results present in search results
            next_url_list = list(filter(None, [x.get_attribute('href') for x in driver.find_elements(By.XPATH, './/ul[@class="news-list"]/li/*')]))
            additionals = list(filter(None, [x.get_attribute('href') for x in driver.find_elements(By.XPATH, './/ul[@class="news-list"]/li/h3/*')]))
            next_url_list = next_url_list + additionals
            time.sleep(1)

        for inner_ring in next_url_list: #Loop to harvest the (up to) ten search results in a given page
            driver.get(inner_ring)
            time.sleep(3)
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

            #Comments --> Aims to simplify formatting and include first few comments of every article
            try:
                comment_list = driver.find_element(By.CLASS_NAME,'comment-list-section').text.split('\n')
                comment_output = ''
                for t, i in enumerate(comment_list):
                    if t == 0:
                        last_one = i
                        continue
                    if i == '':
                        continue
                    if i[0] == "@":
                        commenter_name = last_one
                    if last_one[0] == "@":
                        commenter_likes = i
                    if i == "回复":
                        commenter_content = last_one
                        comment_output = comment_output + '\n' + commenter_name + '(' + commenter_likes + '):' + commenter_content
                    last_one = i
            except: comment_output = 'None'

            #Add to list of entries
            new_entry = [article_headline, article_body, article_author, inner_ring, article_date, comment_link, article_comments, comment_output]
            logging.info(f"new_entry: {new_entry}") #level denotes floor for displaying the message
            df_list.append(new_entry)

    #Create harvest dataframe
    scraped_data = pd.DataFrame(data=df_list, columns=['headline', 'body', 'author', 'url', 'date', 'commentlink', 'totalcomments', 'comments'])

    #Format dataframe
    scraped_data['totalcomments'].replace('None', 0, inplace=True)  #Convert data types for easier sorting
    scraped_data = scraped_data.astype({'totalcomments':'int'})

    # Convert Chinese dates to datetime
    scraped_data['date'] = scraped_data['date'].str.replace('年', '-').str.replace('月', '-').str.replace('日', 'X')
    def datecut(input):  # Formatting for datetime conversion
        try:
            return re.findall(r'.*?(?=X)', input)[0]
        except:
            return 'None'
    scraped_data['date'] = scraped_data['date'].apply(datecut)
    # Get rid of 'None' entries (these are brief posts of daily headlines without comments; eg> https://info.51.ca/articles/1226208?wyacs=
    scraped_data = scraped_data[scraped_data['date'] != 'None']
    scraped_data['date'] = pd.to_datetime(scraped_data['date'])
    return scraped_data



df = harvester(search_term, initial_site_url)

# Save to pickle
df.to_pickle('51ca-NDP.pickle')

