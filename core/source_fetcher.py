import requests
import json
import openai
from config import settings
from logger import logging
import urllib.parse
import urllib.request
import time
from typing import Optional


NEWSDATA_MAX_RESULTS_PER_QUERY = 10
GNEWS_MAX_RESULTS_PER_QUERY = 10
DEFAULT_LANGUAGE = "en"
DEFAULT_COUNTRY_FALLBACK = "in"
DEFAULT_MODEL = "gpt-4o-mini"


def initialize_openai_client():
    try:
        return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
        return None


def fetch_from_newsdata(query: str, language: str = DEFAULT_LANGUAGE, country_code: Optional[str] = None) -> list[dict]:

    if not settings.NEWSDATA_API_KEY:
        logging.error("NewsData.io API key is not configured.")
        return []

    articles = query_newsdata_api(query, language, country_code)
    if articles:
        return articles

    client = initialize_openai_client()

    refined_query_1 = reframe_search_statement(client, query, attempt=1)
    if refined_query_1 and refined_query_1 != query:
        logging.info(f"Retrying with refined query 1: {refined_query_1}")
        articles = query_newsdata_api(refined_query_1, language, country_code)
        if articles:
            return articles

    time.sleep(5) 
    refined_query_2 = reframe_search_statement(client, refined_query_1, attempt=2, previous_refinement=refined_query_1)
    if refined_query_2 and refined_query_2 != refined_query_1 and refined_query_2 != query:
        logging.info(f"Retrying with refined query 2: {refined_query_2}")
        articles = query_newsdata_api(refined_query_2, language, country_code)
    else:
        logging.info("Skipping second refinement: query did not change.")
    return articles


