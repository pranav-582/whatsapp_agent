import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
from functions import get_products, place_order, check_order_status, process_return, compare_products_serper, manage_session_chat_history
load_dotenv()

class ProductDetailsAgent:
    """AI Agent for handling product information requests using get_products"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.3,
        )
    
    def process_message(self, user_message, phone_no, customer_data, previous_conversations, chat_context=""):
        """Process product details requests"""

        user_lower = user_message.lower()
        product_keywords = ['iphone', 'macbook', 'ipad', 'airpods', 'levi', 'nike', 'puma', 'adidas']
        
        product_name = None
        for keyword in product_keywords:
            if keyword in user_lower:
                product_name = keyword
                break

        if any(word in user_lower for word in ['all', 'catalog', 'everything', 'show me']):
            product_data = get_products()
        elif product_name:
            product_data = get_products(product_name)
        else:
            product_data = get_products()

        if product_data and product_data.get('found'):
            products_info = f"Found {product_data['total_products']} products:\n\n"
            for product in product_data['products']:
                status = "✅ Available" if product['available'] else "❌ Out of Stock"
                products_info += f"• {product['product_name']} ({product['size']})\n"
                products_info += f"  Price: ${product['price']:.2f}\n"
                products_info += f"  Stock: {product['stock_quantity']} units {status}\n\n"
        else:
            products_info = "No products found or unable to retrieve product information."

        system_prompt = f"""You are a Product Information Specialist for our e-commerce store.

CHAT CONTEXT:
{chat_context}

AVAILABLE PRODUCTS:
{products_info}

Your role:
- Provide detailed product information, specifications, and pricing
- Help customers understand product features and benefits
- Show product availability and stock levels
- Be enthusiastic about products while being honest about details
- Use emojis to make responses friendly (🛍️ 💰 📦 ✨)

Customer: {customer_data.get('customer_name', 'Valued Customer')}
Phone: {phone_no}

Respond to their inquiry about products in a helpful and engaging way."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        response = self.llm.invoke(messages)
        return response.content


class InventoryManagementAgent:
    """AI Agent for handling orders, returns, and inventory management"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.3,
        )
    
    def process_message(self, user_message, phone_no, customer_data, previous_conversations, chat_context=""):
        """Process inventory management requests"""
        
        user_lower = user_message.lower()
        operation_result = ""

        if any(keyword in user_lower for keyword in ['order status', 'check order', 'my orders', 'track']):
            order_data = check_order_status(phone_no)
            if order_data['found']:
                operation_result = f"ORDER STATUS for {order_data['customer_name']}:\n"
                operation_result += f"Total Orders: {order_data['order_count']}\n\n"
                for order in order_data['orders'][:3]:  # Show last 3 orders
                    operation_result += f"📦 Order #{order['order_id']}\n"
                    operation_result += f"   Product: {order['product_name']} ({order['size']})\n"
                    operation_result += f"   Quantity: {order['quantity']}\n"
                    operation_result += f"   Total: ${order['total_amount']:.2f}\n"
                    operation_result += f"   Status: {order['status']}\n"
                    operation_result += f"   Date: {order['order_date']}\n\n"
            else:
                operation_result = f"ORDER STATUS: {order_data['message']}"
                
        elif any(keyword in user_lower for keyword in ['return', 'refund', 'send back']):
            return_data = process_return(phone_no)
            if return_data['success']:
                operation_result = f"RETURN PROCESSED:\n"
                operation_result += f"Return ID: #{return_data['return_id']}\n"
                operation_result += f"Order ID: #{return_data['order_id']}\n"
                operation_result += f"Product: {return_data['product_name']} ({return_data['size']})\n"
                operation_result += f"Quantity: {return_data['quantity']}\n"
                operation_result += f"Refund Amount: ${return_data['refund_amount']:.2f}\n"
                operation_result += f"Status: {return_data['status']}\n"
                operation_result += f"Reason: {return_data['reason']}\n"
            else:
                operation_result = f"RETURN ERROR: {return_data['message']}"
                
        elif any(keyword in user_lower for keyword in ['buy', 'order', 'purchase', 'want to buy']):
            if 'levi' in user_lower and 't-shirt' in user_lower:
                size = 'M' if ' m ' in user_lower or user_lower.endswith(' m') else 'L'
                order_data = place_order(phone_no, "Levi's T-Shirt", size, 1, customer_data.get('customer_name'))
            elif 'nike' in user_lower and 'shoes' in user_lower:
                size = '42' if '42' in user_message else '44'
                order_data = place_order(phone_no, "Nike Running Shoes", size, 1, customer_data.get('customer_name'))
            else:
                operation_result = "PLACE ORDER: Please specify the product name and size you want to order."
                order_data = {"success": False}
            
            if order_data.get("success"):
                operation_result = f"ORDER PLACED SUCCESSFULLY:\n"
                operation_result += f"Order ID: #{order_data['order_id']}\n"
                operation_result += f"Product: {order_data['product_name']} ({order_data['size']})\n"
                operation_result += f"Quantity: {order_data['quantity']}\n"
                operation_result += f"Unit Price: ${order_data['unit_price']:.2f}\n"
                operation_result += f"Total: ${order_data['total_amount']:.2f}\n"
                operation_result += f"Status: {order_data['status']}\n"
            elif 'Please specify' not in operation_result:
                operation_result = f"ORDER ERROR: {order_data.get('message', 'Unknown error')}"
        else:
            operation_result = "I can help you with:\n- Checking order status\n- Placing new orders\n- Processing returns\n\nWhat would you like to do?"

        system_prompt = f"""You are an Inventory Management Specialist for our e-commerce store.

