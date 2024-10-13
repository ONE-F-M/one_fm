import os
import json
from langdetect import detect
import shutil
from deep_translator import GoogleTranslator

import frappe
from llama_index.core import SimpleDirectoryReader,PromptHelper,VectorStoreIndex,PromptTemplate

from llama_index.llms.openai import OpenAI

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import StorageContext, load_index_from_storage

from one_fm.docsagent.docs_agent.preprocess.files_to_plain_text import process_all_products as chunk
from one_fm.docsagent.docs_agent.preprocess.populate_vector_database import process_all_products as populate
from one_fm.docsagent.docs_agent.utilities.config import return_config_and_product
from one_fm.docsagent.docs_agent.agents.docs_agent import DocsAgent
import typing


from one_fm.api.v1.utils import response
        
def create_vector_index():
    try:
        os.environ["OPENAI_API_KEY"] = frappe.local.conf.CHATGPT_APIKEY   
        docs = SimpleDirectoryReader(get_folder_path("chatgpt")).load_data()
        embedding_model = OpenAIEmbedding(model_name="gpt-4o-mini")
        vector_index = VectorStoreIndex.from_documents(docs,embedding=embedding_model)
        vector_index.storage_context.persist(persist_dir="vector_index")
        return vector_index
    except:
        frappe.log_error(frappe.get_traceback(), "Error while adding to bot memory(Chat-BOT)")


@frappe.whitelist()
def ask_question(question: str = None):
    try:
        os.environ["OPENAI_API_KEY"] = frappe.local.conf.CHATGPT_APIKEY
        if not question:
            return response("Bad Request !", 400, error="Question can not be empty")
        storage_context = StorageContext.from_defaults(persist_dir="vector_index")
        index = load_index_from_storage(storage_context)
        prompt_template_str = (
           "Context information is below.\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "Given the context information and not prior knowledge, "
            "You do not need to introduce yourself or say who you are when you are not asked directly\n"
            "You are an AI assistant called Lumina.\n"
            "You Work for One Faciities Management, A company with it's Headquarters in Kuwait\n"
            "Whenever Lumina does not find the required data,ask the user to upload the most updated data to enable you answer the question appropriately\n"
            "Respond to the user in the same language they use"
            "Query: {query_str}\n"
            "Answer: "
        )
        refine_prompt_str = (
            "We have the opportunity to refine the original answer "
            "(only if needed) with some more context below.\n"
            "------------\n"
            "If you did not respond to the question  in the same language it was asked,translate your answer to the same language as the question unless the preferred languaged was specified in the query\n"
            "------------\n"
            "Given the new context, refine the original answer to better "
            "answer the question: {query_str}. "
            
            "Original Answer: {existing_answer}"
        )
        text_qa_template = PromptTemplate(prompt_template_str)
        refined_text_qa_template = PromptTemplate(refine_prompt_str)
        llm = OpenAI(model="gpt-4o-mini")
        query_engine = index.as_query_engine(llm=llm,text_qa_template=text_qa_template,refine_template=refined_text_qa_template)
        answer = query_engine.query(question)
        return response(message="Success", status_code=200, data={"question": question, "answer": answer.response})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error while generating answer(Chat-BOT)")
        return response(e, 500, {}, False, )


@frappe.whitelist()
def ask_question_with_gemini(question: str = None):
    try:
        cwd = os.getcwd()
        config_file = os.path.join(cwd, '..','apps', 'one_fm', 'one_fm', 'docsagent', 'config.yaml')
        new_condition = f"Read the context below and answer the question at the end:"
        new_question = f"Can you think of 5 questions whose answers can be found in the context above?"
        if detect(question) != 'en':
            new_condition = GoogleTranslator(source='en', target=detect(question)).translate(new_condition)
            new_question = GoogleTranslator(source='en', target=detect(question)).translate(new_question)
        loaded_config, product_config = return_config_and_product(config_file=config_file)
        try:
            docs_agent = DocsAgent(config= product_config.products[0], init_chroma=True)
            (answers, final_context) = docs_agent.ask_aqa_model_using_local_vector_store(question=question,results_num=1,)
        except:
            docs_agent = DocsAgent(
                config= product_config.products[0], init_chroma=False, init_semantic=False
            )
            (answers,final_context) = docs_agent.ask_content_model_with_context_prompt(context="",question=question,prompt="",model="models/aqa",)
            final_context = ""
        (related_questions,new_prompt_questions,) = docs_agent.ask_content_model_with_context_prompt(context=final_context,question=new_question,prompt=new_condition,model="models/aqa",)
        answer = answers + "\n\n" + related_questions
        return response(message="Success", status_code=200, data={"question": question,"answer":answer})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error while generating answer(Chat-BOT)")
        return response(e, 500, {}, False, )

