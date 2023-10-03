from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from datetime import datetime
from bs4 import BeautifulSoup as bs 
import c_scrape51ca as cs
import pickle
import pandas as pd
import regex as re
import time
import logging
import platform

#Inputs from a pickle file from article scrape, outputs updated df with comments.

INPUT_FILE = '邹至蕙-article-51ca.pickle'
PICKLE_SAVE = True

pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', None    )

service = Service("/home/zbon/bin/geckodriver")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(service=service, options=options)


#['article_headline', 'article_body', 'article_author', 'article_date', 'comment_link', 'article_link']



article_df = pd.read_pickle(f'pickle/{INPUT_FILE}')


#print(article_df.columns)
#testy = article_df.loc[article_df['article_link'] == 'https://info.51.ca/articles/264777?wyacs=']


scraper = cs.CommentFetch51ca(driver)
comment_list = []

for index, row in article_df.iterrows():
    if row['comment_link'] == 'None':
        continue
    else: pass 
    for comments in scraper.comment_scrape(row['comment_link']):
        comments['article_link'] = row['article_link']
        print(comments)
        comment_list.append(comments)

comments_df = pd.DataFrame.from_dict(comment_list)
comments_df.set_index(['comment_no', 'article_link'], inplace=True)

#Save the DF
if PICKLE_SAVE == True:
    with open(f"pickle/{INPUT_FILE.replace('article', 'comments')}", "wb") as f:
        pickle.dump(comments_df, f)
else: pass