CHAT CONTEXT:
{chat_context}

OPERATION RESULT:
{operation_result}

Customer Info: {customer_data.get('customer_name', 'Unknown')} ({phone_no})

Your role:
- Help customers with order placement, tracking, and returns
- Provide clear order status information
- Process return requests professionally
- Be empathetic with order issues
- Use order-related emojis (📦 ✅ 🚚 📋 💰)

Respond to the customer's request based on the operation result above."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        response = self.llm.invoke(messages)
        return response.content


class ProductComparisonAgent:
    """AI Agent for handling product comparisons using compare_products_serper"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.3,
        )
    
    def process_message(self, user_message, phone_no, customer_data, previous_conversations, chat_context=""):
        """Process product comparison requests"""

        comparison_data = compare_products_serper(user_message)

        if comparison_data.get('success'):
            comparison_info = f"EXTERNAL COMPARISON RESULTS for '{comparison_data['query']}':\n"
            comparison_info += f"Found {comparison_data['result_count']} comparison sources:\n\n"
            
            for i, result in enumerate(comparison_data['results'], 1):
                comparison_info += f"{i}. {result['title']}\n"
                comparison_info += f"   Summary: {result['snippet']}\n"
                if result.get('source'):
                    comparison_info += f"   Source: {result['source']}\n"
                comparison_info += "\n"
        else:
            comparison_info = f"COMPARISON ERROR: {comparison_data.get('message', 'Unable to fetch comparison data')}"

        our_products_info = ""
        if any(product in user_message.lower() for product in ['iphone', 'macbook', 'ipad', 'airpods']):
            internal_products = get_products()
            if internal_products and internal_products.get('found'):
                our_products_info = "\nOUR AVAILABLE PRODUCTS:\n"
                for product in internal_products['products'][:5]:  # Show first 5
                    our_products_info += f"• {product['product_name']} ({product['size']}): ${product['price']:.2f}\n"

        system_prompt = f"""You are a Product Comparison Specialist for our e-commerce store.

CHAT CONTEXT:
{chat_context}

COMPARISON RESEARCH:
{comparison_info}

{our_products_info}

Customer: {customer_data.get('customer_name', 'Valued Customer')}

Your role:
- Help customers compare different products objectively
- Provide balanced comparisons highlighting pros and cons
- Use external research data to support comparisons
- Guide purchasing decisions with unbiased information
- Use comparison emojis (⚖️ 🔍 📊 vs.)
- Summarize key findings and recommendations

Respond to their comparison request with helpful, objective analysis."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        response = self.llm.invoke(messages)
        return response.content