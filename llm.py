"""LLM integration and extraction module for Restaurant Order AI Agent."""

import os
import re
from typing import Optional, Tuple
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class OrderExtraction(BaseModel):
    """Structured extraction of order details from user text."""
    is_food_related: bool = Field(
        description="True if the user input is related to ordering food or drinks, False otherwise."
    )
    dish_name: Optional[str] = Field(
        default=None,
        description="Name of the food dish (e.g., 'burger', 'pizza', 'pasta')."
    )
    quantity: Optional[int] = Field(
        default=None,
        description="Quantity requested by the user. Default to 1 if user requests a dish without explicit number."
    )
    user_decision: Optional[str] = Field(
        default=None,
        description="If user was asked to decide on partial/unavailable stock: 'accept_partial', 'new_order', 'cancel', or 'unknown'."
    )


def get_chat_model():
    """Returns an active LangChain ChatModel if API keys exist, else None."""
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if google_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=google_key,
                temperature=0.0
            )
        except Exception as e:
            print(f"[Warning] Failed to initialize Google GenAI model: {e}")

    if openai_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=openai_key,
                temperature=0.0
            )
        except Exception as e:
            print(f"[Warning] Failed to initialize OpenAI model: {e}")

    return None


def extract_order_details(user_text: str, current_dish: Optional[str] = None) -> OrderExtraction:
    """
    Extracts dish and quantity from user input using LLM or rule-based fallback.
    Identifies whether input is food-related or general/unrelated.
    """
    model = get_chat_model()
    if model:
        try:
            prompt = (
                "You are an AI food ordering assistant. Analyze the user's input.\n"
                "1. If the input is general conversation, greeting without order, general knowledge question, "
                "or unrelated to ordering food, set is_food_related=False.\n"
                "2. If the user is ordering food, set is_food_related=True, extract the dish_name and quantity.\n"
                "3. If the user mentions an agreement to a partial order (like 'yes', 'proceed', 'go ahead', "
                "'take the partial'), set user_decision='accept_partial'.\n"
                "4. If the user cancels ('no', 'cancel', 'nevermind'), set user_decision='cancel'.\n"
                "5. If the user places a new order, set user_decision='new_order'.\n\n"
                f"User text: \"{user_text}\""
            )
            structured_llm = model.with_structured_output(OrderExtraction)
            result = structured_llm.invoke(prompt)
            if result:
                return result
        except Exception as e:
            print(f"[LLM notice] Fallback to heuristic parser: {e}")

    # Robust Heuristic / Rule-Based NLP Parser Fallback
    return _rule_based_order_extraction(user_text, current_dish)


def _rule_based_order_extraction(user_text: str, current_dish: Optional[str] = None) -> OrderExtraction:
    """Heuristic rule-based extractor when LLM is unavailable or for testing."""
    text = user_text.strip().lower()

    # Check for cancellation
    if text in ["cancel", "no", "stop", "nevermind", "exit", "quit", "i don't want it", "not satisfied"]:
        return OrderExtraction(
            is_food_related=True,
            user_decision="cancel"
        )

    # Check for partial confirmation
    if text in ["yes", "proceed", "go ahead", "ok", "okay", "sure", "fine", "confirm", "i will take it", "take partial"]:
        return OrderExtraction(
            is_food_related=True,
            dish_name=current_dish,
            user_decision="accept_partial"
        )

    # Check for unrelated queries
    unrelated_patterns = [
        r"what is", r"who is", r"how do", r"tell me a", r"capital of",
        r"write code", r"solve", r"weather", r"math", r"history",
        r"explain", r"who are you"
    ]
    if any(re.search(pat, text) for pat in unrelated_patterns) and not any(
        food in text for food in ["order", "burger", "pizza", "pasta", "food", "eat", "salad", "sandwich"]
    ):
        return OrderExtraction(is_food_related=False)

    # Words to numbers mapping
    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "a": 1, "an": 1
    }

    # Extract quantity
    quantity = None
    num_match = re.search(r"\b(\d+)\b", text)
    if num_match:
        quantity = int(num_match.group(1))
    else:
        for word, val in word_to_num.items():
            if re.search(rf"\b{word}\b", text):
                quantity = val
                break

    # Common food items keywords to search for
    common_dishes = [
        "burger", "cheeseburger", "pizza", "pasta", "sandwich",
        "fries", "salad", "sushi", "taco", "noodle", "steak", "rice", "soup"
    ]

    detected_dish = None
    for dish in common_dishes:
        # Check singular and plural
        if re.search(rf"\b{dish}s?\b", text):
            detected_dish = dish
            break

    # If no explicit quantity was specified but dish was found, default to 1
    if detected_dish:
        if quantity is None:
            quantity = 1
        return OrderExtraction(
            is_food_related=True,
            dish_name=detected_dish,
            quantity=quantity,
            user_decision="new_order"
        )

    # Check if user says something like "I want 2 of those" or "give me 2" when current_dish exists
    if current_dish and quantity is not None:
        return OrderExtraction(
            is_food_related=True,
            dish_name=current_dish,
            quantity=quantity,
            user_decision="new_order"
        )

    # If text is unrelated or not understandable as an order
    return OrderExtraction(is_food_related=False)
