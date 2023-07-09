import os
import json

import frappe
from gpt_index import SimpleDirectoryReader, GPTListIndex, GPTSimpleVectorIndex, LLMPredictor, PromptHelper
from langchain import OpenAI

from one_fm.api.v1.utils import response


the_conf = frappe.conf
print(the_conf, "\n\n\n\n\n\n\n\n\n")
# API_KEY = the_conf.CHATGPT_APIKEY    
# os.environ["OPENAI_API_KEY"] = frappe.client.get_password("API Integration", "ChatGPT", "api_key")
# os.environ["OPENAI_API_KEY"] = API_KEY

# param_name = frappe.db.get_value("API Parameter", {"parent": "ChatGPT", "parameter": "Folder Path"}, ["name"])

# folder_path = frappe.client.get_password("API Parameter", param_name, "value") if param_name else ""

folder_path = frappe.conf.get("CHATGPT_FOLDER_PATH", None)
print(folder_path, "\n\n\n\n\n\n\n\n")

def create_vector_index(path: str = folder_path):
    try:
        max_input = 4096
        tokens = 256
        chunk_size = 600
        max_chunk_overlap = 0.5
        prompt_helper = PromptHelper(max_input, tokens, max_chunk_overlap, chunk_size_limit=chunk_size)
        llm_predictor = LLMPredictor(OpenAI(temperature=0.5, model_name="text-ada-001", max_tokens=tokens))
        docs = SimpleDirectoryReader(path).load_data()
        vector_index = GPTSimpleVectorIndex(documents=docs, llm_predictor=llm_predictor, prompt_helper=prompt_helper)
        vector_index.save_to_disk("vector_index.json")
        return vector_index
    except:
        frappe.log_error(frappe.get_traceback(), "Error while adding to bot memory(Chat-BOT)")


@frappe.whitelist()
def ask_question(question: str = None):
    try:
        if not question:
            return response("Bad Request !", 400, error="Question can not be empty")
        index = GPTSimpleVectorIndex.load_from_disk("vector_index.json")
        answer = index.query(question)
        return response(message="Success", status_code=200, data={"question": question, "answer": answer.response})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error while generating answer(Chat-BOT)")
        return response(e, 500, {}, False, )


@frappe.whitelist()
def queue_fetch_wiki_and_add_to_bot_memory():
    frappe.enqueue(fetch_wiki_and_add_to_bot_memory, queue='long')


def fetch_wiki_and_add_to_bot_memory():
    try:
        wiki_page_list = frappe.db.get_list("Wiki Page", fields=["name", "content", "title"])
        wiki_page_dict = {item["name"]: item["title"] + "\n" + item["content"] for item in wiki_page_list}
        for k, v in wiki_page_dict.items():
            with open(f"{folder_path}{k}.txt", "w") as x:
                x.write(v)

        create_vector_index(path=folder_path)

        queue_delete_all_uploaded_files()

        return "Done"
    except:
        frappe.log_error(frappe.get_traceback(), "Error while adding to bot memory")
        return "Failed"


def after_insert_wiki_page(doc, method):
    frappe.enqueue(add_wiki_page_to_bot_memory, doc=doc, queue='long')


@frappe.whitelist()
def add_wiki_page_to_bot_memory(doc):
    try:
        doc = json.loads(doc)
        with open(f"{folder_path}{doc.get('name')}.txt", "w") as x:
            x.write(doc.get("title") + "\n" + doc.get("content"))

        create_vector_index(path=folder_path)

        queue_delete_all_uploaded_files()
        return True
    except Exception as e:
        print(e)
        frappe.log_error(frappe.get_traceback(), "Error while adding to bot memory")
        return False


def queue_delete_all_uploaded_files():
    frappe.enqueue(delete_all_uploaded_files, queue='long')


def delete_all_uploaded_files():
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
