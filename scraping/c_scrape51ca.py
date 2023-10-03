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
import pickle
import pandas as pd
import regex as re
import time
import logging


class CommentFetch51ca:

    def __init__(self, driver):
        self.driver = driver
        self.base_url = 'https://bbs.51.ca/thread'
        self.url = None

        # Logging (output to file)
        self.logger = logging.getLogger(__name__)  # creates logger
        self.logger.setLevel(logging.INFO)
        self.file_handler = logging.FileHandler('logs/commentscrape.log', encoding='utf-8', mode='w')
        self.file_format = logging.Formatter(
            '%(asctime)s, %(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
        self.file_handler.setFormatter(self.file_format)
        self.logger.addHandler(self.file_handler)

    def _format_url(self, url):
        max_page = 1
        self.thread_id = re.search(r'(?<=tid=)(.*?)(?=$)', url).group(0).strip()

        self.driver.get(url)
        pgt = self.driver.find_elements(By.ID, 'pgt')
        for x in pgt:
            if '/' in x.text:
                max_page = re.search('(?<=/)(.*?)(?=页)', x.text).group(0).strip()
        for p in range(1, int(max_page) + 1):
            yield str(f'{self.base_url}-{self.thread_id}-{p}-1.html')

    def _comment_extract(self, xpath):
        def _comment_formatter(entry):
            entry['comment'] = entry['comment'].replace('<br/>', '').replace('\n', '').strip().replace('</font>',
                                                                                                       '').replace(
                '<i>', '').replace('</i>', '')
            if ".gif" in entry['comment']:  # Emoticons
                try:
                    entry['comment'] = re.sub('<img src="(.*?)alt="">', '*Emoticon*', entry['comment'])
                except: pass
            if "ignore_js_op" in entry['comment']:  # Image embed
                try: 
                    entry['comment'] = re.sub('<ignore_js_op>([\s\S]*?)<\/ignore_js_op>', entry['comment'])
                except: pass
            if "a href" in entry['comment']:  # links with html formatting
                try:
                    replacement_text = re.search(r'(?<=blank">)(.*?)(?=</a>)', entry['comment']).group(0).strip()
                    entry['comment'] = re.sub(r'<a href=(.*?)</a>', replacement_text, entry['comment'])
                except: pass 
            if "<font " in entry['comment']:
                try:
                    entry['comment'] = re.sub(r'<font (.*?)>', '', entry['comment'])
                except: pass
            if "<img alt=" in entry['comment']:
                try:
                    entry['comment'] = re.sub(r'<img alt=([\s\S]*?)"/>', '', entry['comment'])
                except: pass
            if "<i class" in entry['comment']:
                try: 
                    entry['comment'] = re.sub(r'<i class(.*?)>', '', entry['comment'])
                except: pass
            if "本帖最后由" in entry['comment']:
                try:
                    entry['comment'] = re.sub(r'本帖最后由(.*?)编辑', '', entry['comment'])
                except: pass
            return entry

        for x in self.driver.find_elements(By.XPATH, xpath):
            quoter = None
            post_list = []

            if re.match(r'post_\d\d\d\d\d\d', x.get_attribute('id')) != None:
                raw_html = x.get_attribute('innerHTML')
                post_id = x.get_attribute('id')
                souped_html = bs(x.get_attribute('innerHTML'), 'html.parser')
                
                #Checking for atypical posts - first is for moderated posts
                if '该帖被管理员或版主屏蔽' in str(souped_html):
                    entry = {'comment_no': None, 'poster':None, 'date':None, 'comment':'Locked Post', 'quoted': None, 'likes':None, 'dislikes':None}
                    yield entry
                    self.logger.info(f'\n\nPOST ID: {post_id} \nENTRY: {entry}') #\nHTML: {souped_html}\n\n---\n\n')
                    continue
                else: pass
                
                #Note: this isn't 100%; trying to isolate and troubleshoot a missing post on https://bbs.51.ca/thread-1182385-5-1.html
                if '<!-- add supportbtns start -->\n<!-- add supportbtns end -->' in str(souped_html):
                    entry = {'comment_no': None, 'poster':None, 'date':None, 'comment':'Missing Post', 'quoted': None, 'likes':None, 'dislikes':None}
                    yield entry
                    self.logger.info(f'\n\nPOST ID: {post_id} \nENTRY: {entry}\nXXX_MISSING POST_XXX')
                    continue
                else: pass

                td_id = 'postmessage_' + str(x.get_attribute("id")).split('_')[1]
                em_id = 'authorposton' + str(x.get_attribute("id")).split('_')[1]

                full_post = x.find_element(By.ID, td_id).text
                post_author = re.search(r'(?<=color: #\w\w\w">|class="\w\w\w">)(.*?)(?=<\/a>)',
                                        x.get_attribute('innerHTML')).group(0)  # works 2023/2014
                post_date = re.search(str('(?<=' + em_id + '">发表于 )(.*?)(?=<\/em>)'), str(souped_html)).group(0)

                # Likes and dislikes
                like_id_regex = '(?<=review_support_' + (
                str(x.get_attribute("id")).split('_')[1]) + '" class="sz">)(.*?)(?=<\/span>)'
                dislike_id_regex = '(?<=review_against_' + (
                str(x.get_attribute("id")).split('_')[1]) + '" class="sz">)(.*?)(?=<\/span>)'
                likes = re.search(like_id_regex, x.get_attribute('innerHTML')).group(0) if len(
                    re.search(like_id_regex, x.get_attribute('innerHTML')).group(0)) > 0 else 0
                dislikes = re.search(dislike_id_regex, x.get_attribute('innerHTML')).group(0) if len(
                    re.search(dislike_id_regex, x.get_attribute('innerHTML')).group(0)) > 0 else 0

                # Posts with quotes
                if '<blockquote>' in str(souped_html):  # post with a quote in it
                    # Check for first post (the blockquote is a news story, not a previous user post)
                    if '§ 发表于' in str(souped_html):
                        full_post_text = re.search(str('(?<=' + td_id + '">)([\s\S]*?)(?=<\/td><\/tr>)'),
                                                   str(souped_html)).group(0)
                        entry = {'comment_no':None, 'poster': post_author, 'date': post_date, 'comment': full_post_text,
                                'quoted': 'None' if not quoter else quoter, 'likes': likes, 'dislikes': dislikes, 'article_link':None}
                        yield _comment_formatter(entry)
                        self.logger.info(
                            f'\n\nPOST ID: {post_id} \nENTRY: {entry}')  # \nHTML: {souped_html}\n\n---\n\n')
                        continue

                    html_blockquotes = re.search(r'<blockquote>([\s\S]*?)<\/td><\/tr>',
                                                 str(souped_html)).group(0)  # works 2023/2014
                    quote_raw = re.search(r'(?<=<blockquote>)([\s\S]*?)(?=<\/blockquote>)', html_blockquotes).group(0)
                    quoter = re.search(r'(?<=\d\d">|^)([^>]+)(?= 发表于)', str(souped_html), re.MULTILINE).group(
                        0).strip() if ' 发表于' in html_blockquotes else 'None'  # More efficient; works 2014/2023
                    quote_text = '"' + re.sub('<font size="2">([\s\S]*?)<\/a><\/font>', '', quote_raw).replace('<br>',
                                                                                                               '').replace(
                        '&nbsp;', '').replace('<strong>', '').replace('</strong>',
                                                                      '').strip() + '((' + quoter + '))' + '"'  # works 2014/2023
                    post_text = re.search(r'(?<=<\/blockquote><\/div>|<\/blockquote>)([\s\S]*?)(?=<\/td><\/tr>)',
                                          html_blockquotes).group(0).replace('<br>', '').replace('&nbsp;', '').replace(
                        '<strong>', '').replace('</strong>', '').strip()
                    full_post_text = quote_text + '\n' + post_text


                else:  # posts without quotes
                    # print('\n---', x.get_attribute('id'), '---\n')
                    html_noblockquotes = x.get_attribute('innerHTML')
                    fp_regex = str('(?<="' + td_id + '">)([\s\S]*?)(?=<\/td>|<\/tr>)')
                    full_post_text = re.search(fp_regex, html_noblockquotes).group(0).replace('<br>', '').replace(
                        '&nbsp;', '\n').replace('<strong>', '').replace('</strong>', '').strip()  # works 2014/2023
                    # print(post_author, 'SAYS:\n', full_post_text)
                entry = {'comment_no':None, 'poster': post_author, 'date': post_date, 'comment': full_post_text,
                        'quoted': 'None' if not quoter else quoter, 'likes': likes, 'dislikes': dislikes, 'article_link':None}
                self.logger.info(f'\n\nPOST ID: {post_id} \nENTRY:{entry}')  # \nHTML: {souped_html}\n\n---\n\n')
                yield _comment_formatter(entry)

    def comment_scrape(self, base_url):
        post_counter = 0
        for paged_url in self._format_url(base_url):
            self.logger.info(f'COMMENT URL: {paged_url} \n')
            self.driver.get(paged_url)
            for i in self._comment_extract("//div[contains(@id,'post')]"):
                post_counter += 1
                i['comment_no'] = post_counter
                yield i

#
# if __name__ == "__main__":
#     pd.set_option('mode.chained_assignment', None)
#     pd.set_option('display.max_rows', None)
#     pd.set_option('display.max_colwidth', None    )
#
#     service = Service("C:\geckodriver.exe")
#     options = webdriver.FirefoxOptions()
#     options.add_argument("--headless")
#     driver = webdriver.Firefox(service=service, options=options)
#
# cs = CommentFetch51ca(driver)
# cs.comment_scrape('https://bbs.51.ca/forum.php?mod=viewthread&tid=590142')
# #https://bbs.51.ca/forum.php?mod=viewthread&tid=536479 - regular 6 page test
# #https://bbs.51.ca/forum.php?mod=viewthread&tid=673882 - small test