def query_newsdata_api(query: str, language: str, country_code: Optional[str]) -> list[dict]:
    time.sleep(6)
    articles = []
    target_country = country_code.lower() if isinstance(country_code, str) and country_code.strip() else DEFAULT_COUNTRY_FALLBACK
    encoded_query = urllib.parse.quote(query)

    url = (
        f"https://newsdata.io/api/1/news?"
        f"apikey={settings.NEWSDATA_API_KEY}"
        f"&q={encoded_query}"
        f"&language={language}"
        f"&country={target_country}"
    )

    logging.info(f"Querying NewsData.io with q='{query}', lang='{language}', country='{target_country}'")

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))

            if data.get("status") == "success":
                results = data.get("results", [])[:NEWSDATA_MAX_RESULTS_PER_QUERY]
                for article in results:
                    articles.append({
                        "article_id": article.get("article_id"),
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "source_id_from_api": article.get("source_name")
                    })

                logging.info(f"Fetched {len(articles)} articles from NewsData.io")
            else:
                logging.error(f"NewsData.io API error: {data.get('message', 'Unknown error')}")
                logging.debug(f"Full response: {data}")
    except urllib.error.HTTPError as e:
        logging.error(f"HTTPError from NewsData.io: {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        logging.error(f"URLError from NewsData.io: {e.reason}")
    except Exception as e:
        logging.error(f"Unexpected exception from NewsData.io: {e}")
        logging.debug("Exception details:", exc_info=True)

    return articles

def fetch_from_gnews_io(query: str, language: str = DEFAULT_LANGUAGE, country_code: Optional[str] = None) -> list[dict]:
    if not settings.GNEWS_API_KEY:
        logging.warning("GNews.io API key is not configured.")
        return []

    articles_data = query_gnews_api(query, language, country_code)
    if articles_data :
        return articles_data

    client = initialize_openai_client()

    refined_query_1 = reframe_search_statement(client, query, attempt=1)
    if refined_query_1 and refined_query_1 != query:
        logging.info(f"Retrying GNews with refined query 1: {refined_query_1}")
        articles_data = query_gnews_api(refined_query_1, language, country_code)
        if articles_data:
            return articles_data

    refined_query_2 = reframe_search_statement(client, refined_query_1, attempt=2, previous_refinement=refined_query_1)
    if refined_query_2 and refined_query_2 != refined_query_1 and refined_query_2 != query:
        logging.info(f"Retrying GNews with refined query 2: {refined_query_2}")
        articles_data = query_gnews_api(refined_query_2, language, country_code)
    else:
        logging.info("Skipping second GNews refinement: query did not change.")

    return articles_data


def query_gnews_api(query: str, language: str, country_code: Optional[str]) -> list[dict]:
    time.sleep(6)  

    gnews_api_endpoint = "https://gnews.io/api/v4/search"
    target_country = country_code.lower() if isinstance(country_code, str) and country_code.strip() else DEFAULT_COUNTRY_FALLBACK

    params = {
        "q": query,
        "lang": language,
        "country": target_country,
        "max": GNEWS_MAX_RESULTS_PER_QUERY,
        "token": settings.GNEWS_API_KEY,
        "sortby": "relevance"
    }

    articles_data = []
    log_params = {k: v for k, v in params.items() if k != 'token'}
    logging.info(f"Querying GNews.io with params: {log_params}")

    try:
        response = requests.get(gnews_api_endpoint, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if isinstance(data.get("articles"), list):
            for article in data["articles"]:
                source_info = article.get("source", {})
                name = source_info.get("name", "Unknown Source")
                articles_data.append({
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "content": article.get("content"),
                    "name": name
                })
            logging.info(f"Fetched {len(articles_data)} articles from GNews.io")
        else:
            logging.error(f"GNews.io response missing 'articles'. Response: {data}")

    except requests.exceptions.Timeout:
        logging.error(f"Timeout fetching from GNews.io for query '{query}'.")
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error from GNews.io: {e.response.status_code} - {e.response.text[:500]}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request exception from GNews.io: {e}")
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON response from GNews.io: {response.text[:200]}")
    except Exception as e:
        logging.error(f"Unexpected error from GNews.io: {e}")
        logging.debug("Exception details:", exc_info=True)

    return articles_data



def reframe_search_statement(client: openai.OpenAI, original_query: str, attempt: int = 1, previous_refinement: Optional[str] = None) -> str:
    
    # print("\n\n\n\n\n\n I am triggered from reframe_search_statement, Original query is:", original_query)

    if attempt == 1:
        system_prompt = """
            You are an expert at optimizing search queries for news APIs and search engines.

            Your task is to extract only the most essential keyword or phrase from a given natural language query.

            Remove:
            - Any filler words, grammatical structure, or phrases that do not aid in finding relevant news

            The result must be:
            - A concise, meaningful keyword suitable for news article search engine
            - Faithful to the core idea of the original query

            Respond only with the improved query string. Do not include explanations or formatting.
        """
        user_prompt = original_query

    else:
        system_prompt = f"""
            You are an expert at refining search queries for news APIs.

            Your goal is to reduce a natural language query to a **short, meaningful** phrase made up of 1–3 keywords or named entities (like people, organizations, events, places).

            You already tried this refinement: "{previous_refinement}". 
            Do not repeat or closely resemble that version, and do not return the same structure or phrase again.

            Your result should:
            - Be different from both the original query and previous refinement
            - Focus on key search terms
            - Avoid unnecessary phrasing or similarity

            Return only the new refined query string. No explanations.
        """
        user_prompt = original_query

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()}
            ],
            temperature=0.9,
            max_tokens=30
        )
        refined_query = response.choices[0].message.content.strip().strip('"')
        print("\n\n\n\n haha:", refined_query)
        return refined_query
    except Exception as e:
        logging.error(f"Failed to reframe query using LLM: {e}")
        return original_query








# import requests
# import json
# import openai
# from config import settings
# from logger import logging
# import urllib.parse
# import urllib.request
# import os
# from typing import Optional

# NEWSDATA_MAX_RESULTS_PER_QUERY = 10
# GNEWS_MAX_RESULTS_PER_QUERY = 10
# DEFAULT_LANGUAGE = "en"
# DEFAULT_COUNTRY_FALLBACK = "in"
# DEFAULT_MODEL = "gpt-4o-mini"

# def initialize_openai_client():
#     try:
#         return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
#     except Exception as e:
#         logging.error(f"Failed to initialize OpenAI client: {e}")
#         return None


# def fetch_from_newsdata(
#     query: str,
#     language: str = DEFAULT_LANGUAGE,
#     country_code: Optional[str] = None,
#     attempt_refinement: bool = True
# ) -> list[dict]:
#     if not settings.NEWSDATA_API_KEY:
#         logging.error("NewsData.io API key is not configured.")
#         return []

#     articles_data = []
#     target_country = country_code.lower() if isinstance(country_code, str) and country_code.strip() else DEFAULT_COUNTRY_FALLBACK

#     logging.info(f"Querying NewsData.io with q='{query}', lang='{language}', country='{target_country}'")

