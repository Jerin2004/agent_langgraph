"""Restaurant Menu and Inventory Management for Restaurant Order AI Agent."""

from typing import Dict, Tuple

# Default restaurant menu with stock quantities
# Notice: "salad" has 0 quantity for testing unavailable items
# "pasta" has 2 quantity for testing partial availability
DEFAULT_MENU: Dict[str, int] = {
    "burger": 10,
    "cheeseburger": 8,
    "pizza": 5,
    "pasta": 2,
    "sandwich": 4,
    "fries": 8,
    "salad": 0,       # out of stock / unavailable
    "sushi": 6,
    "taco": 5,
}

def normalize_dish_name(dish_name: str) -> str:
    """Normalize dish name for case-insensitive and basic plural matching."""
    name = dish_name.strip().lower()
    # Simple singularization if not found directly
    if name not in DEFAULT_MENU:
        if name.endswith("s") and name[:-1] in DEFAULT_MENU:
            return name[:-1]
        if name.endswith("es") and name[:-2] in DEFAULT_MENU:
            return name[:-2]
    return name

def check_dish_availability(
    dish_name: str,
    required_quantity: int,
    menu: Dict[str, int] = None
) -> Tuple[str, int]:
    """
    Checks the availability of the dish against the menu.
    
    Returns:
        (status, available_quantity)
        status: "confirmed" (fully available)
                "partial" (partially available, 0 < available < required)
                "unavailable" (not in menu or stock is 0)
    """
    if menu is None:
        menu = DEFAULT_MENU

    normalized = normalize_dish_name(dish_name)

    if normalized not in menu:
        # Dish not present in menu
        return "unavailable", 0

    available_stock = menu[normalized]

    if available_stock <= 0:
        # Stock is 0
        return "unavailable", 0
    elif available_stock >= required_quantity:
        # Full order available
        return "confirmed", available_stock
    else:
        # Partially available
        return "partial", available_stock
