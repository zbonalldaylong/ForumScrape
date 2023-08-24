import pandas as pd
import re
import time
from tabulate import tabulate
from collections import Counter
import jieba
import jieba.analyse
import snownlp



##WHAT THIS IS: Tools to perform textual analysis on scrapes
##WHAT THIS OUTPUTS:

pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', None)

df= pd.read_pickle('tempresult.pickle')

#print(tabulate(df['headline']))
print(df['headline'])

test_comment = df['comments'].tolist()

#
# for x in test_comment:
#     print(x, '\n')


#Creates a block of text that removes quotes from the posts
#text_chunk = re.sub(r'"[\s\S]*?\)', '', '\n\n'.join([x[1] for x in test_comment])).strip()











#
#
# ###JIEBA TOLKENIZATION###
# #Scrubs strings and outputs a numbered list of the top terms / inputs the df
# def top_terms(df):
#     comment_harvest = []
#     for index, row in df.iterrows():
#         for x in row['comments']:
#             comment_harvest.append(x[1])
#
#     input = '\n'.join(comment_harvest)
#
#     # Scrub the text --> Removes all punctuation and English
#     input = input.replace('…', '').replace(',', '').replace('。', '').replace('，', '').replace('！', '') \
#         .replace('？', '').replace('!', '').replace('“', '').replace('.', '')
#     input = re.sub(r'\s', '', input)
#     input = re.sub(r'[a-zA-Z01-9]', '', input)
#     #Exclusions (prepositions, pronouns, etc., to be removed from results
#     exclusions = ['的', '你', '了', '在', '她', '是', '人', '和', '就是', '不是', '都', '不', '有', '我', '多', '就', '这',
#                   '也', '吧', '对', '要', '会', '一个', '吗', '什么', '很', '让', '应该', '不会', '因为', '没有', '这样',
#                   '更', '他们', '于', '（', '）', '不是', '但', '啥', '把', '才', '啊', '"', ')', '(', '他', ':', '”',
#                   '还', '可以', '为', '这个', '?', '又', '—','呀', '得', '、', '\'', '《', '》', '者'
#                   ]
#     #jieba.add_word('邹至蕙')
#
#     #Tolkenize with Jieba + Counter to count terms in the list
#     output = Counter(jieba.lcut(input))
#     #Eliminate the exclusions
#     for x in list(output):
#         if x in exclusions:
#             del output[x]
#
#     print(output)
#     return output
#
# top_terms(df)



#MISC
#print(Counter(jieba.lcut(text_chunk)))
#print(jieba.analyse.extract_tags(text_chunk, topK=50, withWeight=True, allowPOS=()))


#Add custom words to be segmented
#jieba.add_word('邹至蕙')
#jieba.suggest_freq('...', tune=True)

# seg_list = jieba.cut(text_chunk, cut_all=False)
# print('/'.join(seg_list))