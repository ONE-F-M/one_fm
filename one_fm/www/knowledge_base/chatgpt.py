import openai
import os
import pandas as pd
import time
import requests
import frappe

@frappe.whitelist()
def get_completion(prompt):
    try:
        default_api_integration = frappe.get_doc("Default API Integration")

        chatgpt = frappe.get_doc("API Integration",
            [i for i in default_api_integration.integration_setting
                if i.app_name=='ChatGPT'][0].app_name)
        openai.api_key = chatgpt.get_password('api_key')

        completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                )

        response = completion.choices[0].message.content

        if response:
            return response
        else:
            return None
    except:
        return None