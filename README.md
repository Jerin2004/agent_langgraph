# Restaurant Order Management AI Agent (LangGraph)

An intelligent restaurant order processing agent built with **LangGraph**, **LangChain**, and **Python**.

## System Architecture

```mermaid
flowchart TD
    START([User Input]) --> intake[order_intake]
    
    intake -->|Unrelated query| rejected[Reject & Prompt: Food Only] --> END_NODE([End])
    intake -->|Food order| confirmed_node[order_confirmed]
    
    confirmed_node --> decision_node[order_decision]
    
    decision_node -->|Available (confirmed)| cook[cook]
    decision_node -->|Partial / Unavailable| wait_user[Prompt User / Wait]
    
    wait_user --> user_decision[handle_user_decision]
    user_decision -->|Accept partial| cook
    user_decision -->|New order (Retry -1)| confirmed_node
    user_decision -->|Cancel / Retries exhausted| apology[apology] --> END_NODE
    
    cook --> cook_check[cook_decision]
    cook_check -->|Cook Success (60%)| serve[serve]
    cook_check -->|Cook Fail (40%) & Retries > 0| cook
    cook_check -->|Cook Fail & Retries = 0| apology
    
    serve --> serve_check[serve_decision]
    serve_check -->|Serve Success| complete[order_complete] --> END_NODE
    serve_check -->|Serve Fail & Serve/Cook Retries > 0| cook
    serve_check -->|Serve Fail & Retries = 0| apology
```

---

## State Schema (`OrderState`)

| Field | Type | Description |
|---|---|---|
| `messages` | `Annotated[Sequence[BaseMessage], add_messages]` | Conversation history between user and LLM |
| `dish_name` | `Optional[str]` | Extracted dish name |
| `required_quantity` | `Optional[int]` | Desired quantity from user |
| `available_quantity` | `Optional[int]` | Stock quantity determined by `order_confirmed` from menu |
| `status` | `str` | Node status (`confirmed`, `partial`, `unavailable`, `ready`, `completed`, `cook_failed`, `serve_failed`, `cancelled`) |
| `order_retry_count` | `int` | Decrements when order retried (Default: **3**) |
| `cook_retry_count` | `int` | Decrements when cooking fails (Default: **2**) |
| `serve_retry_count` | `int` | Decrements when serving fails (Default: **2**) |
| `final_result` | `Optional[str]` | `"completed"` or `"failed"` |

---

## Quickstart

### 1. Run Interactive CLI
You can place orders interactively in your terminal:
```bash
python main.py
```

### 2. Run Test Simulations
To run all automated simulation test cases:
```bash
python simulate.py
```

### 3. Optional: Configure LLM Provider
The agent has a built-in heuristic NLP extractor that works with zero external dependencies or API keys. To connect with a live LLM (OpenAI or Google Gemini), simply set:
```bash
export GOOGLE_API_KEY="your-gemini-key"
# or
export OPENAI_API_KEY="your-openai-key"
```