#     encoded_query = urllib.parse.quote(query)
#     url = (
#         f"https://newsdata.io/api/1/news?"
#         f"apikey={settings.NEWSDATA_API_KEY}"
#         f"&q={encoded_query}"
#         f"&language={language}"
#         f"&country={target_country}"
#     )

#     try:
#         with urllib.request.urlopen(url) as response:
#             data = json.loads(response.read().decode("utf-8"))

#             if data.get("status") == "success":
#                 results = data.get("results", [])[:NEWSDATA_MAX_RESULTS_PER_QUERY]
#                 for article in results:
#                     articles_data.append({
#                         "article_id": article.get("article_id"),
#                         "title": article.get("title"),
#                         "description": article.get("description"),
#                         "source_id_from_api": article.get("source_name")
#                     })

#                 logging.info(f"Fetched {len(articles_data)} articles from NewsData.io")

#                 if not articles_data and attempt_refinement:
#                     logging.warning("No articles found. Attempting to refine the query using OpenAI.")
#                     client = initialize_openai_client()
#                     if client:
#                         refined_query = reframe_search_statement(client, query)
#                         if refined_query and refined_query != query:
#                             logging.info(f"Retrying with refined query: {refined_query}")
#                             return fetch_from_newsdata(
#                                 query=refined_query,
#                                 language=language,
#                                 # country_code=None,
#                                 attempt_refinement=False
#                             )
#             else:
#                 logging.error(f"NewsData.io API error: {data.get('message', 'Unknown error')}")
#                 logging.debug(f"Full response: {data}")

#     except urllib.error.HTTPError as e:
#         logging.error(f"HTTPError from NewsData.io: {e.code} - {e.reason}")
#     except urllib.error.URLError as e:
#         logging.error(f"URLError from NewsData.io: {e.reason}")
#     except Exception as e:
#         logging.error(f"Unexpected exception from NewsData.io: {e}")
#         logging.debug("Exception details:", exc_info=True)

#     return articles_data



# def fetch_from_gnews_io(query: str, language: str = DEFAULT_LANGUAGE, country_code: Optional[str] = None) -> list[dict]:
#     if not settings.GNEWS_API_KEY:
#         logging.warning("GNews.io API key is not configured.")
#         return []

#     gnews_api_endpoint = "https://gnews.io/api/v4/search"
#     target_country = country_code.lower() if isinstance(country_code, str) and country_code.strip() else DEFAULT_COUNTRY_FALLBACK

#     params = {
#         "q": query,
#         "lang": language,
#         "country": target_country,
#         "max": GNEWS_MAX_RESULTS_PER_QUERY,
#         "token": settings.GNEWS_API_KEY,
#         "sortby": "relevance"
#     }

#     articles_data = []
#     log_params = {k: v for k, v in params.items() if k != 'token'}
#     logging.info(f"Querying GNews.io with params: {log_params}")

#     try:
#         response = requests.get(gnews_api_endpoint, params=params, timeout=10)
#         response.raise_for_status()
#         data = response.json()

#         if isinstance(data.get("articles"), list):
#             for article in data["articles"]:
#                 source_info = article.get("source", {})
#                 name = source_info.get("name", "Unknown Source")
#                 articles_data.append({
#                     "title": article.get("title"),
#                     "description": article.get("description"),
#                     "content": article.get("content"),
#                     "name": name
#                 })
#             logging.info(f"Fetched {len(articles_data)} articles from GNews.io")
#         else:
#             logging.error(f"GNews.io response missing 'articles'. Response: {data}")

#     except requests.exceptions.Timeout:
#         logging.error(f"Timeout fetching from GNews.io for query '{query}'.")
#     except requests.exceptions.HTTPError as e:
#         logging.error(f"HTTP error from GNews.io: {e.response.status_code} - {e.response.text[:500]}")
#     except requests.exceptions.RequestException as e:
#         logging.error(f"Request exception from GNews.io: {e}")
#     except json.JSONDecodeError:
#         logging.error(f"Invalid JSON response from GNews.io: {response.text[:200]}")
#     except Exception as e:
#         logging.error(f"Unexpected error from GNews.io: {e}")
#         logging.debug("Exception details:", exc_info=True)

#     return articles_data


# def reframe_search_statement(client: openai.OpenAI, original_query: str) -> str:
#     print("\n\n\n\n\n\n I am triggered from reframe_search_statement, Original query is: " , original_query)
#     system_prompt = """
# You are an expert at optimizing search queries for news APIs and search engines.

