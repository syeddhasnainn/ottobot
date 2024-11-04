import httpx
from together import Together
from dotenv import load_dotenv
import os
import json
import openai
from curl_cffi import requests
from parsel import Selector
import html2text
import os
import subprocess

load_dotenv()
client = openai.OpenAI(
    base_url="https://api.together.xyz/v1",
    api_key=os.environ['TOGETHER_API_KEY'],
)


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_web_results",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": [
                            "celsius",
                            "fahrenheit"
                        ]
                    }
                }
            }
        }
    }
]


def get_headers():
    headers = {
        'authority': 'iapps.courts.state.ny.us',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    return headers


def parse_search_results(selector: Selector):
    """parse search results from google search page"""
    h = html2text.HTML2Text()
    h.ignore_images = True
    h.ignore_links = True
    
    results = []
    for box in selector.xpath("//h1[contains(text(),'Search Results')]/following-sibling::div[1]/div"):
        title = box.xpath(".//h3/text()").get()
        url = box.xpath(".//h3/../@href").get()

        if not url:
            continue
        results.append({"title": title, "url": url})


    temp = custom_search(results[0]['url'])
    resp = h.handle(temp)
    return resp

def custom_search(url):
    return requests.get(url, headers=get_headers(), impersonate='chrome110').text

def get_web_results(location, unit="celsius"):

    url = f'https://www.google.com/search?q=weather+in+{location}'
    response = custom_search(url)
    selector = Selector(response)
    return parse_search_results(selector)


def chat():
    messages = [
        {"role": "system", "content": "You are a helpful assistant that can access external functions. The responses from these function calls will be appended to this dialogue. Please provide responses based on the information from these function calls."},
        {"role": "user", "content": "What is the current temperature of Karachi?"}
    ]

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    tool_calls = response.choices[0].message.model_dump()['tool_calls']
    print(tool_calls)
    for tool_call in tool_calls:
        function_name = tool_call['function']['name']
        if function_name == 'get_web_results':
            function_response = get_web_results(
                **json.loads(tool_call['function']['arguments']))
            messages.append({
                "tool_call_id": tool_call['id'],
                "content": function_response,
                "name": function_name,
                "role": "tool"
            })
    function_enriched_response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        messages=messages,
    )
    print(json.dumps(function_enriched_response.choices[0].message.model_dump(), indent=2))


if __name__ == "__main__":
    chat()
