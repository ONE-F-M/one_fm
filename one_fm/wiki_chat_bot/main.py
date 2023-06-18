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


import frappe

from gpt_index import SimpleDirectoryReader, GPTListIndex, GPTSimpleVectorIndex, LLMPredictor, PromptHelper
from langchain import OpenAI

import os

os.environ["OPENAI_API_KEY"] = frappe.local.conf.get("OPENAI_API_KEY")


def create_vector_index(path: str):
    max_input = 4096
    tokens = 256
    chunk_size = 600
    max_chunk_overlap = 0.5
    prompt_helper = PromptHelper(max_input, tokens, max_chunk_overlap, chunk_size_limit=chunk_size)
    llm_predictor = LLMPredictor(OpenAI(temperature=0.5, model_name="text-ada-001", max_tokens=tokens))
    docs = SimpleDirectoryReader(path).load_data()
    vector_index = GPTSimpleVectorIndex(documents=docs, llm_predictor=llm_predictor, prompt_helper=prompt_helper)
    vector_index.save_to_disk("vector_index.json")
    print(vector_index)
    return vector_index
