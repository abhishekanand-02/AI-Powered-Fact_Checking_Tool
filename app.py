import streamlit as st
import os
from logger import logging
from core.llm_processor import run_fact_checking_pipeline

PROJECT_ROOT_DIR_APP = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="AI Fact-Checker", layout="wide")
st.title("Fact-Checking Tool")

if 'pipeline_output' not in st.session_state:
    st.session_state.pipeline_output = None

article_text = st.text_area("Paste the article text you want to fact-check:", height=250)

if st.button(" Run Fact-Check"):
    if article_text.strip():
        st.session_state.pipeline_output = run_fact_checking_pipeline(article_text)
    else:
        st.warning("Please enter some article text to analyze.")

output = st.session_state.pipeline_output
if output:
    st.success("Fact-checking completed!")

    st.subheader("Verification Results")
    for v in output["verifications"]:
        st.markdown(f"- **Claim:** *{v['fact']}*")
        st.info(v["verdict"])
        st.markdown("---")

    logging.info("Fact-checking process completed successfully.")








# LATER REViEW TO UTILIZE THIS ALSO: 

# import streamlit as st
# import json
# import os
# import time
# from datetime import datetime
# from typing import Optional, Dict, Any

# # --- Setup Logging ---
# from logger import logging
# logger = logging.getLogger(__name__)

# # --- Core Logic Imports ---
# from config import settings # Ensure settings are loaded
# from core.claim_extractor import initialize_openai_client as init_llm_for_claims_extraction, extract_title_and_claims
# from core.source_fetcher import fetch_sources_for_query
# from core.llm_processor import initialize_openai_client as init_llm_for_verification, process_all_claims_and_generate_statements

# # --- Define Output Directory for Streamlit Runs ---
# # Place it inside the project root for clarity, or adjust as needed
# PROJECT_ROOT_DIR_APP = os.path.dirname(os.path.abspath(__file__))
# STREAMLIT_RUN_OUTPUT_DIR = os.path.join(PROJECT_ROOT_DIR_APP, "streamlit_outputs")
# os.makedirs(STREAMLIT_RUN_OUTPUT_DIR, exist_ok=True)

# # --- Helper Function for Saving JSON ---
# def save_json_to_file(data: Dict, base_filename: str, run_timestamp: str):
#     """Saves dictionary data to a JSON file with a timestamp."""
#     try:
#         filename = f"{base_filename}_{run_timestamp}.json"
#         file_path = os.path.join(STREAMLIT_RUN_OUTPUT_DIR, filename)
#         with open(file_path, 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=2)
#         logger.info(f"Successfully saved data to {file_path}")
#         return file_path # Return the path in case it's needed
#     except Exception as e:
#         logger.error(f"Error saving data to {base_filename} for run {run_timestamp}: {e}")
#         return None

# # --- Main Pipeline Function ---
# def run_fact_checking_pipeline(article_text: str) -> Optional[Dict[str, Any]]:
#     logger.info(f"--- Starting Fact-Checking Pipeline for Streamlit Run ---")
#     pipeline_results = {} # Stores results passed between stages
#     run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # Unique ID for this run's files

#     # --- Stage 1: Extract Title, Claims, and Country Code ---
#     st_status_stage1 = st.status("Stage 1: Extracting article details...", expanded=True)
#     try:
#         llm_claim_client = init_llm_for_claims_extraction()
#         if not llm_claim_client:
#             st_status_stage1.update(label="Stage 1 Failed: LLM init error.", state="error", expanded=True)
#             return None

#         summary_title, extracted_claims_dict, detected_country_code = extract_title_and_claims(
#             article_text, llm_claim_client
#         )
#         if not summary_title or not extracted_claims_dict:
#             st_status_stage1.update(label="Stage 1 Failed: Could not extract details.", state="error", expanded=True)
#             return None
        
#         # Store results for pipeline
#         stage1_output_data = {
#             "summary_title": summary_title,
#             "extracted_claims": extracted_claims_dict,
#             "detected_country_code": detected_country_code
#         }
#         pipeline_results.update(stage1_output_data)
        
#         # Save Stage 1 output
#         save_json_to_file(stage1_output_data, "1_extracted_claims", run_timestamp)

#         st_status_stage1.update(label="Stage 1: Article details extracted!", state="complete", expanded=False)
#         logger.info(f"Stage 1 OK: Title='{summary_title}', Claims={len(extracted_claims_dict)}, Country='{detected_country_code}'")
#     except Exception as e:
#         st_status_stage1.update(label=f"Stage 1 Error: {str(e)[:100]}", state="error", expanded=True)
#         logger.critical(f"Stage 1 Critical Error: {e}", exc_info=True)
#         return None
#     time.sleep(0.2)

