# Forum Scraper
Scraping tools for 51ca and associated forum, intended to collect textual data for academic analysis. 

CommentFetch51ca class contains various functions for scraping article metadata and corresponding comment threads from 51.ca sites. 

Scraper(keyword, news=False, comments=False, pickled=False) : Main function that takes in a keyword and scrapes data in two stages: 
1) Searching info.51.ca and returning a list of article metadata (headline, author, date, body) and a link to the corresponding forum discussion.
2) Using the above forum link to scrape all comments regarding a given news story. Pickled toggle will save the returned dataframe as a pickle;
note: the comment stage requires a saved pickle to execute. 
