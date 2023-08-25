from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from datetime import datetime
import pickle
import pandas as pd
import re
import time

""" WHAT THIS IS: A function (comment_harvester) to fill in the entire comments for news articles hosted on 51CA, which 
# are hosted on a separate forum site (bbs51.ca) """
"""WHAT THIS OUTPUTS: The entire post/comment history as a list of tuples (author, body, likes, dislikes) """

pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', 40    )

#scraped_data = pd.read_pickle('51ca.pickle')

#print(tabulate(top_ten[['headline', 'url', 'totalcomments']], headers='keys', tablefmt='psql'))

#Function that scrapes comments from a forum site (bbs.51.ca) that hosts comments for 51.ca news articles
def comment_harvester(url):
    service = Service()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=service, options=options)
    #driver = webdriver.Firefox(executable_path=r'geckodriver.exe')
    comment_list = []
    verbose_mode = True

    #Formats the URL for loop
    thread_id = re.search(r'(?<=tid=).*', url).group(0)
    driver.get(url)
    time.sleep(1)
    try:
        result_pages = driver.find_element(By.ID, 'pgt') #Determine number of pages of comments (last page)
        max_page = int(re.search(r"(?<=\/).*(?=页)", result_pages.text).group(0).strip())
    except:
        max_page = 1
        print('MAX PAGE 1 EXCEPTION ON:', url)

    #Harvest loop (for pages of comments)
    for z in range(1, (max_page + 1)):
        if verbose_mode == True: print('TOP LEVEL:', url, 'PAGE:', z)
        likes = []
        dislikes = []
        all_posts = []
        loop_url = str('https://bbs.51.ca/thread-' + thread_id + '-' + str(z) + '-1.html')
        driver.get(loop_url)

        # DELETED POST CHECK
        try:
            delete_check = driver.find_element(By.ID, 'messagetext')
            if '指定的主题不存在或已被删除' in delete_check.text:
                break
        except: pass

        #GET THE RAW DATA
        lock_detect = driver.find_elements(By.ID, 'postlist')  # Gets raw post data
        full_posts = '\n'.join([x.text for x in lock_detect])  # Gets raw post data
        #print(full_posts)

        #GET THE POSTERS LIST
        poster_ref = driver.find_elements(By.CLASS_NAME, 'authi')
        all_posters =  [x.text for x in poster_ref if '发表于' not in x.text]
        posts_num = len(all_posters) #reference for number of posts on the page

        #Get a reference point for the year the posts are being made
        post_date = driver.find_elements(By.CLASS_NAME, 'authi')
        date_list = [re.findall(r'\d\d\d\d-\d{1,2}-\d{1,2}', x.text) for x in post_date]
        date_list = [x for x in date_list if x != []]
        date_ref = date_list[0][0]
        date_ref = datetime.strptime(date_ref, '%Y-%m-%d')

        ###NEW FORMAT###
        #Format check
        shift_date = datetime.strptime('2016-06-01', '%Y-%m-%d') #Narrow down to the date when the format changed
        new_format = True if date_ref >= shift_date else False
        if verbose_mode == True: print('NEW FORMAT:',new_format, 'DATE REF:', date_ref)
        if new_format == True:
            #GET THE POSTS
            postsplit_list = re.findall(r'只看该作者([\s\S]*?)【', full_posts) #splits posts into list
            for no, l in enumerate(postsplit_list):
                if no == 0 and z == 1: #This is for the first post in any thread; unique format for the quote
                    edit_check = re.sub('本帖最后由 (.*?)编辑', '', l).strip().replace('- 此帖来自无忧论坛手机版', '').strip()
                    print(edit_check)
                    if '评分' in edit_check and '参与' in edit_check:
                        full_post = re.search(r'\d{1,2}-\d{1,2}\n(.*?)(?=\n评分)', edit_check).group(0).strip()
                        full_post = '\n'.join(full_post.split('\n\n'))[1:]
                    else:
                        full_post = re.search(r'(?:\d{1,2}-\d{1,2}\n)(.*)', edit_check).group(0).strip()
                        full_post = '\n'.join(full_post.split('\n\n'))[1:]
                    all_posts.append(full_post)
                    if verbose_mode == True: print(full_post, '\n---')
                    continue

                if '发表于' in l:
                    edit_check = re.sub('本帖最后由 (.*?)编辑', '', l).strip() #Removes format-busting edit message statement
                    quoter = re.search(r'.*(?=发表于)', l).group(0).strip()
                    try: #with ... in the quote (an extended quote)
                        quote_regex= quoter + '([\s\S]*?)\.\.\.'
                        quote = re.search(quote_regex, edit_check).group(0).strip().replace('- 此帖来自无忧论坛手机版', '')
                        quote_text = quote.split('\n')[1].strip()
                        post = re.search(r'\n(.*?)(?=\n\d{1,2}\n\d{1,2})', edit_check).group(0).strip().replace('- 此帖来自无忧论坛手机版', '')
                        full_post = str('"' + quote_text + '"' + '(' + quoter + ')' + '\n\n' + post)
                        if verbose_mode == True: print(full_post, '\n---')
                        all_posts.append(full_post)
                        continue
                    except: #short quote (no ... in the quotation)
                       regex_string = '(?<=' + re.escape(quoter) + ' 发表于).*(?:\\n.*){2}'
                       quote = re.search(regex_string, edit_check).group(0).strip().replace('- 此帖来自无忧论坛手机版', '')
                       quote_text = quote.split('\n')[1].strip()
                       try: post = re.search(r'\n\n(.*?)(?=\n\d{1,2})', edit_check).group(0).strip()\
                           .replace('- 此帖来自无忧论坛手机版', '') #Tries for the posts that end with numbers
                       except: post = re.search(r'\n\n([\s\S]*)', edit_check).group(0).strip()\
                           .replace('- 此帖来自无忧论坛手机版', '') #Captures to the end (no numbers)
                       full_post = str('"' + quote_text + '"' + '(' + quoter + ')' + '\n\n' + post)
                       if verbose_mode == True: print(full_post, '\n---')
                       all_posts.append(full_post)
                       continue
                else:
                    edit_check = re.sub('本帖最后由 (.*?)编辑', '', l).strip().replace('- 此帖来自无忧论坛手机版', '').strip()
                    #print(edit_check, '\n---')
                    if '评分' in edit_check and '参与' in edit_check:
                        full_post = re.search(r'(.*?)(?=\n评分)', edit_check).group(
                            0)  # for posts with the supporters at end
                    else:
                        try:
                            full_post = re.search(r'(.*?)(?=\n\d{1,2})', edit_check).group(0)
                        except: full_post = edit_check
                    if verbose_mode == True: print(full_post, '\n---')
                    all_posts.append(full_post)
                    continue

            #Insert the ups and down votes
            ups = driver.find_elements(By.CLASS_NAME, 'replyadd')  # Get the number of 'likes' of each post
            ups = [x.text for x in ups if len(x.text) != 0]
            if len(ups) != 15 or len(ups) != posts_num: #This sets a default of 0 likes if it runs into trouble
                ups = [0] * posts_num
            downs = driver.find_elements(By.CLASS_NAME, 'replysubtract')  # Get the number of 'likes' of each post
            downs = [x.text for x in downs if len(x.text) != 0]
            if len(downs) != 15 or len(downs) != posts_num: #This sets a default of 0 dislikes if it runs into trouble
                downs = [0] * posts_num

            if verbose_mode == True:
            #Notification message for if a scrape fails
                if len(all_posters) == 15 and len(all_posts) == 15 and len(downs) == 15 and len(ups) == 15 and z != (max_page):
                    pass
                else:
                    print('Abnormal result on page:', z, 'at link', loop_url, '|', 'authors:', len(all_posters), 'posts:',
                          len(all_posts), 'downs:', len(downs), 'ups:', len(ups))
                    if z != (max_page): print('This is NOT the last page of the scrape.')
                    if z == (max_page): print('This is the last page of the scrape.')
            else: pass

            #Create a list of tuples of commenter, likes, and post body
            for a, p, d, l in zip(all_posters, all_posts, downs, ups):
                add = (a, p, d, l)
                comment_list.append(add)


        ###OLD FORMAT###
        if new_format == False:
            # GET THE THREAD SUBJECT
            thread_sub = driver.find_element(By.CSS_SELECTOR, '#thread_subject').text

            # GET THE POSTS
            postsplit_list = re.findall(r'只看该作者([\s\S]*?)【', full_posts)  # splits posts into list
            for no, l in enumerate(postsplit_list):
                if no == 0 and z == 1: #This is for the first post in any thread; unique format for the quote
                    try:
                        full_post = l.split('发表于')[1]
                        full_post = '\n'.join(full_post.split('\n')[1:]).strip().replace('- 此帖来自无忧论坛手机版', '')
                        all_posts.append(full_post)
                        if verbose_mode == True: print(full_post, '\n---')
                        continue
                    except: print('problem with post', l, 'at url -', url)

                if '发表于' in l:
                    edit_check = re.sub('本帖最后由 (.*?)编辑', '', l).strip() #Removes format-busting edit statement
                    edit_check = edit_check.replace(thread_sub, '').strip() #removes subject text at start of posts

                    if '评分' in edit_check and '参与' in edit_check: #Removes supporter information from end of post
                        cleaner_p = re.compile(r'^([\s\S]*?)(?=^评分)', re.MULTILINE)
                        edit_check = cleaner_p.match(edit_check).group(0)
                    else: pass

                    if '回复' in edit_check.split('\n')[0]: #Eliminate regex-busting reply message in some posts
                        reply_remover = re.compile(r'回复.*$', re.MULTILINE)
                        edit_check = reply_remover.sub('',edit_check).strip()
                    else: pass

                    quoter = re.search(r'.*(?=发表于)', l).group(0).strip()
                    #Formatting typical of most posts; quote and then post text
                    quote_regex = '^([\s\S]*?)(?=' + re.escape(quoter) + ')'
                    #quote = re.search(quote_regex, edit_check).group(0).strip().replace('- 此帖来自无忧论坛手机版', '')
                    quote_split = [x for x in re.split(quote_regex, edit_check) if x != '']
                    quote_text = quote_split[0].strip()

                    if '发表于' in quote_split[0]: #Blank quote (very rare)
                        post = '\n'.join(quote_split[0].split('\n\n')[1:]).strip()
                    else:
                        #print(url, '\n---', quote_split, '\n---')
                        post = '\n'.join(quote_split[1].split('\n')[1:]).strip() #Text in quote (very common)
                        post = re.sub(r'', '', post)

                    if len(post) == 0: #This suggests a post where the text is before the quote; likely to be inaccurate
                        post = quote_split[0].split('\n\n')[0].strip()
                        quote_text = '\n'.join(quote_split[0].split('\n\n')[1:])
                        full_post = str('"' + quote_text.strip() + '"' + '(' + quoter + ')' + '\n\n' + post.strip())
                    else: full_post = str('"' + quote_text.strip() + '"' + '(' + quoter + ')' + '\n\n' + post.strip())
                    all_posts.append(full_post)
                    if verbose_mode == True: print(full_post, '\n---')

                else: #For posts without quotes
                    edit_check = re.sub('本帖最后由 (.*?)编辑', '', l).strip().replace('- 此帖来自无忧论坛手机版', '').strip()
                    try:
                        full_post = re.search(r'(.*?)(?=\n评分)', edit_check).group(0) #for posts with the supporters at end
                    except:
                        full_post = edit_check
                    # Removes format-busting edit statement
                    all_posts.append(full_post)
                    if verbose_mode == True: print(full_post, '\n---')

            #Verify length of list
            if verbose_mode == True:
                print('author list length:', len(all_posters), 'post list length:', len(all_posts))
            #Add to the overall post list
            for bam, boom in zip(all_posters, all_posts):
                add = (bam, boom, 0, 0)
                comment_list.append(add)

    driver.close()
    return comment_list


comments = comment_harvester('https://bbs.51.ca/forum.php?mod=viewthread&tid=579111')

#[print(x) for x in comments]


#NEW - https://bbs.51.ca/forum.php?mod=viewthread&tid=1183524
#OLD - https://bbs.51.ca/forum.php?mod=viewthread&tid=553876
