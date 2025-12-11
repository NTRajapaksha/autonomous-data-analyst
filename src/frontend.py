import sys
import os
import streamlit as st
import pandas as pd
from src.data_agent import data_agent_app
from src.sandbox import PythonSandbox
from langchain_core.messages import HumanMessage

# Add root path to find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

st.set_page_config(page_title="Autonomous Data Analyst", layout="wide", page_icon="📊")

# --- Custom CSS for better look ---
st.markdown("""
<style>
    .stChatInput {position: fixed; bottom: 0; width: 100%;}
    .block-container {padding-bottom: 100px;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Autonomous Data Analyst")
st.markdown("Upload a CSV and ask complex questions. I write my own code to answer you.")

# --- Sidebar ---
with st.sidebar:
    st.header("📂 Data Source")
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

# --- Session State Init ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "sandbox" not in st.session_state:
    st.session_state.sandbox = PythonSandbox()

# --- Logic ---
if uploaded_file:
    # Save and Load
    file_path = f"temp_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Load into Sandbox (Only once to save resources)
    if "current_file" not in st.session_state or st.session_state.current_file != uploaded_file.name:
        msg = st.session_state.sandbox.load_data(file_path)
        st.session_state.current_file = uploaded_file.name
        st.toast(msg, icon="✅")

    # Sidebar Data Preview
    df = pd.read_csv(file_path)
    with st.sidebar.expander("🔎 Data Preview"):
        st.dataframe(df.head())
        st.caption(f"Shape: {df.shape}")
        st.caption(f"Columns: {', '.join(df.columns)}")

    # --- Suggested Questions (Quick Actions) ---
    col1, col2, col3 = st.columns(3)
    prompt = None
    
    if col1.button("👀 Overview"):
        prompt = "Show me the first 5 rows and describe the columns."
    if col2.button("📈 Missing Values"):
        prompt = "Check for missing values and show them in a table."
    if col3.button("📊 Correlation"):
        prompt = "Show the correlation matrix for numeric columns."

    # --- Chat Interface ---
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "image" in msg:
                st.image(msg["image"])

    # Handle User Input (either from button or text box)
    user_input = st.chat_input("Ask about your data (e.g., 'Plot the distribution of X')")
    
    if user_input:
        prompt = user_input

    if prompt:
        # User Message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Agent Response
        with st.chat_message("assistant"):
            with st.spinner("🤖 Writing Python code..."):
                try:
                    inputs = {
                        "messages": [HumanMessage(content=prompt)],
                        "csv_path": file_path,
                        "sandbox": st.session_state.sandbox,
                        "retry_count": 0
                    }
                    
                    final_state = data_agent_app.invoke(inputs)
                    final_msg = final_state["messages"][-1].content
                    
                    # Display Text
                    st.markdown(final_msg)
                    response_data = {"role": "assistant", "content": final_msg}

                    # Display Plot if generated
                    if os.path.exists("output_plot.png"):
                        st.image("output_plot.png")
                        new_name = f"plot_{len(st.session_state.chat_history)}.png"
                        os.rename("output_plot.png", new_name)
                        response_data["image"] = new_name
                    
                    st.session_state.chat_history.append(response_data)
                    
                except Exception as e:
                    st.error(f"An error occurred: {e}")

else:
    st.info("👆 Please upload a CSV file in the sidebar to get started.")