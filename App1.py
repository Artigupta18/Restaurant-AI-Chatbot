import streamlit as st
import json
import uuid
from openai import OpenAI

if "orderHistory" not in st.session_state:
    st.session_state.orderHistory = {}

menu = {
    "burger": {"price": 150, "stock": 10, "description": "Delicious beef burger"},
    "pizza": {"price": 300, "stock": 5, "description": "Cheesy pepperoni pizza"},
    "pasta": {"price": 250, "stock": 8, "description": "Creamy alfredo pasta"},
    "coke": {"price": 50, "stock": 20, "description": "Refreshing soft drink"},
    "sandwich": {"price": 120, "stock": 15, "description": "Grilled cheese sandwich"},
    "fries": {"price": 100, "stock": 12, "description": "Crispy golden french fries"},
    "mojito": {"price": 180, "stock": 10, "description": "Cool mint mojito"},
    "coffee": {"price": 120, "stock": 20, "description": "Hot brewed coffee"},
    "tea": {"price": 80, "stock": 25, "description": "Refreshing herbal tea"}
}

def getMenu():
    return json.dumps(menu, indent=2)

def addToCart(item, quantity):
    item = item.lower()
    cart = st.session_state.cart

    if item in menu:
        if menu[item]["stock"] >= quantity:
            cart[item] = cart.get(item, 0) + quantity
            menu[item]["stock"] -= quantity
            return json.dumps({"message": f"{quantity} {item}(s) added to cart.", "cart": cart})
        else:
            return json.dumps({"error": f"Only {menu[item]['stock']} {item}(s) available."})
    return json.dumps({"error": "Item not available in menu."})

def removeFromCart(item, quantity):
    item = item.lower()
    cart = st.session_state.cart

    if item in cart:
        if cart[item] > quantity:
            cart[item] -= quantity
            menu[item]["stock"] += quantity
        else:
            menu[item]["stock"] += cart[item]
            del cart[item]

        return json.dumps({"message": f"{quantity} {item}(s) removed from cart.", "cart": cart})
    
    return json.dumps({"error": "Item not in cart."})

def getOrderDetails():
    cart = st.session_state.cart
    orderHistory = st.session_state.orderHistory

    if not cart:
        return json.dumps({"message": "Your cart is empty."})

    total = sum(menu[item]["price"] * qty for item, qty in cart.items())
    order_id = str(uuid.uuid4())[:8]
    
   
    orderHistory[order_id] = {"cart": cart.copy(), "total": total}
    
    response = {
        "orderId": order_id,
        "order": orderHistory[order_id],
        "cart_snapshot": cart.copy()
    }

    cart.clear()  
    return json.dumps(response)

def clearCart():
    cart = st.session_state.cart

    for item, qty in cart.items():
        menu[item]["stock"] += qty  

    cart.clear()
    return json.dumps({"message": "Cart has been cleared."})

def viewOrderHistory():
    orderHistory = st.session_state.orderHistory
    return json.dumps(orderHistory) if orderHistory else json.dumps({"message": "No past orders."})

tools = [
    {"type": "function", "function": {"name": "getMenu", "description": "Get the restaurant menu.", 
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}},
    
    {"type": "function", "function": {"name": "addToCart", "description": "Add an item to the cart.", 
        "parameters": {"type": "object", "properties": {"item": {"type": "string"}, "quantity": {"type": "integer"}}, 
        "required": ["item", "quantity"], "additionalProperties": False}}},
    
    {"type": "function", "function": {"name": "removeFromCart", "description": "Remove an item from the cart.", 
        "parameters": {"type": "object", "properties": {"item": {"type": "string"}, "quantity": {"type": "integer"}}, 
        "required": ["item", "quantity"], "additionalProperties": False}}},
    
    {"type": "function", "function": {"name": "getOrderDetails", "description": "Get the order details and generate an order ID.", 
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}},
    
    {"type": "function", "function": {"name": "clearCart", "description": "Clear all items from the cart.", 
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}},
    
    {"type": "function", "function": {"name": "viewOrderHistory", "description": "View past order history.", 
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}}
]
api_key = st.secrets["OPENAI_API_KEY"]


client = OpenAI(api_key=api_key)
if "cart" not in st.session_state:
    st.session_state.cart = {}

def executeToolCall(toolCall):
    tool = toolCall.function
    args = json.loads(tool.arguments) if hasattr(tool, "arguments") else {}

    if tool.name == "getMenu":
        return getMenu()
    if tool.name == "addToCart":
        return addToCart(args.get("item", ""), args.get("quantity", 1))
    if tool.name == "removeFromCart":
        return removeFromCart(args.get("item", ""), args.get("quantity", 1))
    if tool.name == "getOrderDetails":
        return getOrderDetails()
    if tool.name == "clearCart":
        return clearCart()
    if tool.name == "viewOrderHistory":
        return viewOrderHistory()

    return json.dumps({"error": "Unknown tool call."})


st.title("Restaurant AI Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if isinstance(msg, dict):  
        role = msg["role"]
        content = msg["content"]
    else: 
        role = msg.role
        content = msg.content

    st.chat_message(role).write(content)


user_input = st.chat_input("Enter your message:")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=st.session_state.messages,
        tools=tools
    )
    
    aiMessage = response.choices[0].message
    st.session_state.messages.append(aiMessage)

    if aiMessage.tool_calls:
        tool_responses = []
        for toolCall in aiMessage.tool_calls:
            toolResponse = executeToolCall(toolCall)
            tool_responses.append({"role": "tool", "content": toolResponse, "tool_call_id": toolCall.id})

        st.session_state.messages.extend(tool_responses)
        
        finalResponse = client.chat.completions.create(
            model="gpt-4o",
            messages=st.session_state.messages,
            tools=tools
        )

        final_msg = finalResponse.choices[0].message
        st.session_state.messages.append(final_msg)
        st.chat_message("assistant").write(final_msg.content)
    else:
        st.chat_message("assistant").write(aiMessage.content)
