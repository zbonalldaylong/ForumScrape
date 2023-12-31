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
import os
from os.path import exists
from pathlib import Path
import pickle
import pandas as pd
import regex as re
import time
import logging


"""
Class includes all functions for scraping comments from a list of (multi-page) forum threads. 

Core functions:

Scraper(keyword, news=False, comments=False, pickled=False) : Main function that takes in a keyword and scrapes data in two stages: 
1) Searching info.51.ca and returning a list of article metadata (headline, author, date, body) and a link to the corresponding forum discussion.
2) Using the above forum link to scrape all comments regarding a given news story. Pickled toggle will save the returned dataframe as a pickle;
note: the comment stage requires a saved pickle to execute. 

"""


class CommentFetch51ca:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "https://bbs.51.ca/thread"
        self.news_base_url = "https://info.51.ca/search?q="
        self.url = None

        # LOGGING (output to commentscrape.log)
        self.logger = logging.getLogger(__name__)  # creates logger
        self.logger.setLevel(logging.INFO)
        self.file_handler = logging.FileHandler(
            "logs/commentscrape.log", encoding="utf-8", mode="w"
        )
        self.file_format = logging.Formatter(
            "%(asctime)s, %(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
        )
        self.file_handler.setFormatter(self.file_format)
        self.logger.addHandler(self.file_handler)

    # ARTICLE SCRAPING - functions to scrape news articles and comment links from https://info.51.ca; a Chinese-language news site

    # Formats the target url with search term
    def _get_url(self, page_num=None):
        url = f"{self.news_base_url}/{self.search_term}"
        if page_num:
            url = f"{url}&page={page_num}"
        return url

    # Get the URLs for a search result
    def url_fetch(self, keyword, max_page_depth=None):

        # Retrieves the urls from the paginated search results
        def _fetch_urls_from_page(page_num):

            # Checks for multi-image posts, which can impact scrape results
            def __multi_image_checker():
                is_multi_image = False
                try:
                    self.driver.find_element(By.CSS_SELECTOR, ".img-wrap")
                    is_multi_image = True
                except:
                    pass

                return is_multi_image

            def __filter_elements(xpath):
                return list(
                    filter(
                        None,
                        [
                            x.get_attribute("href")
                            for x in self.driver.find_elements(By.XPATH, xpath)
                        ],
                    )
                )

            urls = []
            self.driver.get(self._get_url(page_num=page_num))

            # First objective is to get the urls from the ten search results per-page, with the following variation:
            if (
                __multi_image_checker() == False
            ):  # Multi-picture results not present in search results
                urls = __filter_elements('.//ul[@class="news-list"]/li/*')

            else:
                # Multi-picture results present in search results
                urls = __filter_elements('.//ul[@class="news-list"]/li/*')
                urls += __filter_elements('.//ul[@class="news-list"]/li/h3/*')

            return urls

        self.search_term = keyword

        time.sleep(1)
        self.driver.get(self._get_url())
        result_pages = self.driver.find_element(By.ID, "pagination")
        max_page = (
            max_page_depth
            or int(re.search(r".*?(?=\s*›)", result_pages.text).group(0)) + 1
        )
        # The last page of search results

        for i in range(
            1, max_page
        ):  # Loop to harvest all of the results (based on max page)
            for url in _fetch_urls_from_page(i):
                yield url
            time.sleep(0.25)

    # Scrapes headline, author, date, body from news articles aggregated by url_scrape (based on a search term)
    def _scrape_news_articles(self, input_url):
        driver.get(input_url)

        try:
            article_headline = driver.find_element(By.TAG_NAME, "h1").text
        except:
            article_headline = "None"
        # Meta data (author, date, comments)
        try:
            article_meta = driver.find_element(By.CLASS_NAME, "article-meta")
        except:
            article_meta = "None"
        try:
            article_author = re.search(r"(?<=作者：\s).*(?=\s*)", article_meta.text).group(
                0
            )
        except:
            article_author = "None"
        try:
            article_date = re.search(r"(?<=发布：\s).*", article_meta.text).group(0)
        except:
            article_date = "None"
        try:
            article_body = driver.find_element(By.ID, "arcbody").text
        except:
            article_body = "None"
        try:
            comment_link = driver.find_element(
                By.CSS_SELECTOR, ".view-all-section > div:nth-child(1) > a:nth-child(1)"
            ).get_attribute("href")
        except:
            comment_link = "None"

        new_entry = [
            article_headline,
            article_body,
            article_author,
            article_date,
            comment_link,
            input_url,
        ]
        logging.info(
            f"new_entry: {new_entry}"
        )  # level denotes floor for displaying the message

        return new_entry

    # executes the url / article scraping; takes a keyword and outputs a formatted dataframe to then be used for comment scraping.
    def Scraper(self, keyword, news=False, comments=False, pickled=False):
        def _formatter(input):
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

        # First stage - scraping news articles using a keyword
        if news == True:

            df = pd.DataFrame(
                columns=[
                    "article_headline",
                    "article_body",
                    "article_author",
                    "article_date",
                    "comment_link",
                    "article_link",
                ]
            )

            for url in self.url_fetch(keyword):
                df = pd.concat(
                    [
                        df,
                        pd.DataFrame(
                            [self._scrape_news_articles(url)], columns=df.columns
                        ),
                    ],
                    ignore_index=True,
                )

            driver.quit()
            df = _formatter(df)

            # Pickling
            if pickled == True:
                with open(
                    Path(__file__).parent
                    / f"pickle/{keyword.lower()}-articles-51ca.pickle",
                    "wb",
                ) as f:
                    pickle.dump(df, f)
            else:
                return df
        else:
            pass

        # Scrape comments from a df established by the news scrape
        if comments == True:

            # Check for a pre-existing pickle from news site scrape
            if exists(
                Path(__file__).parent / f"pickle/{keyword.lower()}-articles-51ca.pickle"
            ):
                pass
            else:
                print(
                    "Pickle not found. Run Scraper with news=True before attempting to scrape comments"
                )

            # Load the df from pickled news scrape
            in_df = pd.read_pickle(
                Path(__file__).parent / f"pickle/{keyword.lower()}-articles-51ca.pickle"
            )
            comments_list = []

            for index, row in in_df.iterrows():
                if row["comment_link"] != "None":
                    post_counter = 0
                    for paged_url in self._format_url(row["comment_link"]):
                        self.logger.info(f"COMMENT URL: {paged_url} \n")
                        self.driver.get(paged_url)
                        for i in self._comment_extract("//div[contains(@id,'post')]"):
                            post_counter += 1
                            i["comment_no"] = post_counter if post_counter else 1
                            i["comment_link"] = row["comment_link"]
                            i["article_link"] = row["article_link"]
                            comments_list.append(i)
            else:
                pass

            driver.quit()

            comments_df = pd.DataFrame.from_dict(comments_list)
            comments_df["date"] = pd.to_datetime(comments_df["date"])
            comments_df.set_index(["comment_no", "article_link"], inplace=True)

            # Pickling
            if pickled == True:
                with open(
                    Path(__file__).parent
                    / f"pickle/{keyword.lower()}-comments-51ca.pickle",
                    "wb",
                ) as f:
                    pickle.dump(comments_df, f)
            else:
                return comments_df

    # COMMENT SCRAPING - functions to scrape comments from the Chinese-language forum bbs.51.ca
    # This takes the initial url from the url_fetch.py and yields the sub-pages of comments (15 comments per page)
    def _format_url(self, url):
        max_page = 1
        self.thread_id = re.search(r"(?<=tid=)(.*?)(?=$)", url).group(0).strip()

        self.driver.get(url)
        pgt = self.driver.find_elements(By.ID, "pgt")
        for x in pgt:
            if "/" in x.text:
                max_page = re.search("(?<=/)(.*?)(?=页)", x.text).group(0).strip()
        for p in range(1, int(max_page) + 1):
            yield str(f"{self.base_url}-{self.thread_id}-{p}-1.html")

    # This extracts comments and saves them as entries in a dataframe. Includes a nested function to format the scraped comments.
    def _comment_extract(self, xpath):

        # The formatter takes a dictionary entry for one post as input
        def _comment_formatter(entry):
            entry["comment"] = (
                entry["comment"]
                .replace("<br/>", "")
                .replace("\n", "")
                .strip()
                .replace("</font>", "")
                .replace("<i>", "")
                .replace("</i>", "")
            )
            if ".gif" in entry["comment"]:  # Swap in a note for emoticons
                try:
                    entry["comment"] = re.sub(
                        '<img src="(.*?)alt="">', "*Emoticon*", entry["comment"]
                    )
                except:
                    pass
            if "ignore_js_op" in entry["comment"]:  # Image embed
                try:
                    entry["comment"] = re.sub(
                        "<ignore_js_op>([\s\S]*?)<\/ignore_js_op>", entry["comment"]
                    )
                except:
                    pass
            if "a href" in entry["comment"]:  # links with html formatting
                try:
                    replacement_text = (
                        re.search(r'(?<=blank">)(.*?)(?=</a>)', entry["comment"])
                        .group(0)
                        .strip()
                    )
                    entry["comment"] = re.sub(
                        r"<a href=(.*?)</a>", replacement_text, entry["comment"]
                    )
                except:
                    pass
            if "<font " in entry["comment"]:
                try:
                    entry["comment"] = re.sub(r"<font (.*?)>", "", entry["comment"])
                except:
                    pass
            if "<img alt=" in entry["comment"]:
                try:
                    entry["comment"] = re.sub(
                        r'<img alt=([\s\S]*?)"/>', "", entry["comment"]
                    )
                except:
                    pass
            if "<i class" in entry["comment"]:
                try:
                    entry["comment"] = re.sub(r"<i class(.*?)>", "", entry["comment"])
                except:
                    pass
            if "本帖最后由" in entry["comment"]:
                try:
                    entry["comment"] = re.sub(r"本帖最后由(.*?)编辑", "", entry["comment"])
                except:
                    pass
            return entry

        # Start of main comment harvesting loop
        for x in self.driver.find_elements(By.XPATH, xpath):
            quoter = None

            if re.match(r"post_\d\d\d\d\d\d", x.get_attribute("id")) != None:
                raw_html = x.get_attribute("innerHTML")
                post_id = x.get_attribute("id")
                souped_html = bs(x.get_attribute("innerHTML"), "html.parser")

                # ATYPICAL POSTS: MODERATED POST...  Creates a dummy entry for the df.
                if "该帖被管理员或版主屏蔽" in str(souped_html):
                    entry = {
                        "comment_no": None,
                        "poster": None,
                        "date": None,
                        "comment": "Locked Post",
                        "quoted": None,
                        "likes": None,
                        "dislikes": None,
                    }
                    yield entry
                    self.logger.info(
                        f"\n\nPOST ID: {post_id} \nENTRY: {entry}"
                    )  # \nHTML: {souped_html}\n\n---\n\n')
                    continue
                else:
                    pass

                # ATYPICAL POST: MISSING POST
                # Note: this isn't 100%; trying to isolate and troubleshoot a missing post on https://bbs.51.ca/thread-1182385-5-1.html
                if (
                    "<!-- add supportbtns start -->\n<!-- add supportbtns end -->"
                    in str(souped_html)
                ):
                    entry = {
                        "comment_no": None,
                        "poster": None,
                        "date": None,
                        "comment": "Missing Post",
                        "quoted": None,
                        "likes": None,
                        "dislikes": None,
                    }
                    yield entry
                    self.logger.info(
                        f"\n\nPOST ID: {post_id} \nENTRY: {entry}\nXXX_MISSING POST_XXX"
                    )
                    continue
                else:
                    pass

                # TYPICAL POSTS - 1) Harvest the post metadata
                td_id = "postmessage_" + str(x.get_attribute("id")).split("_")[1]
                em_id = "authorposton" + str(x.get_attribute("id")).split("_")[1]

                full_post = x.find_element(By.ID, td_id).text
                post_author = re.search(
                    r'(?<=color: #\w\w\w">|class="\w\w\w">)(.*?)(?=<\/a>)',
                    x.get_attribute("innerHTML"),
                ).group(
                    0
                )  # works 2023/2014
                post_date = re.search(
                    str("(?<=" + em_id + '">发表于 )(.*?)(?=<\/em>)'), str(souped_html)
                ).group(0)

                # Likes and dislikes
                like_id_regex = (
                    "(?<=review_support_"
                    + (str(x.get_attribute("id")).split("_")[1])
                    + '" class="sz">)(.*?)(?=<\/span>)'
                )
                dislike_id_regex = (
                    "(?<=review_against_"
                    + (str(x.get_attribute("id")).split("_")[1])
                    + '" class="sz">)(.*?)(?=<\/span>)'
                )
                likes = (
                    re.search(like_id_regex, x.get_attribute("innerHTML")).group(0)
                    if len(
                        re.search(like_id_regex, x.get_attribute("innerHTML")).group(0)
                    )
                    > 0
                    else 0
                )
                dislikes = (
                    re.search(dislike_id_regex, x.get_attribute("innerHTML")).group(0)
                    if len(
                        re.search(dislike_id_regex, x.get_attribute("innerHTML")).group(
                            0
                        )
                    )
                    > 0
                    else 0
                )

                # 2) Move on to harvesting posts that have quotes (different formatting involved)
                if "<blockquote>" in str(souped_html):
                    # Check for first post (the blockquote will be news story rather than a previous user post)
                    if "§ 发表于" in str(souped_html):
                        full_post_text = re.search(
                            str("(?<=" + td_id + '">)([\s\S]*?)(?=<\/td><\/tr>)'),
                            str(souped_html),
                        ).group(0)
                        entry = {
                            "comment_no": None,
                            "poster": post_author,
                            "date": post_date,
                            "comment": full_post_text,
                            "quoted": "None" if not quoter else quoter,
                            "likes": likes,
                            "dislikes": dislikes,
                            "article_link": None,
                        }
                        yield _comment_formatter(entry)
                        self.logger.info(
                            f"\n\nPOST ID: {post_id} \nENTRY: {entry}"
                        )  # \nHTML: {souped_html}\n\n---\n\n')
                        continue

                    html_blockquotes = re.search(
                        r"<blockquote>([\s\S]*?)<\/td><\/tr>", str(souped_html)
                    ).group(
                        0
                    )  # works 2023/2014
                    quote_raw = re.search(
                        r"(?<=<blockquote>)([\s\S]*?)(?=<\/blockquote>)",
                        html_blockquotes,
                    ).group(0)
                    quoter = (
                        re.search(
                            r'(?<=\d\d">|^)([^>]+)(?= 发表于)',
                            str(souped_html),
                            re.MULTILINE,
                        )
                        .group(0)
                        .strip()
                        if " 发表于" in html_blockquotes
                        else "None"
                    )  # More efficient; works 2014/2023
                    quote_text = (
                        '"'
                        + re.sub(
                            '<font size="2">([\s\S]*?)<\/a><\/font>', "", quote_raw
                        )
                        .replace("<br>", "")
                        .replace("&nbsp;", "")
                        .replace("<strong>", "")
                        .replace("</strong>", "")
                        .strip()
                        + "(("
                        + quoter
                        + "))"
                        + '"'
                    )  # works 2014/2023
                    post_text = (
                        re.search(
                            r"(?<=<\/blockquote><\/div>|<\/blockquote>)([\s\S]*?)(?=<\/td><\/tr>)",
                            html_blockquotes,
                        )
                        .group(0)
                        .replace("<br>", "")
                        .replace("&nbsp;", "")
                        .replace("<strong>", "")
                        .replace("</strong>", "")
                        .strip()
                    )
                    full_post_text = quote_text + "\n" + post_text

                # 3) Posts without quotes
                else:
                    # print('\n---', x.get_attribute('id'), '---\n')
                    html_noblockquotes = x.get_attribute("innerHTML")
                    fp_regex = str('(?<="' + td_id + '">)([\s\S]*?)(?=<\/td>|<\/tr>)')
                    full_post_text = (
                        re.search(fp_regex, html_noblockquotes)
                        .group(0)
                        .replace("<br>", "")
                        .replace("&nbsp;", "\n")
                        .replace("<strong>", "")
                        .replace("</strong>", "")
                        .strip()
                    )  # works 2014/2023
                    # print(post_author, 'SAYS:\n', full_post_text)
                entry = {
                    "comment_no": None,
                    "poster": post_author,
                    "date": post_date,
                    "comment": full_post_text,
                    "quoted": "None" if not quoter else quoter,
                    "likes": likes,
                    "dislikes": dislikes,
                    "article_link": None,
                }
                self.logger.info(f"\n\nPOST ID: {post_id} \nENTRY:{entry}")
                yield _comment_formatter(entry)


if __name__ == "__main__":
    pd.set_option("mode.chained_assignment", None)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_colwidth", None)

    if os.name == "posix":
        service = Service(Path.home() / "bin/geckodriver")
    else:
        service = Service("C:\geckodriver.exe")
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = webdriver.Firefox(service=service, options=options)


cs = CommentFetch51ca(driver)

cs.Scraper("Pumpkin", pickled=True, comments=True)
