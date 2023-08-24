import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from commentscrape import comment_harvester
from tabulate import tabulate
from collections import Counter


##WHAT THIS IS: Tools to format and refine scraped data
##WHAT THIS OUTPUTS: Custom dataframes based on user inputs

pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', None)

scraped_data = pd.read_pickle('51ca.pickle')

#Convert Chinese dates to datetime -- GET RID OF THIS AFTER RE-RUNNING SCRAPE
scraped_data['date'] = scraped_data['date'].str.replace('年', '-').str.replace('月', '-').str.replace('日', 'X')
def datecut(input): #Formatting for datetime conversion
    try:
        return re.findall(r'.*?(?=X)', input)[0]
    except:
        return 'None'
scraped_data['date'] = scraped_data['date'].apply(datecut)
#Get rid of 'None' entries (these are brief posts of daily headlines without comments; eg> https://info.51.ca/articles/1226208?wyacs=
scraped_data = scraped_data[scraped_data['date'] != 'None']
scraped_data['date'] = pd.to_datetime(scraped_data['date'])


###Search toggles for news###
search_term = '邹至蕙' #First search term
date_start = '2013-04-04' #Start of search date range
date_end = '2023-08-01' #End of search date range
top_results = 15 #cut output results


def news_searcher(st, dstart, dend, tresults, input_df, search=True, date=True, results=True):
    #Outputs a df of search results based on user toggles (data from newsscrape.py)
    if date == True and search == False:
        after_start_date = input_df['date'] >= dstart
        before_end_date = input_df['date'] <= dend
        range = after_start_date & before_end_date
        result_df = input_df.loc[range]

    if search == True and date == False:
        result_df = input_df[input_df['body'].str.contains(st)]
        result_df['hits'] = result_df['body'].str.count(st)

    if search == True and date == True:
        after_start_date = input_df['date'] >= dstart
        before_end_date = input_df['date'] <= dend
        range = after_start_date & before_end_date
        result_df = input_df.loc[range]
        result_df = result_df[result_df['body'].str.contains(st)]
        result_df['hits'] = result_df['body'].str.count(st)

    if results == True and (search == False and date == False):
        result_df = input_df.sort_values(by=['totalcomments'], ascending=True).tail(tresults)
    if results == True and (search == True or date == True):
        result_df = result_df.sort_values(by=['totalcomments'], ascending=True).tail(tresults)

    return result_df

def comment_adder(input_df):
    input_df['comments'] = '' #Clear out the 5 comments scraped on the website
    for index, row in input_df.iterrows():
        input_df.at[index, 'comments'] = comment_harvester(row['commentlink'])
    return input_df


#trimmed_df = comment_adder((news_searcher(search_term, date_start, date_end, top_results, scraped_data, search=True, date=True, results=True)))

df = comment_adder(news_searcher(search_term, date_start, date_end, top_results, scraped_data, search=True, date=True, results=True))


print(df['commentlink'].tolist())


for index, row in df.iterrows():
    print('COMMENT URL:', row['commentlink'], '\n')
    print('WEBSITE URL:', row['url'], '\n')
    for x in row['comments']:
        print(x[0], 'SAYS:', x[1])


df.to_pickle('tempresult.pickle')

#
# df= pd.read_pickle('tempresult.pickle')
#
# # #Displays contents of the DF
# print(tabulate(df[['headline', 'commentlink']], headers='keys', tablefmt='psql'))

#Check comments from a given comment forum link
# for index, row in df.iterrows():
#     if row['commentlink'] == 'https://bbs.51.ca/forum.php?mod=viewthread&tid=592947':
#         for x in row['comments']:
#             print(x[0])

# #Commenter counter
# commenter_list = []
# for index, row in df.iterrows():
#     for x in row['comments']:
#         commenter_list.append(x[0])

#Word search in comment (as opposed to news)
# st2 = 'Xin Ru Rong'
# for index, row in df.iterrows():
#     if row['commentlink'] == 'https://bbs.51.ca/forum.php?mod=viewthread&tid=534799':
#         print(len(row['comments']))
#         #for x in row['comments']:
#             #if st2 in x[0]:
#                 #print(row['commentlink'], '\n')
#             #print('USER:', x[0], 'SAYS:', x[1], '\n')
#
# [print(x) for x in df['comments'].loc[62]]

#Commenter search
# for index, row in df.iterrows():
#     print(row['commentlink'])
#     for x in row['comments']:
#         if 'iacrossnation' in x[0]:
#             print(x[1],'\n', '--', '\n')


# Total comment count:
# for index, row in df.iterrows():
#     if row['commentlink'] == 'https://bbs.51.ca/forum.php?mod=viewthread&tid=592947':
#         print(len(row['comments']))
#
#
