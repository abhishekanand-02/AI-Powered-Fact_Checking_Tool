import requests
import json
# from newsdataapi import NewsDataApiClient
from config import settings
from logger import logging
# from core.utils import save_json_to_root, load_claims_from_json
import urllib.parse
import urllib.request
import os


NEWSDATA_MAX_RESULTS_PER_QUERY = 10
GNEWS_MAX_RESULTS_PER_QUERY = 10
DEFAULT_LANGUAGE = "en"
DEFAULT_COUNTRY_FALLBACK = "in"


def fetch_from_newsdata(query: str, language: str = DEFAULT_LANGUAGE, country_code: str | None = None) -> list[dict]:
    if not settings.NEWSDATA_API_KEY:
        logging.error("NewsData.io API key is not configured.")
        return []

    articles_data = []
    target_country = country_code.lower() if isinstance(country_code, str) and country_code.strip() else DEFAULT_COUNTRY_FALLBACK

    logging.info(f"Querying NewsData.io with q='{query}', lang='{language}', country='{target_country}'")

    encoded_query = urllib.parse.quote(query)
    url = (
        f"https://newsdata.io/api/1/news?"
        f"apikey={settings.NEWSDATA_API_KEY}"
        f"&q={encoded_query}"
        f"&language={language}"
        f"&country={target_country}"
    )

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))

            if data.get("status") == "success":
                results = data.get("results", [])[:NEWSDATA_MAX_RESULTS_PER_QUERY]
                for article in results:
                    articles_data.append({
                        "article_id": article.get("article_id"),
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "source_id_from_api": article.get("source_name")
                    })
                logging.info(f"Fetched {len(articles_data)} articles from NewsData.io")
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

    return articles_data


def fetch_from_gnews_io(query: str, language: str = DEFAULT_LANGUAGE, country_code: str | None = None) -> list[dict]:
    if not settings.GNEWS_API_KEY:
        logging.warning("GNews.io API key is not configured.")
        return []

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