@frappe.whitelist()
def queue_fetch_wiki_and_add_to_bot_memory():
    frappe.enqueue(fetch_wiki_and_add_to_bot_memory, queue='long', at_front=True, is_async=True)


def fetch_wiki_and_add_to_bot_memory():
    try:
        folder_path = get_folder_path("chatgpt")
        wiki_page_list = frappe.db.get_list("Wiki Page", fields=["name", "content", "title"])
        wiki_page_dict = {item["name"]: item["title"] + "\n" + item["content"] for item in wiki_page_list}
        for k, v in wiki_page_dict.items():
            with open(f"{folder_path}/{k}.txt", "w") as x:
                x.write(v)

        create_vector_index()

        queue_delete_all_uploaded_files()

        return "Done"
    except:
        frappe.log_error(frappe.get_traceback(), "Error while adding to bot memory")
        return "Failed"


def after_insert_wiki_page(doc, method):
    frappe.enqueue(add_wiki_page_to_bot_memory, doc=doc, queue='long', at_front=True, is_async=True)


@frappe.whitelist()
def add_wiki_page_to_bot_memory(doc):
    try:
        if isinstance(doc, str):
            doc = json.loads(doc)
            
        folder_path = get_folder_path("chatgpt")
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        with open(f"{folder_path}/{doc.get('name')}.txt", "w") as x:
            x.write(doc.get("title") + "\n" + doc.get("content"))
        
        create_vector_index()

        queue_delete_all_uploaded_files()
        return True
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error while adding to bot memory")
        return False

@frappe.whitelist()
def add_wiki_page_to_bot_memory_by_gemini(doc):
    try:
        if isinstance(doc, str):
            doc = json.loads(doc)
        folder_path = get_folder_path("gemini")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        markdown_content = f"{doc['title']}\n\n"
        markdown_content += f"{doc['route']}\n\n"
        markdown_content += f"{doc['content']}\n\n"
        output_file_path = folder_path+"/"+doc['title']+".md"
        with open(output_file_path, "w") as file:
            file.write(markdown_content)
        chunk()
        populate()
        queue_delete_all_uploaded_files("gemini")
        return True
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error while adding to bot memory")
        return False


def queue_delete_all_uploaded_files(chatbot):
    frappe.enqueue(delete_all_uploaded_files(chatbot=chatbot), queue='long', at_front=True, is_async=True)


def delete_all_uploaded_files(chatbot):
    try:
        folder_path = get_folder_path(chatbot)
        if chatbot == "gemini":
            data_path = str(folder_path)
            path = data_path.replace("content","data")
            file_path = os.path.join(path)
            if os.path.exists(file_path):
                shutil.rmtree(file_path)
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except:
        frappe.log_error(frappe.get_traceback(), "Error while deleting files CHATBOT")


def get_folder_path(chatbot):
    if frappe.local.conf.gemini_folder_name and chatbot== "gemini":
        return os.path.join(os.path.abspath(frappe.get_site_path('private')), frappe.local.conf.gemini_folder_name)
    elif frappe.local.conf.CHATGPT_FOLDER_NAME and chatbot== "chatgpt":
        return os.path.join(os.path.abspath(frappe.get_site_path('private')), frappe.local.conf.CHATGPT_FOLDER_NAME)
    return None