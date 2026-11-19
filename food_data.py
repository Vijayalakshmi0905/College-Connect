"""
Food catalog data for College Connect Canteen.
Contains 16 sample Indian food items categorized into:
- Breakfast
- Lunch
- Snacks
- Beverages
"""

FOOD_ITEMS = [
    # --- Breakfast ---
    {
        "id": 1,
        "name": "Masala Dosa",
        "category": "Breakfast",
        "price": 60,
        "description": "Crispy fermented crepe stuffed with spiced potato mash, served with coconut chutney and sambar.",
        "image": "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 2,
        "name": "Idli Vada Combo",
        "category": "Breakfast",
        "price": 50,
        "description": "Two soft steamed rice cakes and one crispy medu vada served with piping hot sambar.",
        "image": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 3,
        "name": "Indori Poha",
        "category": "Breakfast",
        "price": 35,
        "description": "Flattened rice tempered with mustard seeds, curry leaves, crunchy peanuts, and ratlami sev.",
        "image": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 4,
        "name": "Aloo Paratha with Curd",
        "category": "Breakfast",
        "price": 65,
        "description": "Whole wheat flatbread stuffed with spiced potato filling, served with fresh curd and pickle.",
        "image": "https://images.unsplash.com/photo-1626074353765-517a681e40be?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },

    # --- Lunch ---
    {
        "id": 5,
        "name": "Paneer Butter Masala Thali",
        "category": "Lunch",
        "price": 120,
        "description": "Cottage cheese in rich tomato-butter gravy, served with 2 rotis, jeera rice, dal, and salad.",
        "image": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 6,
        "name": "Hyderabadi Veg Biryani",
        "category": "Lunch",
        "price": 110,
        "description": "Aromatic basmati rice slow-cooked with fresh garden vegetables and saffron, served with cucumber raita.",
        "image": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 7,
        "name": "Rajma Chawal Bowl",
        "category": "Lunch",
        "price": 80,
        "description": "North Indian kidney bean curry in thick onion-tomato gravy, served over steamed basmati rice.",
        "image": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 8,
        "name": "Dal Tadka with Jeera Rice",
        "category": "Lunch",
        "price": 85,
        "description": "Yellow lentils tempered with ghee, garlic, and cumin seeds, served alongside fragrant jeera rice.",
        "image": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },

    # --- Snacks ---
    {
        "id": 9,
        "name": "Samosa Chaat (2 pcs)",
        "category": "Snacks",
        "price": 45,
        "description": "Crushed crispy potato samosas topped with warm chole, mint & tamarind chutneys, and nylon sev.",
        "image": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 10,
        "name": "Mumbai Pav Bhaji",
        "category": "Snacks",
        "price": 75,
        "description": "Mashed spiced vegetable curry with generous butter, served with two soft toasted pav buns.",
        "image": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 11,
        "name": "Veg Grilled Cheese Sandwich",
        "category": "Snacks",
        "price": 60,
        "description": "Golden grilled bread filled with cucumber, tomato, green bell pepper, cheese, and spicy mint chutney.",
        "image": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 12,
        "name": "Chole Bhature",
        "category": "Snacks",
        "price": 95,
        "description": "Spicy chickpea curry paired with two fluffy, golden-fried bhature, pickled carrots, and onions.",
        "image": "https://images.unsplash.com/photo-1626132647523-66f5bf380027?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },

    # --- Beverages ---
    {
        "id": 13,
        "name": "Kulhad Masala Chai",
        "category": "Beverages",
        "price": 15,
        "description": "Traditional Indian tea brewed with crushed ginger, cardamom, and whole spices, served in a clay kulhad.",
        "image": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 14,
        "name": "South Indian Filter Coffee",
        "category": "Beverages",
        "price": 25,
        "description": "Authentic chicory blend coffee frothed with steaming hot milk in a traditional brass tumbler.",
        "image": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 15,
        "name": "Alphonso Mango Lassi",
        "category": "Beverages",
        "price": 50,
        "description": "Thick chilled yogurt beverage blended with sweet Alphonso mango pulp and garnished with pistachios.",
        "image": "https://images.unsplash.com/photo-1570701564993-e00652af8aa7?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    },
    {
        "id": 16,
        "name": "Fresh Nimbu Shikanji",
        "category": "Beverages",
        "price": 30,
        "description": "Refreshing chilled lemonade flavored with black salt, roasted cumin seeds, and fresh mint leaves.",
        "image": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=500&auto=format&fit=crop&q=60",
        "available": True,
        "is_veg": True
    }
]

CATEGORIES = ["All", "Breakfast", "Lunch", "Snacks", "Beverages"]