# Your task is to extract only the most essential keyword or phrase from a given natural language query.

# Remove:
# - Irrelevant details, functional words, and general context like job titles or known facts
# - Any filler words, grammatical structure, or phrases that do not aid in finding relevant news

# The result must be:
# - A concise, meaningful keyword suitable for news article search
# - Faithful to the core idea of the original query

# Respond only with the improved query string. Do not include explanations or formatting.
# """



#     try:
#         response = client.chat.completions.create(
#             model=DEFAULT_MODEL,
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": original_query}
#             ],
#             temperature=0.7,
#             max_tokens=30
#         )
#         print("\n\n\n\n haha: ",response.choices[0].message.content.strip().strip('"'))
#         return response.choices[0].message.content.strip().strip('"')
#     except Exception as e:
#         logging.error(f"Failed to reframe query using LLM: {e}")
#         return original_query

# Working code -----------------

# import requests
# import json
# import openai
# # from newsdataapi import NewsDataApiClient
# from config import settings
# from logger import logging
# # from core.utils import save_json_to_root, load_claims_from_json
# import urllib.parse
# import urllib.request
# import os


# NEWSDATA_MAX_RESULTS_PER_QUERY = 10
# GNEWS_MAX_RESULTS_PER_QUERY = 10
# DEFAULT_LANGUAGE = "en"
# DEFAULT_COUNTRY_FALLBACK = "in"

# DEFAULT_MODEL = "gpt-4o-mini"

# def initialize_openai_client():
#     try:
#         return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
#     except Exception as e:
#         logging.error(f"Failed to initialize OpenAI client: {e}")
#         return None



# def fetch_from_newsdata(query: str, language: str = DEFAULT_LANGUAGE, country_code: str | None = None) -> list[dict]:
#     if not settings.NEWSDATA_API_KEY:
#         logging.error("NewsData.io API key is not configured.")
#         return []

#     articles_data = []
#     target_country = country_code.lower() if isinstance(country_code, str) and country_code.strip() else DEFAULT_COUNTRY_FALLBACK

#     logging.info(f"Querying NewsData.io with q='{query}', lang='{language}', country='{target_country}'")

#     encoded_query = urllib.parse.quote(query)
#     url = (
#         f"https://newsdata.io/api/1/news?"
#         f"apikey={settings.NEWSDATA_API_KEY}"
#         f"&q={encoded_query}"
#         f"&language={language}"
#         f"&country={target_country}"
#     )

#     try:
#         with urllib.request.urlopen(url) as response:
#             data = json.loads(response.read().decode("utf-8"))

#             if data.get("status") == "success":
#                 results = data.get("results", [])[:NEWSDATA_MAX_RESULTS_PER_QUERY]
#                 for article in results:
#                     articles_data.append({
#                         "article_id": article.get("article_id"),
#                         "title": article.get("title"),
#                         "description": article.get("description"),
#                         "source_id_from_api": article.get("source_name")
#                     })

#                 logging.info(f"Fetched {len(articles_data)} articles from NewsData.io")

#                 if len(articles_data) == 0:
#                     print("\n No articles found for the given query.")

#             else:
#                 logging.error(f"NewsData.io API error: {data.get('message', 'Unknown error')}")
#                 logging.debug(f"Full response: {data}")

#     except urllib.error.HTTPError as e:
#         logging.error(f"HTTPError from NewsData.io: {e.code} - {e.reason}")
#     except urllib.error.URLError as e:
#         logging.error(f"URLError from NewsData.io: {e.reason}")
#     except Exception as e:
#         logging.error(f"Unexpected exception from NewsData.io: {e}")
#         logging.debug("Exception details:", exc_info=True)

#     return articles_data


# def fetch_from_gnews_io(query: str, language: str = DEFAULT_LANGUAGE, country_code: str | None = None) -> list[dict]:
#     if not settings.GNEWS_API_KEY:
#         logging.warning("GNews.io API key is not configured.")
#         return []

#     gnews_api_endpoint = "https://gnews.io/api/v4/search"
#     target_country = country_code.lower() if isinstance(country_code, str) and country_code.strip() else DEFAULT_COUNTRY_FALLBACK

#     params = {
#         "q": query,
#         "lang": language,
#         "country": target_country,
#         "max": GNEWS_MAX_RESULTS_PER_QUERY,
#         "token": settings.GNEWS_API_KEY,
#         "sortby": "relevance"
#     }

