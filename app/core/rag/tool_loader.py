import chromadb
import os
from app.utils.prompts import QUERY_ENGINE_PROMPT
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore


collection_dict = {
    "kfc":{
        "collection_name": "Kenya Film Commission",
        "collection_description": "Kenya Film Commission is a government agency responsible for promoting and facilitating the growth of the film industry in Kenya. It provides support to filmmakers, promotes Kenya as a filming destination, and works to develop local talent and infrastructure.",
    }
}

remote_db = chromadb.HttpClient(
    host="localhost",
    port=8050
)


retrievers = []
for collection_name, entry  in collection_dict.items():
    collection = remote_db.get_or_create_collection(
        name=collection_name
    )
    prompt = QUERY_ENGINE_PROMPT.format(
        collection_name=entry["collection_name"],
        collection_description=entry["collection_description"]
    )

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store,
    )
    
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
    )
    retriever = index.as_retriever()

    retrievers.append(retriever.aretrieve) 
