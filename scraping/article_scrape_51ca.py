import re
import time
import logging
import pickle
import url_fetch_51ca as uf
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service


SEARCH_TERM = "Pumpkin"
MAX_PAGES = None
PICKLE_SAVE = True #whether to save or not

logging.basicConfig(
    format="%(asctime)s, %(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=logging.INFO,
)


def url_scraper(input):
    driver.get(input)

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
        article_author = re.search(r"(?<=作者：\s).*(?=\s*)", article_meta.text).group(0)
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
        input,
    ]
    logging.info(
        f"new_entry: {new_entry}"
    )  # level denotes floor for displaying the message
    return new_entry


# Formats dataframe (standardize dates, convert to datetime)
def df_formatter(input):
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

    # Create empty DF
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

    # Fill DF with scrape function
    u = uf.URLFetch51ca(driver)

    for url in u.url_fetch(SEARCH_TERM, max_page_depth=MAX_PAGES):
        df = pd.concat(
            [df, pd.DataFrame([url_scraper(url)], columns=df.columns)],
            ignore_index=True,
        )

    # Format the DF
    df = df_formatter(df)
    
    IF PICKLE_SAVE = True:
        
        # Save to pickle
        with open(f"{SEARCH_TERM.lower()}-51ca.pickle", "wb") as f:
        pickle.dump(df, f)
    else: pass 