#     articles_data = []
#     log_params = {k: v for k, v in params.items() if k != 'token'}
#     logging.info(f"Querying GNews.io with params: {log_params}")

#     try:
#         response = requests.get(gnews_api_endpoint, params=params, timeout=10)
#         response.raise_for_status()
#         data = response.json()

#         if isinstance(data.get("articles"), list):
#             for article in data["articles"]:
#                 source_info = article.get("source", {})
#                 name = source_info.get("name", "Unknown Source")
#                 articles_data.append({
#                     "title": article.get("title"),
#                     "description": article.get("description"),
#                     "content": article.get("content"),
#                     "name": name
#                 })
#             logging.info(f"Fetched {len(articles_data)} articles from GNews.io")
#         else:
#             logging.error(f"GNews.io response missing 'articles'. Response: {data}")

#     except requests.exceptions.Timeout:
#         logging.error(f"Timeout fetching from GNews.io for query '{query}'.")
#     except requests.exceptions.HTTPError as e:
#         logging.error(f"HTTP error from GNews.io: {e.response.status_code} - {e.response.text[:500]}")
#     except requests.exceptions.RequestException as e:
#         logging.error(f"Request exception from GNews.io: {e}")
#     except json.JSONDecodeError:
#         logging.error(f"Invalid JSON response from GNews.io: {response.text[:200]}")
#     except Exception as e:
#         logging.error(f"Unexpected error from GNews.io: {e}")
#         logging.debug("Exception details:", exc_info=True)

#     return articles_data
#     # pass



# def reframe_search_statement(client:openai.OpenAI, original_query: str) -> str:
#     system_prompt = """

#          "You are an expert at optimizing search queries for news APIs. "
#          "Given a complex or verbose query, your job is to simplify it to keywords "        "or short phrases that are more likely to match news articles, without changing the meaning.\n\n"
#         "Respond only with the improved query string and nothing else."
#     """
#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-4",
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": f"Original query: {query}"}
#             ],
#             temperature=0.7,
#             max_tokens=30
#         )
#         return response.choices[0].message.content.strip().strip('"')
#     except Exception as e:
#         logging.error(f"Failed to reframe query using LLM: {e}")
#         return original_query 


# def refine_search_statement(query: str) -> str:
#     """
#     Use an LLM to simplify and refine the search query to increase the chance
#     of matching relevant news articles from NewsData.io.
#     """
#     system_prompt = (
#         "You are an expert at optimizing search queries for news APIs. "
#         "Given a complex or verbose query, your job is to simplify it to keywords "
#         "or short phrases that are more likely to match news articles, without changing the meaning.\n\n"
#         "Respond only with the improved query string and nothing else."
#     )

#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-4",
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": f"Original query: {query}"}
#             ],
#             temperature=0.7,
#             max_tokens=30
#         )
#         refined_query = response.choices[0].message['content'].strip()
#         logging.info(f"Refined query: '{refined_query}' from original: '{query}'")
#         return refined_query

#     except Exception as e:
#         logging.error(f"Failed to refine query using LLM: {e}")
#         return query 



# USE THESE FUNCTIONS TO FETCH DATA FROM BOTH SOURCES- LATER USE 

# def get_articles_from_both_sources(query: str, country_code: str | None = None) -> dict[str, list[dict]]:
#     if not query or not query.strip():
#         logging.warning("Empty or whitespace-only query for fetching sources. Returning empty results.")
#         return {}

#     all_results = {}
#     country_log_msg = country_code if isinstance(country_code, str) and country_code.strip() else f"None provided (will use fallback: {DEFAULT_COUNTRY_FALLBACK})"
#     logging.info(f"Fetching all sources for query: '{query}', country_code: '{country_log_msg}'")

#     newsdata_articles = fetch_from_newsdata(query, country_code=country_code)
#     if newsdata_articles:
#         all_results["NewsData.io"] = newsdata_articles

#     gnews_articles = fetch_from_gnews_io(query, country_code=country_code)
#     if gnews_articles:
#         all_results["GNews.io"] = gnews_articles

#     total_fetched = sum(len(v) for v in all_results.values() if isinstance(v, list))
#     sources_responded_count = len(all_results)
#     logging.info(f"Total articles fetched for query '{query}': {total_fetched} from {sources_responded_count} source(s).")
#     print(all_results)
#     return all_results

