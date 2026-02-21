import requests
import streamlit as st
import json
import time
from assets.data import data_to_optimize


tab1, tab2 = st.tabs(["Web Crawl", "Suggestion"])

#### 1 : crawl URL ####

API_URL_crawl = "http://127.0.0.1:8000/crawl"

if "url" not in st.session_state:
    st.session_state.url = ""

if "crawl_url" not in st.session_state:
    st.session_state.crawl_url = ""


with tab1 :
    
    st.title("Url")
    url = st.text_input("🏢 Fill the url of your website.") 
    company_type = st.selectbox( "Field",["Finance", "Law", "Gym", "Other"])

    if url:

        st.session_state.url = url

        payload_crawl_url = {
            "url": st.session_state.url,
            }

        try:
            with st.spinner("Exploring the URL... this may take a minute."):
                response = requests.post(API_URL_crawl, json=payload_crawl_url)
            

            if response.status_code == 200:
                st.success("Url crawlped", icon="✅")

                st.session_state.crawl_url = response.json()

                st.write("### API response:")
                st.json(response.json())


            else:
                st.error("Error sending data to API")

        except Exception as e:
            st.error(f"Connection error: {e}")
        

#### Generate itw

if "suggestion" not in st.session_state : 
    st.session_state.suggestion = {}

API_URL_SUGGESTION = "http://127.0.0.1:8000/suggestion"

with tab2 :

    st.title("Suggestion from Claude.")

    button_for_suggestion = st.button(f"Improve '{url}' SEO.")
    

    if button_for_suggestion :

        if st.session_state.crawl_url == {}:
            payload_suggestion = {
                "extracted_from_url": data_to_optimize , #st.session_state.crawl_url this is the command after the first page works
                }
        else : 
            payload_suggestion = {
                "extracted_from_url": st.session_state.crawl_url["info_website"] , 
                }

        try:

            with st.spinner("Generating SEO suggestions... this may take a minute."):
                response = requests.post(API_URL_SUGGESTION, json=payload_suggestion)

            if response.status_code == 200:
                st.success(f"Suggestions generated!")
                st.session_state.suggestion = response.json()
                st.write("### API response:")
                st.json(response.json())
            else:
                st.error("Error sending data to API")

        except Exception as e:
            st.error(f"Connection error: {e}")