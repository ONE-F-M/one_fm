import openai
import os
import pandas as pd
import time
import requests
import frappe

API_KEY = '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'
API_ENDPOINT = 'https://api.openai.com/v1/chat/completions'

@frappe.whitelist()
def get_completion(prompt):
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }

        data = {
            'messages': [{'role': 'system', 'content': 'You are a helpful assistant.'},
                        {'role': 'user', 'content': prompt}],
        }

        response = requests.post(API_ENDPOINT, headers=headers, json=data)
        response_json = response.json()

        if response_json:
            return response_json['choices'][0]['message']['content']
        else:
            return None
    except:
        return None