# if __name__ == '__main__':
#     logging.info("START: Custom Extraction and Saving")

#     sample_query = "Pahalgam mass shooting April"
#     sample_country = "in"

#     fetched_data = get_articles_from_both_sources(sample_query, country_code=sample_country)

#     newsdata_list = []
#     gnews_list = []

#     for source, articles in fetched_data.items():
#         if source == "NewsData.io":
#             for article in articles:
#                 newsdata_list.append({
#                     "article_id": article.get("article_id"),
#                     "title": article.get("title"),
#                     "description": article.get("description"),
#                     "source_id_from_api": article.get("source_id_from_api")
#                 })
#         elif source == "GNews.io":
#             for article in articles:
#                 gnews_list.append({
#                     "title": article.get("title"),
#                     "description": article.get("description"),
#                     "content": article.get("content"),
#                     "name": article.get("name", "Unknown Source")
#                 })

#     structured_output = {
#         "NewsData.io": newsdata_list,
#         "GNews.io": gnews_list
#     }

#     try:
#         save_json_to_root(structured_output, "filtered_articles.json")
#         logging.info("Saved filtered article data to 'filtered_articles.json'.")
#     except Exception as e:
#         logging.error(f"Failed to save articles: {e}")

#     logging.info("END: Custom Extraction and Saving")



# import requests
# import json
# import urllib.parse
# import urllib.request
# import os

# from config import settings
# from logger import logging
# from core.utils import load_claims_from_json

# NEWSDATA_MAX_RESULTS_PER_QUERY = 10
# GNEWS_MAX_RESULTS_PER_QUERY = 10
# DEFAULT_LANGUAGE = "en"
# DEFAULT_COUNTRY_FALLBACK = "in"

# def fetch_from_newsdata(query: str, language: str = DEFAULT_LANGUAGE, country_code: str | None = None) -> list[dict]:
#     if not settings.NEWSDATA_API_KEY:
#         logging.error("NewsData.io API key is not configured.")
#         return []

#     articles_data = []
#     target_country = country_code.lower() if isinstance(country_code, str) and country_code.strip() else DEFAULT_COUNTRY_FALLBACK
#     logging.info(f"Querying NewsData.io with q='{query}', lang='{language}', country='{target_country}'")

#     encoded_query = urllib.parse.quote(query)
#     print("\n encoded_query",encoded_query)
#     url = (
#         f"https://newsdata.io/api/1/news?"
#         f"apikey={settings.NEWSDATA_API_KEY}"
#         f"&q={encoded_query}"
#         f"&language={language}"
#         f"&country={target_country}"
#     )

#     try:
#         with urllib.request.urlopen(url) as response:
#             data = json.loads(response.read().decode("utf-8"))

#             if data.get("status") == "success":
#                 results = data.get("results", [])[:NEWSDATA_MAX_RESULTS_PER_QUERY]
#                 for article in results:
#                     articles_data.append({
#                         "article_id": article.get("article_id"),
#                         "title": article.get("title"),
#                         "description": article.get("description"),
#                         "source_id_from_api": article.get("source_name")
#                     })
#                 logging.info(f"Fetched {len(articles_data)} articles from NewsData.io")
#             else:
#                 logging.error(f"NewsData.io API error: {data.get('message', 'Unknown error')}")
#                 logging.debug(f"Full response: {data}")

#     except urllib.error.HTTPError as e:
#         logging.error(f"HTTPError from NewsData.io: {e.code} - {e.reason}")
#     except urllib.error.URLError as e:
#         logging.error(f"URLError from NewsData.io: {e.reason}")
#     except Exception as e:
#         logging.error(f"Unexpected exception from NewsData.io: {e}")
#         logging.debug("Exception details:", exc_info=True)

#     return articles_data


# def fetch_from_gnews_io(query: str, language: str = DEFAULT_LANGUAGE, country_code: str | None = None) -> list[dict]:
#     if not settings.GNEWS_API_KEY:
#         logging.warning("GNews.io API key is not configured.")
#         return []

#     gnews_api_endpoint = "https://gnews.io/api/v4/search"
#     target_country = country_code.lower() if isinstance(country_code, str) and country_code.strip() else DEFAULT_COUNTRY_FALLBACK

#     params = {
#         "q": query,
#         "lang": language,
#         "country": target_country,
#         "max": GNEWS_MAX_RESULTS_PER_QUERY,
#         "token": settings.GNEWS_API_KEY,
#         "sortby": "relevance"
#     }

