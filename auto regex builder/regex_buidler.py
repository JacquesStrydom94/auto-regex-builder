import requests
import re
import json
import base64
from itertools import permutations
from collections import defaultdict

# API Endpoint (Replace with actual URLs)
API_SCHEMA_URL = "https://appnostic.dbflex.net/secure/api/v2/97065/AAAtest/describe.json"  # Endpoint to get column types
API_POST_URL = "https://appnostic.dbflex.net/secure/api/v2/97065/AAAtest/create.json"  # Endpoint to test posting data

# Authentication Credentials
USERNAME = "jstrydom@farmtrace.co.za"
PASSWORD = "TeamJay@2024"

# Encode credentials in Base64
credentials = f"{USERNAME}:{PASSWORD}".encode("utf-8")
encoded_credentials = base64.b64encode(credentials).decode("utf-8")

AUTH_HEADERS = {
    "Authorization": f"Basic {encoded_credentials}",
    "Content-Type": "application/json"
}

# Retrieve column types dynamically
def get_column_types():
    response = requests.get(API_SCHEMA_URL, headers=AUTH_HEADERS)
    if response.status_code == 200:
        schema = response.json()
        print("Schema Response:", json.dumps(schema, indent=4))  # Debugging output
        if isinstance(schema, dict) and "columns" in schema:
            return {col["name"]: col["type"] for col in schema["columns"] if "name" in col and "type" in col}
        elif isinstance(schema, list):
            return {col["name"]: col["type"] for col in schema if "name" in col and "type" in col}
        else:
            print("Unexpected schema format")
            return {}
    else:
        print(f"Failed to retrieve column schema, Status Code: {response.status_code}, Response: {response.text}")
        return {}

# Define test data variations
test_data_variants = {
    "Text": ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz", "0123456789", r"!@#$%^&*()_+\-=", "你好世界", "Приветмир", "こんにちは世界", "안녕하세요세계", r"\n\t\r", r"\\", "'", "\""],
    "Multiline": ["Hello\nWorld", "First Line\nSecond Line", "Multiline\ntext\nexample"],
    "Numeric": ["42", "-1", "0", "999999", "1000000000"],
    "Float": ["0.1", "-3.1415", "1e5", "2.0"],
    "Boolean": ["true", "false", "1", "0"],
    "Date": ["2025-03-18", "18/03/2025", "March 18, 2025"],
    "Timestamp": ["2025-03-18T14:30:00Z", "2025-03-18 14:30:00", "2025/03/19 10:42", "19-03-2025 10:42", "03-19-2025 10:42 AM"],
    "Email": ["test@example.com", "user@domain.org"],
    "URL": ["https://example.com", "http://test.org", "https://sub.domain.com/path?query=123"],
    "Phone": ["+1234567890", "(123) 456-7890", "123-456-7890"],
    "Checkbox": ["true", "false", "1", "0"],
}

# Store accepted and rejected values per column
accepted_values = defaultdict(set)
rejected_values = defaultdict(set)

def test_api():
    column_types = get_column_types()
    if not column_types:
        return
    
    for col, col_type in column_types.items():
        if col in ["Date Created", "Date Modified"]:
            continue  # Skip system reserved columns
        
        test_values = test_data_variants.get(col_type, [])
        if not test_values:
            print(f"No test data found for column: {col} (type: {col_type})")
            continue
        
        for value in test_values:
            payload = [{col: value}]
            response = requests.post(API_POST_URL, json=payload, headers=AUTH_HEADERS)
            print(f"Testing column '{col}' with value '{value}': Status {response.status_code}, Response: {response.text}")
            
            if response.status_code in [200, 201]:
                accepted_values[col].add(value)
            else:
                rejected_values[col].add(value)

def generate_regex():
    column_regex = {}
    
    for col, values in accepted_values.items():
        if not values:
            print(f"No accepted values for column: {col}, skipping regex generation.")
            continue

        patterns = set()

        for v in values:
            if re.fullmatch(r"^[A-Za-z0-9!@#$%^&*()_+\-=\\]+$", v):
                patterns.add("[A-Za-z0-9!@#$%^&*()_+\-=\\]+")
            elif re.fullmatch(r"^[0-9]+$", v):
                patterns.add("[0-9]+")
            elif re.fullmatch(r"^(true|false|1|0)$", v):
                patterns.add("(true|false|1|0)")
            elif re.fullmatch(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}$", v):
                patterns.add("\d{4}/\d{2}/\d{2} \d{2}:\d{2}")  # YYYY/MM/DD HH:MM
            elif re.fullmatch(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}$", v):
                patterns.add("\d{2}-\d{2}-\d{4} \d{2}:\d{2}")  # DD-MM-YYYY HH:MM
            elif re.fullmatch(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2} (AM|PM)$", v):
                patterns.add("\d{2}-\d{2}-\d{4} \d{2}:\d{2} (AM|PM)")  # MM-DD-YYYY HH:MM AM/PM
            elif re.fullmatch(r"^https?://[\\w.-]+(?:\\.[\\w.-]+)+[/\\w._%&=+-]*$", v):
                patterns.add(r"https?://[\\w.-]+(?:\\.[\\w.-]+)+[/\\w._%&=+-]*")

        final_pattern = "|".join(patterns)
        column_regex[col] = f"^({final_pattern})$" if final_pattern else ""
    
    return column_regex

test_api()
regex_dict = generate_regex()

with open("regex_dictionary.json", "w") as f:
    json.dump(regex_dict, f, indent=4)

print("Regex dictionary generated:")
print(json.dumps(regex_dict, indent=4))
