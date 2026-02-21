import requests
import streamlit as st
import json
import time
from assets.data import data_to_optimize
from utils.markdown_to_html import markdown_to_html
from utils.highlight_diff import highlight_additions
from utils.comment_to_html import comment_to_html


tab1, tab2, tab3, tab4 = st.tabs(["Web Crawl", "Suggestion", "Preview", "Insight"])

#### 1 : crawl URL ####

API_URL_crawl = "http://127.0.0.1:8000/crawl"

if "status_crawl" not in st.session_state:
    st.session_state.status_crawl = 0

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
            with st.spinner("Exploring the URL... this may take 15-30 seconds."):
                response_crawler = requests.post(API_URL_crawl, json=payload_crawl_url)
            

            if response_crawler.status_code == 200:
                st.session_state.status_crawl = 200
                st.success("Url crawlped", icon="✅")

                st.session_state.crawl_url = response_crawler.json()

                st.write("### API response:")
                st.json(response_crawler.json())


            else:
                st.error("Error sending data to API")

        except Exception as e:
            st.error(f"Connection error: {e}")
        

#### Generate itw

if "suggestion" not in st.session_state : 
    st.session_state.suggestion = {}

if "status_suggestion" not in st.session_state:
    st.session_state.status_suggestion = 0

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
                response_seo = requests.post(API_URL_SUGGESTION, json=payload_suggestion)

            if response_seo.status_code == 200:
                st.session_state.status_suggestion = 200
                st.success(f"Suggestions generated!")
                st.session_state.suggestion = response_seo.json()
                st.write("### API response:")
                st.json(response_seo.json())
            else:
                st.error("Error sending data to API")

        except Exception as e:
            st.error(f"Connection error: {e}")

if "optimized" not in st.session_state : 
    st.session_state.optimized = "" 

with tab3 : 

    if st.session_state.status_crawl == 200 and st.session_state.status_suggestion == 200 :
        optimized = st.session_state.suggestion.get("company", {})
        original_markdown = st.session_state.crawl_url["info_website"].get("markdown_content", "")
        new_markdown = optimized.get("markdown_content", "")
        metadata = optimized.get("metadata", {})
        title = metadata.get("title", "Preview")
        description = metadata.get("description", "")
        st.session_state.preview = 200

        st.write("### 🌐 Website Preview")
        left, right = st.columns(2)

        with left:
            st.write("#### ⬅️ Before")
            st.components.v1.html(
                markdown_to_html(original_markdown, title="Original Version", is_new=False),
                height=600, scrolling=True
                )

        with right:

            st.write("#### ➡️ After — SEO Optimized")
            st.components.v1.html(markdown_to_html(new_markdown, title=title, description=description, is_new=True),height=600, scrolling=True)
            
    else : 
        st.warning("Missing information, visit previous sections.")

with tab4 : 

    if st.session_state.preview == 200 and "comment" in optimized : 
        st.write("---")
        st.write("### 💡 SEO Analysis")
        st.components.v1.html(
            comment_to_html(optimized["comment"]),
            height=800,
            scrolling=True
        )
         
    else : 
        st.warning("Missing information, visit previous sections.")

