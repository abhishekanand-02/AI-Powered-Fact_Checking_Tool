import json
import time
from typing import Optional, Dict, Any
import openai
import streamlit as st
from logger import logging
from config import settings
from core.claim_extractor import initialize_openai_client as init_llm_for_claims_extraction, extract_incidents_from_article
from core.source_fetcher import fetch_from_newsdata, fetch_from_gnews_io

DEFAULT_MODEL = "gpt-4o-mini"

def initialize_openai_client():
    try:
        return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
        return None


def run_fact_checking_pipeline(article_text: str) -> Optional[Dict[str, Any]]:
    logging.info("--- Running Streamlit Fact-Checking Pipeline ---")
    results = {}

    st_status_1 = st.status("Stage 1: Extracting claims from article...", expanded=True)
    try:
        llm_client = init_llm_for_claims_extraction()
        if not llm_client:
            st_status_1.update(label="Stage 1 Failed: LLM client init error", state="error")
            return None

        incidents = extract_incidents_from_article(article_text, llm_client)
        if not incidents:
            st_status_1.update(label="Stage 1 Failed: No incidents extracted", state="error")
            return None

        claims_output = {"incidents": incidents}
        results["incidents"] = incidents

        with open("claims_from_articles.json", "w", encoding="utf-8") as f:
            json.dump(claims_output, f, ensure_ascii=False, indent=2)

        st_status_1.update(label="Stage 1: Claims extracted!", state="complete")
    except Exception as e:
        st_status_1.update(label=f"Stage 1 Error: {e}", state="error")
        return None
    time.sleep(0.2)

    st_status_2 = st.status("Stage 2: Fetching articles from external sources...", expanded=True)
    try:
        all_articles = []
        for incident in incidents:
            query = incident.get("search_statement")
            if not query:
                continue
            articles = fetch_from_newsdata(query) + fetch_from_gnews_io(query)
            all_articles.extend(articles)

        results["articles"] = all_articles

        with open("filtered_articles.json", "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)

        st_status_2.update(label="Stage 2: Articles fetched!", state="complete")
    except Exception as e:
        st_status_2.update(label=f"Stage 2 Error: {e}", state="error")
        return None
    time.sleep(0.2)

    st_status_3 = st.status("Stage 3: Verifying facts with LLM...", expanded=True)
    try:
        llm_client_verify = initialize_openai_client()
        all_verifications = []

        flat_articles = []
        for article in all_articles:
            title = article.get("title", "")
            description = article.get("description", "")
            source = article.get("source_id_from_api") or article.get("name", "Unknown")
            flat_articles.append(f"Title: {title}\nDescription: {description}\nSource: {source}")

        article_texts = "\n\n".join(flat_articles)

        for incident in incidents:
            search_query = incident.get("search_statement")
            for fact in incident.get("facts", []):
                fact_text = fact.get("statement")
                verdict = call_gpt_for_fact_verification(llm_client_verify, fact_text, article_texts)
                
                all_verifications.append({
                    "fact": fact_text,
                    "related_search": search_query,
                    "verdict": verdict
                })

        results["verifications"] = all_verifications

        with open("fact_verification_results.json", "w", encoding="utf-8") as f:
            json.dump(all_verifications, f, ensure_ascii=False, indent=2)

        st_status_3.update(label="Stage 3: Verification complete!", state="complete")
        return results
    except Exception as e:
        st_status_3.update(label=f"Stage 3 Error: {e}", state="error")
        return None



def call_gpt_for_fact_verification(client, fact_text, all_articles_text):
    prompt = f"""
        You are a fact verification assistant.

        Fact to verify:
        "{fact_text}"

        Below are the contents of multiple news articles. Each article includes its title, description, and the source name.

        Articles:
        {all_articles_text}

        Based on the articles, determine if the fact is:
        - **Proved** (if the fact's core claim is supported clearly by any article),
        - **Refuted** (if any article directly contradicts the fact),
        - **Unclear** (if articles do not give enough information).

        Your response should include:
        1. **Short Reasoning** (2-3 lines)
        2. **Final Verdict**: Proved / Refuted / Unclear
        3. **Supporting Source(s)**: Name the news source(s) you used to justify the verdict, if any. If verdict is Unclear, write source as  "None".

        Respond in this exact format:
        Reasoning: ...
        \nVerdict: ...
        \nSources: ...
        """
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI API call failed: {e}")
        return "Error: Unable to get response"
















# import json
# import os
# import openai
# from config import settings
# from logger import logging
# from core.claim_extractor import initialize_openai_client  # Assuming the function is defined there

# DEFAULT_MODEL = "gpt-4o-mini"

# def call_gpt_4o_for_verification(client, prompt):
#     try:
#         response = client.chat.completions.create(
#             model=DEFAULT_MODEL,
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.2
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         logging.error(f"OpenAI API call failed: {e}")
#         return "Error: Unable to get response"

# def main():
#     try:
#         with open("claims_from_articles.json", "r", encoding="utf-8") as f:
#             claims_data = json.load(f)

#         with open("filtered_articles.json", "r", encoding="utf-8") as f:
#             articles_data = json.load(f)

#     except Exception as e:
#         logging.error(f"Error reading input files: {e}")
#         return

#     client = initialize_openai_client()
#     if client is None:
#         return

#     results = []

#     for incident in claims_data.get("incidents", []):
#         query = incident.get("search_statement")
#         facts = incident.get("facts", [])
#         articles = articles_data.get(query, [])

#         if not articles:
#             logging.warning(f"No articles found for query: {query}")
#             continue

#         for article in articles:
#             article_title = article.get("title", "")
#             article_description = article.get("description", "")
#             article_text = f"Title: {article_title}\nDescription: {article_description or 'N/A'}"

#             for fact in facts:
#                 fact_text = fact.get("statement", "")
#                 print("\n\n fact_text",fact_text)
#                 prompt = f"""
# You are a fact verification assistant.   

# Fact: "{fact_text}"

# Article:
# {article_text}

# Based on the article content, rate the fact as one of:
# - Supported
# - Not Supported
# - Unclear

# Explain your reasoning briefly, then give your final rating.
# """

#                 rating = call_gpt_4o_for_verification(client, prompt)

#                 results.append({
#                     "search_statement": query,
#                     "fact": fact_text,
#                     "article_title": article_title,
#                     "article_id": article.get("article_id"),
#                     "rating_result": rating
#                 })
#                 logging.info(f"Verified fact: '{fact_text[:60]}...' with article: '{article_title[:60]}...'")

#     # Save results to project root
#     project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     output_path = os.path.join(project_root, "fact_verification_results.json")

#     try:
#         with open(output_path, "w", encoding="utf-8") as f:
#             json.dump(results, f, indent=2, ensure_ascii=False)
#         logging.info(f"Saved fact verification results to: {output_path}")
#     except Exception as e:
#         logging.error(f"Failed to save fact verification results: {e}")

# if __name__ == "__main__":
#     main()


# import json
# import os
# import openai
# from config import settings
# from logger import logging

# DEFAULT_MODEL = "gpt-4o-mini"

# def initialize_openai_client():
#     try:
#         return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
#     except Exception as e:
#         logging.error(f"Failed to initialize OpenAI client: {e}")
#         return None

# def call_gpt_for_fact_verification(client, fact_text, all_articles_text):
#     prompt = f"""
# You are a fact verification assistant.

# Fact to verify:
# "{fact_text}"

# Below are the contents of multiple news articles. Titles and descriptions are included.

# Articles:
# {all_articles_text}

# Based on the articles, determine if the fact is:
# - Proved (if the fact's core claim is supported clearly by any article),
# - Refuted (if any article directly contradicts the fact),
# - Unclear (if articles do not give enough information).

# Respond with:
# 1. Short Reasoning (2-3 lines)
# 2. source: source_id_from_api
# 3. Final Verdict: Proved / Refuted / Unclear
#     """

#     try:
#         response = client.chat.completions.create(
#             model=DEFAULT_MODEL,
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.2
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         logging.error(f"OpenAI API call failed: {e}")
#         return "Error: Unable to get response"

# def main():
#     # Load claims
#     try:
#         with open("claims_from_articles.json", "r") as f:
#             claims_data = json.load(f)
#     except Exception as e:
#         logging.error(f"Error reading claims_from_articles.json: {e}")
#         return

#     # Load articles
#     try:
#         with open("filtered_articles.json", "r") as f:
#             articles_data = json.load(f)
#     except Exception as e:
#         logging.error(f"Error reading filtered_articles.json: {e}")
#         return

#     client = initialize_openai_client()
#     if client is None:
#         return

#     # Flatten all articles
#     all_articles = []
#     for source, articles in articles_data.items():
#         for article in articles:
#             title = article.get("title", "")
#             description = article.get("description", "")
#             all_articles.append(f"Title: {title}\nDescription: {description or 'N/A'}")

#     all_articles_text = "\n\n".join(all_articles)

#     results = []
#     for incident in claims_data.get("incidents", []):
#         search_statement = incident.get("search_statement", "")
#         for fact in incident.get("facts", []):
#             fact_text = fact.get("statement", "")

#             verdict_text = call_gpt_for_fact_verification(client, fact_text, all_articles_text)

#             results.append({
#                 "fact": fact_text,
#                 "related_search": search_statement,
#                 "verdict": verdict_text
#             })
#             logging.info(f"Verified fact: {fact_text[:60]}...")

#     # Save to JSON in project root
#     try:
#         project_root = os.path.dirname(os.path.abspath(__file__))
#         output_path = os.path.join(project_root, "../fact_verification_results.json")
#         with open(output_path, "w", encoding="utf-8") as f:
#             json.dump(results, f, indent=2, ensure_ascii=False)
#         logging.info(f"Saved fact verification results to: {output_path}")
#     except Exception as e:
#         logging.error(f"Failed to save verification results: {e}")

# # if __name__ == "__main__":
# #     main()

# import json
# import os
# import openai
# from config import settings
# from logger import logging

# DEFAULT_MODEL = "gpt-4o-mini"

# def initialize_openai_client():
#     try:
#         return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
#     except Exception as e:
#         logging.error(f"Failed to initialize OpenAI client: {e}")
#         return None

# def call_gpt_for_fact_verification(client, fact_text, all_articles_text):
#     prompt = f"""
# You are a fact verification assistant.

# Fact to verify:
# "{fact_text}"

# Below are the contents of multiple news articles. Titles, descriptions, and sources are included.

# Articles:
# {all_articles_text}

# Based on the articles, determine if the fact is:
# - Proved (if the fact's core claim is supported clearly by any article),
# - Refuted (if any article directly contradicts the fact),
# - Unclear (if articles do not give enough information).

# Respond with:
# 1. Short Reasoning (2-3 lines)
# 2. Source: source_id_from_api
# 3. Final Verdict: Proved / Refuted / Unclear
#     """

#     try:
#         response = client.chat.completions.create(
#             model=DEFAULT_MODEL,
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.2
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         logging.error(f"OpenAI API call failed: {e}")
#         return "Error: Unable to get response"

# def main():
#     # Load claims
#     try:
#         with open("claims_from_articles.json", "r") as f:
#             claims_data = json.load(f)
#     except Exception as e:
#         logging.error(f"Error reading claims_from_articles.json: {e}")
#         return

#     # Load articles
#     try:
#         with open("filtered_articles.json", "r") as f:
#             articles_data = json.load(f)
#     except Exception as e:
#         logging.error(f"Error reading filtered_articles.json: {e}")
#         return

#     client = initialize_openai_client()
#     if client is None:
#         return

#     # Flatten all articles with their sources
#     all_articles = []
#     for source_name, articles in articles_data.items():
#         for article in articles:
#             title = article.get("title", "")
#             description = article.get("description", "")
#             source = article.get("source_id_from_api") or article.get("name", source_name)
#             all_articles.append(
#                 f"Title: {title}\nDescription: {description or 'N/A'}\nSource: {source}"
#             )

#     all_articles_text = "\n\n".join(all_articles)

#     results = []
#     for incident in claims_data.get("incidents", []):
#         search_statement = incident.get("search_statement", "")
#         for fact in incident.get("facts", []):
#             fact_text = fact.get("statement", "")
#             verdict_text = call_gpt_for_fact_verification(client, fact_text, all_articles_text)
#             results.append({
#                 "fact": fact_text,
#                 "related_search": search_statement,
#                 "verdict": verdict_text
#             })
#             logging.info(f"Verified fact: {fact_text[:60]}...")

#     # Save to JSON in project root
#     try:
#         project_root = os.path.dirname(os.path.abspath(__file__))
#         output_path = os.path.join(project_root, "../fact_verification_results.json")
#         with open(output_path, "w", encoding="utf-8") as f:
#             json.dump(results, f, indent=2, ensure_ascii=False)
#         logging.info(f"Saved fact verification results to: {output_path}")
#     except Exception as e:
#         logging.error(f"Failed to save verification results: {e}")


# import json
# import os
# import openai
# from config import settings
# from logger import logging
# from core.llm_processor import initialize_openai_client as init_llm_for_verification, call_gpt_for_fact_verification





# import streamlit as st
# import json
# import os
# import time
# from datetime import datetime
# from typing import Optional, Dict, Any

# from logger import logging
# from config import settings
# from core.claim_extractor import initialize_openai_client as init_llm_for_claims_extraction, extract_incidents_from_article
# from core.source_fetcher import fetch_from_newsdata, fetch_from_gnews_io
# from core.llm_processor import initialize_openai_client as init_llm_for_verification, call_gpt_for_fact_verification, run_fact_checking_pipeline


# DEFAULT_MODEL = "gpt-4o-mini"

# def initialize_openai_client():
#     try:
#         return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
#     except Exception as e:
#         logging.error(f"Failed to initialize OpenAI client: {e}")
#         return None

# def call_gpt_for_fact_verification(client, fact_text, all_articles_text):
#     prompt = f"""
#         You are a fact verification assistant.

#         Fact to verify:
#         "{fact_text}"

#         Below are the contents of multiple news articles. Each article includes its title, description, and the source name.

#         Articles:
#         {all_articles_text}

#         Based on the articles, determine if the fact is:
#         - **Proved** (if the fact's core claim is supported clearly by any article),
#         - **Refuted** (if any article directly contradicts the fact),
#         - **Unclear** (if articles do not give enough information).

#         Your response should include:
#         1. **Short Reasoning** (2–3 lines)
#         2. **Final Verdict**: Proved / Refuted / Unclear
#         3. **Supporting Source(s)**: Name the news source(s) you used to justify the verdict, if any (e.g. "NDTV", "BBC" or etc.). If verdict is *Unclear*, write "None".

#         Respond in this exact format:
#         Reasoning: ...
#         Verdict: ...
#         Sources: ...
#         """

#     try:
#         response = client.chat.completions.create(
#             model=DEFAULT_MODEL,
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.2
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         logging.error(f"OpenAI API call failed: {e}")
#         return "Error: Unable to get response"


# PROJECT_ROOT_DIR_APP = os.path.dirname(os.path.abspath(__file__))

# def run_fact_checking_pipeline(article_text: str) -> Optional[Dict[str, Any]]:
#     logging.info("--- Running Streamlit Fact-Checking Pipeline ---")
#     results = {}

#     st_status_1 = st.status("Stage 1: Extracting claims from article...", expanded=True)
#     try:
#         llm_client = init_llm_for_claims_extraction()
#         if not llm_client:
#             st_status_1.update(label="Stage 1 Failed: LLM client init error", state="error")
#             return None

#         incidents = extract_incidents_from_article(article_text, llm_client)
#         if not incidents:
#             st_status_1.update(label="Stage 1 Failed: No incidents extracted", state="error")
#             return None

#         claims_output = {"incidents": incidents}
#         results["incidents"] = incidents

#         with open("claims_from_articles.json", "w", encoding="utf-8") as f:
#             json.dump(claims_output, f, ensure_ascii=False, indent=2)

#         st_status_1.update(label="Stage 1: Claims extracted!", state="complete")
#     except Exception as e:
#         st_status_1.update(label=f"Stage 1 Error: {e}", state="error")
#         return None
#     time.sleep(0.2)

#     st_status_2 = st.status("Stage 2: Fetching articles from external sources...", expanded=True)
#     try:
#         all_articles = []

#         for incident in incidents:
#             query = incident.get("search_statement")
#             if not query:
#                 continue
#             articles = fetch_from_newsdata(query) + fetch_from_gnews_io(query)
#             for article in articles:
#                 all_articles.append(article)

#         results["articles"] = all_articles

#         with open("filtered_articles.json", "w", encoding="utf-8") as f:
#             json.dump(all_articles, f, ensure_ascii=False, indent=2)

#         st_status_2.update(label="Stage 2: Articles fetched!", state="complete")
#     except Exception as e:
#         st_status_2.update(label=f"Stage 2 Error: {e}", state="error")
#         return None
#     time.sleep(0.2)

#     st_status_3 = st.status("Stage 3: Verifying facts with LLM...", expanded=True)
#     try:
#         llm_client_verify = init_llm_for_verification()
#         all_verifications = []

#         flat_articles = []
#         for article in all_articles:
#             title = article.get("title", "")
#             description = article.get("description", "")
#             source = article.get("source_id_from_api") or article.get("name", "Unknown")
#             flat_articles.append(f"Title: {title}\nDescription: {description}\nSource: {source}")

#         article_texts = "\n\n".join(flat_articles)

#         for incident in incidents:
#             search_query = incident.get("search_statement")
#             for fact in incident.get("facts", []):
#                 fact_text = fact.get("statement")
#                 verdict = call_gpt_for_fact_verification(llm_client_verify, fact_text, article_texts)
#                 all_verifications.append({
#                     "fact": fact_text,
#                     "related_search": search_query,
#                     "verdict": verdict
#                 })

#         results["verifications"] = all_verifications

#         with open("fact_verification_results.json", "w", encoding="utf-8") as f:
#             json.dump(all_verifications, f, ensure_ascii=False, indent=2)

#         st_status_3.update(label="Stage 3: Verification complete!", state="complete")
#         return results
#     except Exception as e:
#         st_status_3.update(label=f"Stage 3 Error: {e}", state="error")
#         return None

