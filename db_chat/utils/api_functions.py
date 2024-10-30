import json
import requests
from db_chat.utils.config import OPENAI_API_KEY, AI_MODEL
from db_chat.utils.database_functions import ask_postgres_database, postgres_connection
from tenacity import retry, wait_random_exponential, stop_after_attempt

@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
def send_api_request_to_openai_api(messages, functions=None, function_call=None, model=AI_MODEL, openai_api_key=OPENAI_API_KEY):
    """ Send the API request to the OpenAI API via Chat Completions endpoint """
    try:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {openai_api_key}"}
        json_data = {"model": model, "messages": messages}
        if functions: 
            json_data.update({"functions": functions})
        if function_call: 
            json_data.update({"function_call": function_call})
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json_data)
        response.raise_for_status()

        return response
    
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to connect to OpenAI API due to: {e}")

def execute_function_call(message, selected_tables, selected_schema):
    """ Run the function call provided by OpenAI's API response """
    if message["function_call"]["name"] == "ask_postgres_database":
        query = json.loads(message["function_call"]["arguments"])["query"]
        print(f"SQL query: {query} \n")
        
        # Check if the query only uses selected tables
        for table in selected_tables:
            if f"{selected_schema}.{table}" not in query:
                return f"Error: The query uses tables that were not selected. Please only use the following tables: {', '.join([f'{selected_schema}.{table}' for table in selected_tables])}"
        
        results = ask_postgres_database(postgres_connection, query)
        print(f"Results A: {results} \n")
    else:
        results = f"Error: function {message['function_call']['name']} does not exist"
    return results