#     # --- Stage 2: Fetch Source Articles ---
#     st_status_stage2 = st.status("Stage 2: Fetching source articles...", expanded=True)
#     try:
#         # Use results from Stage 1
#         fetched_api_articles_dict = fetch_sources_for_query(
#             query=pipeline_results["summary_title"],
#             country_code=pipeline_results["detected_country_code"]
#         )
#         if not isinstance(fetched_api_articles_dict, dict):
#             st_status_stage2.update(label="Stage 2 Failed: Unexpected source fetch format.", state="error", expanded=True)
#             return None
        
#         pipeline_results["fetched_sources_data"] = fetched_api_articles_dict
        
#         # Save Stage 2 output
#         save_json_to_file(fetched_api_articles_dict, "2_fetched_sources", run_timestamp)
        
#         if not fetched_api_articles_dict:
#             st_status_stage2.update(label="Stage 2: No source articles found.", state="complete", expanded=False)
#             logger.warning("Stage 2: No source articles fetched.")
#         else:
#             st_status_stage2.update(label="Stage 2: Source articles fetched!", state="complete", expanded=False)
#             # Log summary count
#             total_fetched_count = sum(len(v) for v in fetched_api_articles_dict.values() if isinstance(v, list))
#             logger.info(f"Stage 2 OK: Fetched {total_fetched_count} articles from {len(fetched_api_articles_dict)} APIs.")
#     except Exception as e:
#         st_status_stage2.update(label=f"Stage 2 Error: {str(e)[:100]}", state="error", expanded=True)
#         logger.critical(f"Stage 2 Critical Error: {e}", exc_info=True)
#         return None
#     time.sleep(0.2)

#     # --- Stage 3: Process Claims & Generate Statements ---
#     st_status_stage3 = st.status("Stage 3: Generating verification statements...", expanded=True)
#     try:
#         llm_verification_client = init_llm_for_verification()
#         if not llm_verification_client:
#             st_status_stage3.update(label="Stage 3 Failed: LLM init error.", state="error", expanded=True)
#             return None

#         # Prepare inputs needed by llm_processor
#         claims_input_for_processor = {"extracted_claims": pipeline_results["extracted_claims"]}
#         fetched_sources_input_data = pipeline_results["fetched_sources_data"]

#         final_verification_statements = process_all_claims_and_generate_statements(
#             claims_input_data=claims_input_for_processor,
#             fetched_sources_input_data=fetched_sources_input_data,
#             llm_client=llm_verification_client
#         )
        
#         pipeline_results["final_verification_statements"] = final_verification_statements
        
#         # Save Stage 3 output
#         save_json_to_file(final_verification_statements, "3_verification_statements", run_timestamp)

#         if not final_verification_statements:
#             st_status_stage3.update(label="Stage 3: No verification statements generated.", state="warning", expanded=False)
#             logger.warning("Stage 3: No final verification statements generated.")
#         else:
#             st_status_stage3.update(label="Stage 3: Claim verification complete!", state="complete", expanded=False)
#             logger.info(f"Stage 3 OK: Generated statements for {len(final_verification_statements)} claims.")
        
#         return pipeline_results # Return the dictionary containing all results
#     except Exception as e:
#         st_status_stage3.update(label=f"Stage 3 Error: {str(e)[:100]}", state="error", expanded=True)
#         logger.critical(f"Stage 3 Critical Error: {e}", exc_info=True)
#         return None


# # --- Streamlit UI Configuration & Logic ---
# st.set_page_config(page_title="AI Fact-Checker", layout="wide")
# st.title("AI-Powered Fact-Checking Tool")


# if 'pipeline_output' not in st.session_state:
#     st.session_state.pipeline_output = None
# if 'processing_error' not in st.session_state:
#     st.session_state.processing_error = None

# article_text_input_ui = st.text_area("Paste News Article Text Here:", height=250, key="article_text_ui")

# if st.button("🔍 Fact-Check Article", type="primary", key="analyze_button_ui"):
#     if article_text_input_ui.strip():
#         st.session_state.pipeline_output = None
#         st.session_state.processing_error = None
        
#         # Call the main pipeline function
#         final_results = run_fact_checking_pipeline(article_text_input_ui)
        
