import operator
from typing import TypedDict, Annotated, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from src.sandbox import PythonSandbox
import os

# 1. State Definition
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    csv_path: str
    sandbox: PythonSandbox
    current_code: str
    retry_count: int

# 2. Model Setup
api_key = os.environ.get("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key, temperature=0)

# 3. Nodes
def reasoner_node(state: AgentState):
    messages = state["messages"]
    csv_path = state["csv_path"]
    
    # --- UPDATED SYSTEM PROMPT ---
    # We explicitly ask for .to_markdown() to fix the table display issue
    system_prompt = SystemMessage(content=f"""
    You are an expert Python Data Scientist. You have a pandas DataFrame named 'df' loaded from '{csv_path}'.
    Your goal is to write Python code to answer the user's question.
    
    IMPORTANT GUIDELINES:
    1. **Visualizations:** Use 'plt.savefig("output_plot.png")'. Clear the plot with 'plt.clf()' before creating a new one.
    2. **Tables:** If you print a DataFrame, ALWAYS use `print(df.head().to_markdown(index=False, numalign="left", stralign="left"))`. Never use standard print(df).
    3. **Text:** Use 'print()' for text answers.
    4. **No Loading:** 'df' is ALREADY LOADED. Do not load it again.
    5. **Formatting:** Wrap code in ```python ... ``` blocks.
    """)
    
    if state.get("retry_count", 0) > 0:
        messages.append(HumanMessage(content="The previous code failed. Please rewrite it to fix the error."))

    response = llm.invoke([system_prompt] + messages)
    
    content = response.content
    if "```python" in content:
        code_block = content.split("```python")[1].split("```")[0].strip()
    else:
        code_block = content 
    
    return {"current_code": code_block, "messages": [response]}

def executor_node(state: AgentState):
    sandbox = state["sandbox"]
    code = state["current_code"]
    result = sandbox.execute(code)
    
    if result["success"]:
        return {"messages": [HumanMessage(content=f"Output:\n{result['output']}")], "retry_count": 0}
    else:
        return {"messages": [HumanMessage(content=f"Error: {result['error']}")], "retry_count": state["retry_count"] + 1}

# 4. Logic
def should_continue(state: AgentState):
    last_msg = state["messages"][-1].content
    if "Error:" in last_msg and state["retry_count"] < 3:
        return "reasoner"
    return "end"

# 5. Graph
workflow = StateGraph(AgentState)
workflow.add_node("reasoner", reasoner_node)
workflow.add_node("executor", executor_node)
workflow.set_entry_point("reasoner")
workflow.add_edge("reasoner", "executor")
workflow.add_conditional_edges("executor", should_continue, {"reasoner": "reasoner", "end": END})

data_agent_app = workflow.compile()