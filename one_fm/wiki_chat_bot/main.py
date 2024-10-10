import os
import json

import frappe
from llama_index.core import SimpleDirectoryReader,VectorStoreIndex,PromptTemplate,GPTListIndex,StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.schema import TextNode
from langchain.text_splitter import RecursiveCharacterTextSplitter


from one_fm.api.v1.utils import response

def split_text_into_chunks(text, chunk_size=4096):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=200)
    return splitter.split_text(text)

def create_vector_index():
    try:
        os.environ["OPENAI_API_KEY"] = frappe.local.conf.CHATGPT_APIKEY
        existing_text_nodes,new_text_nodes = [],[]
        embedding_model = OpenAIEmbedding(model_name="gpt-4o-mini")
        # Load existing data and append to nodelist
        existing_docs = SimpleDirectoryReader("vector_index").load_data()
        # existing_text_nodes = [TextNode(text=doc.text) for doc in existing_docs]
        for doc in existing_docs:
            chunks = split_text_into_chunks(doc.text)
            existing_text_nodes.extend([TextNode(text=chunk) for chunk in chunks])

        # Load new data
        new_docs = SimpleDirectoryReader(get_folder_path()).load_data()
        # new_text_nodes = [TextNode(text=doc.text) for doc in new_docs]
        for doc in new_docs:
            #Split the texts so we don't go over the max token value of the model
            chunks = split_text_into_chunks(doc.text)
            new_text_nodes.extend([TextNode(text=chunk) for chunk in chunks])
        # Merge existing and new vector indexes
        merged_nodes = existing_text_nodes+new_text_nodes
        merged_vector_index = VectorStoreIndex(nodes= merged_nodes,embedding =embedding_model)
    
        # Persist the merged vector index
        merged_vector_index.storage_context.persist(persist_dir="vector_index")

        return merged_vector_index
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
            "always respond in the same language as the query "
            "Query: {query_str}\n"
            "Answer: "
        )
        refine_prompt_str = (
            "We have the opportunity to refine the original answer "
            "(only if needed) with some more context below.\n"
            "------------\n"
            "If you did not respond to the question in the same language it was asked,translate your answer to the same language.\n"
            "lumina ALWAYS responds to users in the same language as the question\n"
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
def queue_fetch_wiki_and_add_to_bot_memory():
    frappe.enqueue(fetch_wiki_and_add_to_bot_memory, queue='long', at_front=True, is_async=True)


def fetch_wiki_and_add_to_bot_memory():
    try:
        folder_path = get_folder_path()
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
            
        folder_path = get_folder_path()
        
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


def queue_delete_all_uploaded_files():
    frappe.enqueue(delete_all_uploaded_files, queue='long', at_front=True, is_async=True)


def delete_all_uploaded_files():
    try:
        folder_path = get_folder_path()
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except:
        frappe.log_error(frappe.get_traceback(), "Error while deleting files CHATBOT")


def get_folder_path():
    if frappe.local.conf.CHATGPT_FOLDER_NAME:
        return os.path.join(os.path.abspath(frappe.get_site_path('private')), frappe.local.conf.CHATGPT_FOLDER_NAME)
    return None