#         if final_results:
#             st.session_state.pipeline_output = final_results
#         else:
#             st.session_state.processing_error = "Fact-checking process encountered an issue. See stage messages above for details."
#             logger.error("Fact-checking pipeline did not complete successfully.")
#             # Error display is handled by st.status and the section below
            
#     else:
#         st.warning("Please paste some article text to analyze.")

# # --- Display Final Results ---
# if st.session_state.processing_error and not st.session_state.pipeline_output:
#     # Show general error only if pipeline failed entirely and produced no output dictionary
#     st.error(st.session_state.processing_error)

# if st.session_state.pipeline_output:
#     st.success("Fact-Checking Process Completed!")
#     output_data = st.session_state.pipeline_output # Contains all results

#     # --- Display Section 1 ---
#     st.subheader("1. Extracted Article Information")
#     st.markdown(f"**Search Title:** `{output_data.get('summary_title', 'N/A')}`")
#     st.markdown(f"**Detected Country/Region:** `{output_data.get('detected_country_code', 'N/A')}`")
    
#     original_claims_display = output_data.get('extracted_claims', {})
#     if original_claims_display:
#         with st.expander("View Extracted Claims", expanded=False):
#             if not original_claims_display:
#                 st.caption("No claims were extracted.")
#             else:
#                 st.json(original_claims_display) # Display claims as JSON
#                 # Alternatively, loop and display:
#                 # for claim_key_disp, claim_text_disp in original_claims_display.items():
#                 #     st.markdown(f"- **{claim_key_disp}:** {claim_text_disp}")
    
#     # --- Display Section 2 ---
#     st.subheader("2. Fetched Source Articles Summary")
#     fetched_sources_display = output_data.get('fetched_sources_data', {})
#     if fetched_sources_display:
#         with st.expander("View Fetched Sources (Summary)", expanded=False):
#             if not fetched_sources_display:
#                  st.caption("No articles were fetched from any source API.")
#             else:
#                 for api_name_disp, articles_list_disp in fetched_sources_display.items():
#                     st.markdown(f"**From {api_name_disp}:** ({len(articles_list_disp)} articles found)")
#                     for art_idx, art_disp in enumerate(articles_list_disp[:3]): # Show first 3
#                         title_disp = art_disp.get('title', f"Untitled Article from {api_name_disp}")
#                         url_disp = art_disp.get('url', '#') # Need URL from source_fetcher
#                         outlet_disp = art_disp.get('source_id_from_api') or art_disp.get('name', 'Unknown Outlet')
#                         st.caption(f"  {art_idx+1}. [{title_disp}]({url_disp}) - *{outlet_disp}*")
#     else:
#         st.info("No source articles were fetched or data is not available.")

#     # --- Display Section 3 ---
#     st.subheader("3. Claim Verification Statements")
#     verification_statements_display = output_data.get('final_verification_statements', {})
#     if verification_statements_display:
#         for claim_key_vs, statement_vs in verification_statements_display.items():
#             original_claim_text_vs = original_claims_display.get(claim_key_vs, "Original claim text missing.")
#             # Use columns for better layout
#             col1, col2 = st.columns([2,3])
#             with col1:
#                 st.markdown(f"**Claim ({claim_key_vs}):**")
#                 st.markdown(f"*\"{original_claim_text_vs}\"*")
#             with col2:
#                  st.info(f"**Verification:** {statement_vs}")
#             st.markdown("---") # Separator
#     else:
#         st.warning("No verification statements were generated for the claims (perhaps due to lack of sources or errors).")

# st.sidebar.header("Fact-Checker POC")
# st.sidebar.info(
#     "AI-powered claim extraction, source fetching, and verification."
# )

# Working code ---------------------------------------------

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
# from core.llm_processor import initialize_openai_client as init_llm_for_verification, call_gpt_for_fact_verification

# # Output folder for saved runs
# PROJECT_ROOT_DIR_APP = os.path.dirname(os.path.abspath(__file__))
# STREAMLIT_RUN_OUTPUT_DIR = os.path.join(PROJECT_ROOT_DIR_APP, "streamlit_outputs")
# os.makedirs(STREAMLIT_RUN_OUTPUT_DIR, exist_ok=True)

# def save_json_to_file(data: Dict, base_filename: str, run_timestamp: str):
#     filename = f"{base_filename}_{run_timestamp}.json"
#     path = os.path.join(STREAMLIT_RUN_OUTPUT_DIR, filename)
#     with open(path, 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False, indent=2)
#     return path

# def run_fact_checking_pipeline(article_text: str) -> Optional[Dict[str, Any]]:
#     logging.info("--- Running Streamlit Fact-Checking Pipeline ---")
#     run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
#     results = {}