#     articles_data = []
#     log_params = {k: v for k, v in params.items() if k != 'token'}
#     logging.info(f"Querying GNews.io with params: {log_params}")

#     try:
#         response = requests.get(gnews_api_endpoint, params=params, timeout=10)
#         response.raise_for_status()
#         data = response.json()

#         if isinstance(data.get("articles"), list):
#             for article in data["articles"]:
#                 source_info = article.get("source", {})
#                 name = source_info.get("name", "Unknown Source")
#                 articles_data.append({
#                     "title": article.get("title"),
#                     "description": article.get("description"),
#                     "content": article.get("content"),
#                     "source_id_from_api": name
#                 })
#             logging.info(f"Fetched {len(articles_data)} articles from GNews.io")
#         else:
#             logging.error(f"GNews.io response missing 'articles'. Response: {data}")

#     except requests.exceptions.Timeout:
#         logging.error(f"Timeout fetching from GNews.io for query '{query}'.")
#     except requests.exceptions.HTTPError as e:
#         logging.error(f"HTTP error from GNews.io: {e.response.status_code} - {e.response.text[:500]}")
#     except requests.exceptions.RequestException as e:
#         logging.error(f"Request exception from GNews.io: {e}")
#     except json.JSONDecodeError:
#         logging.error(f"Invalid JSON response from GNews.io: {response.text[:200]}")
#     except Exception as e:
#         logging.error(f"Unexpected error from GNews.io: {e}")
#         logging.debug("Exception details:", exc_info=True)

#     return articles_data

# def main():
#     logging.info("START: Custom Extraction and Saving")

#     try:
#         claims = load_claims_from_json("claims_from_articles.json")
#     except Exception as e:
#         logging.error(f"Failed to load claims file: {e}")
#         return

#     filtered_articles_by_query = {}

#     for incident in claims.get("incidents", []):
#         query = incident.get("search_statement")
#         country_code = "in"

#         if not query:
#             continue

#         # Fetch from NewsData.io
#         newsdata_articles = fetch_from_newsdata(query, country_code=country_code)

#         # Fetch from GNews.io
#         gnews_articles = fetch_from_gnews_io(query, country_code=country_code)

#         # Store separately by API source
#         filtered_articles_by_query[query] = {
#             "newsdata": newsdata_articles,
#             "gnews": gnews_articles
#         }

#         logging.info(f"Saved {len(newsdata_articles)} from NewsData.io and {len(gnews_articles)} from GNews.io for query '{query}'")

#     # Save output
#     try:
#         project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#         output_path = os.path.join(project_root, "filtered_articles.json")
#         with open(output_path, "w", encoding="utf-8") as f:
#             json.dump(filtered_articles_by_query, f, ensure_ascii=False, indent=2)
#         logging.info(f"Saved filtered article data to '{output_path}'")
#     except Exception as e:
#         logging.error(f"Failed to save filtered_articles.json: {e}")

#     logging.info("END: Custom Extraction and Saving")



# def main():
#     logging.info("START: Custom Extraction and Saving")

#     try:
#         claims = load_claims_from_json("claims_from_articles.json")
#     except Exception as e:
#         logging.error(f"Failed to load claims file: {e}")
#         return

#     filtered_articles_by_query = {}

#     for incident in claims.get("incidents", []):
#         query = incident.get("search_statement")
#         country_code = "in"

#         if not query:
#             continue

#         all_articles = []

#         # Fetch from NewsData.io
#         newsdata_articles = fetch_from_newsdata(query, country_code=country_code)
#         all_articles.extend(newsdata_articles)

#         # Fetch from GNews.io
#         gnews_articles = fetch_from_gnews_io(query, country_code=country_code)
#         all_articles.extend(gnews_articles)

#         filtered_articles_by_query[query] = all_articles
#         logging.info(f"Saved {len(all_articles)} articles for query '{query}'")

#     # Save output
#     try:
#         project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#         output_path = os.path.join(project_root, "filtered_articles.json")
#         with open(output_path, "w", encoding="utf-8") as f:
#             json.dump(filtered_articles_by_query, f, ensure_ascii=False, indent=2)
#         logging.info(f"Saved filtered article data to '{output_path}'")
#     except Exception as e:
#         logging.error(f"Failed to save filtered_articles.json: {e}")

#     logging.info("END: Custom Extraction and Saving")


# if __name__ == "__main__":
#     main()
