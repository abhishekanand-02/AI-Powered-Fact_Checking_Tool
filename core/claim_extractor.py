import openai
import json
from config import settings
from logger import logging

DEFAULT_MODEL = "gpt-4o-mini"

def initialize_openai_client():
    if not settings.OPENAI_API_KEY:
        logging.error("OpenAI API key is not configured.")
        return None
    try:
        return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
        return None

def extract_incidents_from_article(
    article_text: str, llm_client: openai.OpenAI, model_name: str = None
) -> list[dict] | None:
    """
    Extracts a list of incidents from an article using LLM.
    Each incident includes: incident_summary, search_statement, and facts.
    """
    if not llm_client:
        logging.error("LLM client is not initialized.")
        return None

    if not article_text.strip():
        logging.warning("Empty article text provided.")
        return None

    model_to_use = model_name or DEFAULT_MODEL
    logging.info(f"Using model for incident extraction: {model_to_use}")

    system_prompt = """
        Read the following article and identify distinct substories or incidents within it. Each substory should represent only one coherent incident, even if it contains multiple factual claims.

        For each identified incident, extract and return the information in the following format:

        [
          {
            "incident_summary": "<A concise summary of the incident>",
            "search_statement": "<Multiple distinct natural language search queries about the incident, joined using ' OR '>",
            "facts": [
              {
                "statement": "<A factual claim related to the incident>",
                "date": "<Date if mentioned, else null>",
                "place": "<Place if mentioned, else null>"
              }
            ]
          }
        ]

        Guidelines:
        - A "fact" is a statement that can be validated as true, false, or partially true using external sources.
        - Each group of facts must relate to only one incident.
        - Do not group together claims that describe different events.
        - For the "search_statement":
          - Generate 2 to 4 **distinct natural language search queries** that someone might use to look up the incident online.
          - Ensure that these queries **do not repeat phrasing** and each focuses on a slightly different angle or keyword set relevant to the same incident.
          - Concatenate these search queries using ` OR ` (capitalized, with spaces) so they can be used directly in a search API.
        - If a fact does not mention a date or place, return those fields as `null`.
    """

    user_prompt = f"""
    Article Text:
    ---
    {article_text}
    ---

    Return a JSON object with an "incidents" key, where the value is a list of incident objects.
    """

    try:
        response = llm_client.chat.completions.create(
            model=model_to_use,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()}
            ],
            temperature=0.0,
            max_tokens=2500
        )

        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)

        if "incidents" in parsed and isinstance(parsed["incidents"], list):
            logging.info(f"Extracted {len(parsed['incidents'])} incident(s) from article.")
            return parsed["incidents"]
        else:
            logging.warning("LLM response missing 'incidents' key or value is not a list.")
            return []

    except openai.APIError as e:
        logging.error(f"OpenAI API error: {e}")
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from LLM. Response: {content if 'content' in locals() else 'Not available'}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)

    return None


# Uncomment the following lines to run the script directly for testing purposes

# if __name__ == '__main__':
#     logging.info("--- Testing Incident Extractor ---")
#     client = initialize_openai_client()

#     if client:
#         sample_article_text = """
#        Operation Sindoor live updates: The Indian armed forces successfully executed Operation Sindoor in the early hours of Wednesday, carrying out targeted strikes on nine "terrorist infrastructure" sites in Pakistan and Pakistan-occupied Kashmir (PoK) in response to the April 2025 Pahalgam attack that left 26 civilians dead. Shortly after the confirmation of military strikes in Pakistan, Indian Army said in a post on X "Justice is served. Jai Hind!". Prime Minister Narendra Modi, who had vowed stern action to the terror attack in Baisaran, constantly monitored the Operation Sindoor throughout the night.Colonel Sofiya Qureshi, Wing Commander Vyomika Singh, and foreign secretary Vikram Misri addressed a briefing on Operation Sindoor and said that the targets chosen by the Indian armed forces were based on strong intelligence inputs and their involvement in terror activities. Col. Qureshi also clarified that no military infrastructure of Pakistan was struck during the operation.Foreign secretary Vikram Misri said that probe into the Pahalgam terror attack has clearly established Pakistan links.ALSO READ | How the 9 targets India hit during Operation Sindoor were providing support to terroristsList of sites hit in Operation Sindoor: Bahawalpur, located around 100 Km from the International Boundary. It is the headquarters of the JeM.Muridke, located 30 km from the border opposite Samba. It is an LeT camp.Gulpur, 35 km from LoC in Poonch-Rajouri.LeT camp in Sawai, 30 km inside POK, Tangdhar Sector.Bilal Camp, a JeM launchpad.LeT Kotli camp, 15 km from LoC opposite Rajouri.Barnala camp, 10 km from LoC opposite Rajouri.Sarjal camp, JeM camp about 8 km from IB opposite Samba-Kathua.Mehmoona camp, 15 km from IB, near Sialkot, HM training camp.Operation Sindoor | Key pointsThe Indian Army said Justice is served after the nations armed forces carried out strikes on terror infrastructure in Pakistan and PoK in Operation Sindoor.Pakistans external affairs ministry in a statement said the Indian Air Force, while remaining within Indian airspace, attacked targets across the international border in Muridke and Bahawalpur, and across the Line of Control in Kotli and Muzaffarabad in Pakistan-occupied Kashmir (PoK) using standoff weapons.Pakistans Inter-Services Public Relations (ISPR) Director General responded to Indias Operation Sindoor and said in a statement that Indias "temporary pleasure will be replaced by enduring grief". It said that Islamabad will respond to it at a time and place of its own choosing and that the strikes "will not go unanswered.Meanwhile, due to the prevailing situation, all educational institutions in the five border districts of Jammu, Samba, Kathua, Rajouri, and Poonch, have been closed on Wednesday. Schools in Rajasthan and Punjab border districts have also been ordered shut.
#         """

#         logging.info("Extracting incidents...")
#         incidents = extract_incidents_from_article(sample_article_text, client)

#         if incidents is not None:
#             save_json_to_root({"incidents": incidents}, "claims_from_articles.json")
#         else:
#             logging.error("No incidents extracted.")
#     else:
#         logging.error("OpenAI client could not be initialized.")
