# import os
# import json
# from logger import logging


# def save_json_to_root(data: dict, filename: str):
#     """
#     Save a dictionary as JSON to the project root directory.

#     Args:
#         data (dict): The data to save.
#         filename (str): The name of the output file (e.g., 'filtered_articles.json').
#     """
#     try:
#         project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#         file_path = os.path.join(project_root, filename)

#         with open(file_path, "w", encoding="utf-8") as f:
#             json.dump(data, f, ensure_ascii=False, indent=2)
        
#         logging.info(f"Saved JSON data to: {file_path}")
#     except Exception as e:
#         logging.error(f"Failed to save JSON data to {filename}: {e}")

# def load_claims_from_json():
#     try:
#         with open('claims_from_articles.json', 'r') as file:
#             claims_data = json.load(file)

#             if "incidents" in claims_data:
#                 queries = [incident["search_statement"] for incident in claims_data["incidents"] if "search_statement" in incident]
#                 logging.info(f"Extracted queries: {queries}")
#                 return queries
#             else:
#                 logging.error("No incidents found in claims_from_articles.json.")
#                 return []

#     except Exception as e:
#         logging.error(f"Error loading claims_from_articles.json: {e}")
#         return []



import os
import json
from logger import logging

def save_json_to_root(data: dict, filename: str):
    """
    Save a dictionary as JSON to the project root directory.

    Args:
        data (dict): The data to save.
        filename (str): The name of the output file (e.g., 'filtered_articles.json').
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(project_root, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Saved JSON data to: {file_path}")
    except Exception as e:
        logging.error(f"Failed to save JSON data to {filename}: {e}")


def load_claims_from_json(file_path: str) -> dict:
    """
    Loads the claims from a JSON file.

    Args:
        file_path (str): The path to the claims JSON file.

    Returns:
        dict: The claims data loaded from the file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            claims_data = json.load(f)
        
        # Assuming you need the incidents and their queries
        if "incidents" in claims_data:
            queries = [incident["search_statement"] for incident in claims_data["incidents"] if "search_statement" in incident]
            logging.info(f"Extracted {len(queries)} queries from the claims data.")
            return claims_data  # Or just return the queries if needed separately
        else:
            logging.error("No incidents found in the claims data.")
            return {}

    except Exception as e:
        logging.error(f"Error loading claims from {file_path}: {e}")
        return {}

