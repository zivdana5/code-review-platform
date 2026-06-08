from dataclasses import dataclass
import requests
import json
from typing import List, Dict, Any

## constants for Ollama LLM client

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_ENDPOINT = "/api/chat"
OLLAMA_MODEL = "qwen2.5-coder:7b"
OLLAMA_TIMEOUT_SECONDS = 120
MEANINGFUL_VARIABLE_NAMES_PROMPT ="""
You are a code review assistant.
Your task is to check the following rule:
All variables in the Python code should have meaningful and descriptive names.
A meaningful variable name should clearly describe the purpose of the variable.
Bad examples: x, y, z, a, b, tmp, data, val, foo, bar, unless their meaning is obvious in a very small/local context.
Good examples: total_price, user_count, file_content, scan_result.
Review the Python code below.
Return only valid JSON as written in the system prompt, with no additional text.
Use true if the code follows the rule.
Use false if the code does not follow the rule."""
DEFAULT_SYSTEM_PROMPT = """
You are a code review assistant.
You check Python code according to one specific rule.
Return only valid JSON.
Do not add text before or after the JSON.
Do not use markdown.
Do not explain outside the JSON.
The JSON must be exactly in this format:
{
    "passed": true
}
"""
DOCSTRING_MATCHES_LOGIC_PROMPT = """
You are a code review assistant.
Your task is to check the following rule:
Each function docstring should accurately reflect the actual logic of the function.
Check whether the function docstrings describe what the function really does.
If a function has no docstring, only fail this rule if the function clearly should have one because it is non-trivial.
If a docstring exists but describes different behavior from the implementation, return false.
Review the Python code below.
Return only valid JSON as written in the system prompt, with no additional text.
Use true if the code follows the rule.
Use false if the code does not follow the rule."""


""" The ReviewRule dataclass represents a code review rule, including its ID, description, and the prompt template used to check the rule. """
@dataclass
class ReviewRule:
    rule_id: str
    description: str
    user_prompt_template: str

    def build_prompt(self, code: str) -> str:
        return f"{self.user_prompt_template}\n\nPython code:\n```python\n{code}\n```"
    
# def add_rule(rule_id: str, description: str, prompt_template: str):
#     new_rule = ReviewRule(
#         rule_id=rule_id,
#         description=description,
#         user_prompt_template=prompt_template
#     )
#     REVIEW_RULES.append(new_rule)

REVIEW_RULES = [
    ReviewRule(
        rule_id="meaningful_variable_names",
        description="All variables have meaningful names",
        user_prompt_template=MEANINGFUL_VARIABLE_NAMES_PROMPT,
    ),
    ReviewRule(
        rule_id="docstring_matches_logic",
        description="Function docstrings reflect the actual code logic",
        user_prompt_template=DOCSTRING_MATCHES_LOGIC_PROMPT,
    )
]

""" The OllamaClient class is responsible for communicating with the Ollama LLM API.
It sends prompts to the model and retrieves responses. """
class OllamaClient:
    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout_seconds: int = OLLAMA_TIMEOUT_SECONDS,
        endpoint: str = OLLAMA_ENDPOINT,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.system_prompt = system_prompt
        self.endpoint = endpoint
    
    def ask(self, prompt: str) -> str:  
        url = f"{self.base_url}{self.endpoint}"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            
            data = response.json()
            if "message" not in data:
                raise RuntimeError("model provider response did not contain a 'message' field.")
            if "content" not in data["message"]:
                raise RuntimeError("model provider response message did not contain a 'content' field.")
        
            return data["message"]["content"]

        except requests.exceptions.ConnectionError:
            raise RuntimeError("Could not connect to model provider. Make sure model provider is running locally.")

        except requests.exceptions.Timeout:
            raise RuntimeError("model provider request timed out. The model may be too slow or not loaded.")

        except requests.exceptions.RequestException as error:
            raise RuntimeError(f"model provider request failed: {error}")

        except ValueError:
            raise RuntimeError("model provider returned an invalid JSON response.")



""" The CodeReviewer class uses the OllamaClient to review code according to a set of rules defined in REVIEW_RULES. 
It processes the code and returns the results for each rule. """

class CodeReviewer:
    def __init__(self, llm_client: OllamaClient, rules: list[ReviewRule] = REVIEW_RULES):
        self.llm_client = llm_client
        self.rules = rules

    def review_code(self, code: str) -> dict[str, Any]:
        ###Run all review rules on the given Python code. Returns only rule_id and true/false result for each rule."""
        final_results = []

        for rule in self.rules:
            prompt = rule.build_prompt(code)

            try:
                model_response_text = self.llm_client.ask(prompt)
                parsed_response = self._parse_model_response(model_response_text)

                rule_result = {
                    "rule_id": rule.rule_id,
                    "passed": parsed_response["passed"],
                }

            except Exception:
                rule_result = {
                    "rule_id": rule.rule_id,
                    "passed": False,
                }

            final_results.append(rule_result)

        return {
            "checked_rules": final_results
        }

    def _parse_model_response(self, response_text: str) -> dict[str, Any]:
       
        ##Parse the LLM response as JSON.
        cleaned_response = response_text.strip()

        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response.removeprefix("```json").strip()

        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response.removeprefix("```").strip()

        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response.removesuffix("```").strip()

        try:
            parsed = json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError("Model response is not valid JSON.")

        if not isinstance(parsed, dict):
            raise ValueError("Model response must be a JSON object.")

        if "passed" not in parsed:
            raise ValueError("Model response is missing 'passed' field.")

        if not isinstance(parsed["passed"], bool):
            raise ValueError("'passed' field must be true or false.")

        return parsed