#     # Stage 1: Extract Incidents
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
#         save_json_to_file(claims_output, "1_claims", run_id)
#         st_status_1.update(label="Stage 1: Claims extracted!", state="complete")
#     except Exception as e:
#         st_status_1.update(label=f"Stage 1 Error: {e}", state="error")
#         return None
#     time.sleep(0.2)

#     # Stage 2: Fetch articles
#     st_status_2 = st.status("Stage 2: Fetching articles from external sources...", expanded=True)
#     try:
#         all_sources = {}
#         for incident in incidents:
#             query = incident.get("search_statement")
#             if not query:
#                 continue
#             articles = fetch_from_newsdata(query) + fetch_from_gnews_io(query)
#             all_sources[query] = articles
#         results["articles"] = all_sources
#         save_json_to_file(all_sources, "2_articles", run_id)
#         st_status_2.update(label="Stage 2: Articles fetched!", state="complete")
#     except Exception as e:
#         st_status_2.update(label=f"Stage 2 Error: {e}", state="error")
#         return None
#     time.sleep(0.2)

#     # Stage 3: Verify claims
#     st_status_3 = st.status("Stage 3: Verifying facts with LLM...", expanded=True)
#     try:
#         llm_client_verify = init_llm_for_verification()
#         all_verifications = []

#         flat_articles = []
#         for articles in all_sources.values():
#             for article in articles:
#                 flat_articles.append(f"Title: {article.get('title', '')}\nDescription: {article.get('description', '')}")
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
#         save_json_to_file(all_verifications, "3_verifications", run_id)
#         st_status_3.update(label="Stage 3: Verification complete!", state="complete")
#         return results
#     except Exception as e:
#         st_status_3.update(label=f"Stage 3 Error: {e}", state="error")
#         return None

# # --- Streamlit App Interface ---
# st.set_page_config(page_title="AI Fact-Checker", layout="wide")
# st.title(" AI-Powered Fact-Checking Tool")

# if 'pipeline_output' not in st.session_state:
#     st.session_state.pipeline_output = None

# article_text = st.text_area("Paste the article text you want to fact-check:", height=250)

# if st.button("🔍 Run Fact-Check"):
#     if article_text.strip():
#         st.session_state.pipeline_output = run_fact_checking_pipeline(article_text)
#     else:
#         st.warning("Please enter some article text to analyze.")

# # --- Display Results ---
# output = st.session_state.pipeline_output
# if output:
#     st.success("Fact-checking completed!")

#     # st.subheader("📌 Extracted Claims")
#     # for idx, incident in enumerate(output["incidents"], start=1):
#     #     st.markdown(f"**Incident {idx}:** {incident['incident_summary']}")
#     #     for fact in incident.get("facts", []):
#     #         st.markdown(f"- 🔹 *{fact['statement']}*")

#     # st.subheader(" Fetched Articles (Summary)")
#     # for query, articles in output["articles"].items():
#     #     st.markdown(f"**Query:** `{query}` — {len(articles)} articles")
#     #     for art in articles[:3]:  # Show up to 3
#     #         st.caption(f"- {art.get('title', 'No Title')} (Source: {art.get('source_id_from_api', 'Unknown')})")

#     st.subheader(" Verification Results")
#     for v in output["verifications"]:
#         st.markdown(f"- **Claim:** *{v['fact']}*")
#         st.info(v["verdict"])
#         st.markdown("---")



# ------------------



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
# from core.llm_processor import initialize_openai_client as init_llm_for_verification, call_gpt_for_fact_verification
# from core
# PROJECT_ROOT_DIR_APP = os.path.dirname(os.path.abspath(__file__))


# st.set_page_config(page_title="AI Fact-Checker", layout="wide")
# st.title("AI-Powered Fact-Checking Tool")

# if 'pipeline_output' not in st.session_state:
#     st.session_state.pipeline_output = None

# article_text = st.text_area("Paste the article text you want to fact-check:", height=250)

# if st.button("🔍 Run Fact-Check"):
#     if article_text.strip():
#         st.session_state.pipeline_output = run_fact_checking_pipeline(article_text)
#     else:
#         st.warning("Please enter some article text to analyze.")

# output = st.session_state.pipeline_output
# if output:
#     st.success("Fact-checking completed!")

#     st.subheader("Verification Results")
#     for v in output["verifications"]:
#         st.markdown(f"- **Claim:** *{v['fact']}*")
#         st.info(v["verdict"])
#         st.markdown("---"