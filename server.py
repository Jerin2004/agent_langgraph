"""FastAPI Web Server for Restaurant Order AI Agent UI."""

import uuid
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from graph import create_order_graph
from menu import DEFAULT_MENU

app = FastAPI(title="Restaurant Order AI Agent")

# Persistent LangGraph instance with in-memory checkpointer
order_agent = create_order_graph()

# Session thread store to track active conversation thread IDs
active_threads: Dict[str, dict] = {}


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    cook_override: Optional[float] = None
    serve_override: Optional[float] = None


@app.get("/api/menu")
def get_menu():
    """Returns current restaurant menu with inventory stock and status."""
    items = []
    for dish, qty in DEFAULT_MENU.items():
        if qty <= 0:
            status = "out_of_stock"
        elif qty <= 2:
            status = "low_stock"
        else:
            status = "in_stock"
        items.append({
            "dish": dish,
            "stock": qty,
            "status": status
        })
    return {"menu": items}


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Processes user input through the LangGraph order agent."""
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    inputs: Dict[str, Any] = {
        "messages": [HumanMessage(content=req.message)]
    }

    if req.cook_override is not None:
        inputs["cook_probability_override"] = req.cook_override
    if req.serve_override is not None:
        inputs["serve_probability_override"] = req.serve_override

    try:
        result = order_agent.invoke(inputs, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Format messages for the frontend
    formatted_messages = []
    for msg in result.get("messages", []):
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        formatted_messages.append({
            "role": role,
            "content": msg.content
        })

    response_data = {
        "thread_id": thread_id,
        "messages": formatted_messages,
        "dish_name": result.get("dish_name"),
        "required_quantity": result.get("required_quantity"),
        "available_quantity": result.get("available_quantity"),
        "status": result.get("status"),
        "order_retry_count": result.get("order_retry_count", 3),
        "cook_retry_count": result.get("cook_retry_count", 2),
        "serve_retry_count": result.get("serve_retry_count", 2),
        "final_result": result.get("final_result"),
    }

    active_threads[thread_id] = response_data
    return response_data


@app.get("/api/state/{thread_id}")
def get_thread_state(thread_id: str):
    """Retrieves current state for a thread."""
    if thread_id in active_threads:
        return active_threads[thread_id]
    return {
        "thread_id": thread_id,
        "status": "pending",
        "order_retry_count": 3,
        "cook_retry_count": 2,
        "serve_retry_count": 2,
        "final_result": None,
        "messages": []
    }


@app.post("/api/reset")
def reset_session():
    """Generates a fresh thread_id for a new order session."""
    new_thread_id = str(uuid.uuid4())
    return {
        "thread_id": new_thread_id,
        "message": "Session reset successfully"
    }


# Mount static assets
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_index():
    return FileResponse("static/index.html")
