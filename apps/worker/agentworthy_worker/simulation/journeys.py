"""Default journey templates by site type."""

from __future__ import annotations

JOURNEY_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "ecommerce": [
        {"name": "Find a product", "task_key": "find_product", "task_template": "Find any product on this site and view its details page."},
        {"name": "Add to cart", "task_key": "add_to_cart", "task_template": "Add any product to the shopping cart."},
        {"name": "Reach checkout", "task_key": "reach_checkout", "task_template": "Navigate to the checkout page with items in cart."},
    ],
    "restaurant": [
        {"name": "View menu", "task_key": "view_menu", "task_template": "Find and view the restaurant menu."},
        {"name": "Make reservation", "task_key": "reservation", "task_template": "Start a table reservation or booking flow."},
    ],
    "local": [
        {"name": "Contact business", "task_key": "contact", "task_template": "Find contact information or a contact form for this business."},
    ],
    "saas": [
        {"name": "View pricing", "task_key": "pricing", "task_template": "Find the pricing page and view plan details."},
        {"name": "Start signup", "task_key": "signup", "task_template": "Navigate to the signup or trial registration page."},
    ],
    "lead-gen": [
        {"name": "Find contact form", "task_key": "lead_form", "task_template": "Find a contact or lead capture form on the site."},
    ],
    "other": [
        {"name": "Explore site", "task_key": "explore", "task_template": "Navigate the site and find the main call-to-action."},
    ],
}


def journeys_for_site_type(site_type: str) -> list[dict[str, str]]:
    return JOURNEY_TEMPLATES.get(site_type, JOURNEY_TEMPLATES["other"])
