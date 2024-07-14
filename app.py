# -*- coding: utf-8 -*-
"""Untitled1.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1M16lwmZPRUW-bnREGom1o-1P5QQnOeIr
"""

import os
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from transformers import AutoTokenizer, AutoModel
from langchain.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from dotenv import load_dotenv

text = ""

def main():
    st.set_page_config(page_title="Healthcare Assistant", page_icon=":book:")

    # Load the .env file
    load_dotenv()
    api_key = os.getenv("GROK_API_KEY")
    if api_key:
        st.session_state.api_key = api_key

    # Initialize the session state for questions if it doesn't exist
    if 'questions' not in st.session_state:
        st.session_state.questions = []

    # Function to add a new question from the input field
    def add_question():
        new_question = st.session_state.new_question
        if new_question:
            st.session_state.questions.append(new_question)
            st.session_state.new_question = ""  # Clear the input field

    # Function to remove a question
    def remove_question(index):
        st.session_state.questions.pop(index)

    st.image("logo.jpeg", width=200)
    # Display a header
    st.header("Enter Your Question")

    # Input field for the new question
    st.text_input("Enter a new question:", key='new_question')

    st.sidebar.header("Healthcare Research Assistant")

    pdf = st.sidebar.file_uploader("Choose a file", type="pdf")

    if pdf is not None:
        pdf_reader = PdfReader(pdf)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()

    if "api_key" in st.session_state:
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=500,
            chunk_overlap=100,
            length_function=len,
        )
        try:
            chunks = text_splitter.split_text(text)

            # Initialize Hugging Face embeddings
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name)

            embeddings = lambda texts: [
                model(tokenizer(text, return_tensors='pt')['input_ids']).last_hidden_state.mean(dim=1).detach().numpy()
                for text in texts
            ]
            vectorstore = FAISS.from_texts(chunks, embeddings)

        except Exception as e:
            st.sidebar.error(f"Error: {str(e)}")

        user_question = st.sidebar.button("Submit")

        if user_question:
            retriever = vectorstore.as_retriever()

            template = """
            You are a helpful healthcare PDF assistant.
            Given the following PDF, answer the question based on the context.
            If you don't know the answer, just say that you don't know.
            You may suggest non-critical healthcare issues even if the context is not in the PDF.
            Never prescribe medications or become a substitute for a doctor.
            Do not make up an answer if you don't know about it.

            Question: {question}
            Context: {context}

            Answer:
            """

            prompt = ChatPromptTemplate.from_template(template)

            rag_chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | prompt
                | model
                | StrOutputParser()
            )

            question = st.session_state.new_question

            try:
                answer = rag_chain.invoke(question)
                st.write(answer)
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()