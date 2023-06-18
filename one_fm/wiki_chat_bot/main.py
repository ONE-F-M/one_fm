# import os
#
#
# import frappe
# from llama_index import SimpleDirectoryReader, GPTListIndex, LLMPredictor, PromptHelper, GPTVectorStoreIndex
# from langchain.agents import initialize_agent, Tool
# from langchain.llms import OpenAI
# from langchain.chains.conversation.memory import ConversationBufferMemory
#
# api_key = frappe.local.conf.get("OPENAI_API_KEY")
#
# os.environ["OPENAI_API_KEY"] = api_key
#
#
# def create_vector_index(path: str):
#     max_input = 4096
#     tokens = 256
#     chunk_size = 600
#     max_chunk_overlap = 0.5
#     prompt_helper = PromptHelper(max_input, tokens, max_chunk_overlap, chunk_size_limit=chunk_size)
#     llm_predictor = LLMPredictor(OpenAI(temperature=0.5, model_name="text-ada-001", max_tokens=tokens))
#     docs = SimpleDirectoryReader(path, recursive=True, exclude_hidden=True).load_data()
#     vector_index = GPTVectorStoreIndex.from_documents(docs)
#     print(type(vector_index))
#
#     from pickle import dump
#     vector_index.core_bpe = None
#     with open("vector_index.pkl", "wb") as f:
#         dump(vector_index, f)
#
#     return vector_index

import os

import frappe
from gpt_index import SimpleDirectoryReader, GPTListIndex, GPTSimpleVectorIndex, LLMPredictor, PromptHelper
from langchain import OpenAI

from one_fm.api.v1.utils import response

os.environ["OPENAI_API_KEY"] = frappe.local.conf.get("OPENAI_API_KEY")
folder_path = "../apps/one_fm/one_fm/wiki_chat_bot/knowledge/"


def create_vector_index(path: str):
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
        # last_token_usage = index.llm_predictor.last_token_usage
        # print(last_token_usage)
        answer = index.query(question)
        return response(message="Success", status_code=200, data={"answer": answer})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error while generating answer(Chat-BOT)")
        return response(e, 500, {}, False, )


def fetch_wiki_and_add_to_bot_memory():
    try:
        wiki_page_list = frappe.db.get_list("Wiki Page", fields=["name", "content"])
        wiki_page_dict = {item["name"]: item["content"] for item in wiki_page_list}
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


def add_wiki_page_to_bot_memory(doc):
    with open(f"{folder_path}{doc.name}.txt", "w") as x:
        x.write(doc.content)

    create_vector_index(path=folder_path)

    queue_delete_all_uploaded_files()


def queue_delete_all_uploaded_files():
    frappe.enqueue(delete_all_uploaded_files, queue='long')


def delete_all_uploaded_files():
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
