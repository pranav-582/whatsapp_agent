import os
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import requests
import json
import redis



redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

load_dotenv()

def load_previous_conversations_to_redis(phone_no: str, limit: int = 20) -> Dict[str, Any]:
    """Check if previous conversations exist in DB and load them to Redis"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Get the most recent conversation for this phone number
        cursor.execute("""
            SELECT conversation_id, started_at
            FROM conversations 
            WHERE phone_no = %s 
            ORDER BY started_at DESC 
            LIMIT 1
        """, (phone_no,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            cursor.close()
            conn.close()
            return {
                "found": False,
                "loaded": False,
                "message": "No previous conversations found in database"
            }
        
        conversation_id = conversation[0]
        started_at = conversation[1]
        
        # Get messages from the conversation
        cursor.execute("""
            SELECT sender, message_text, timestamp
            FROM messages 
            WHERE conversation_id = %s
            ORDER BY timestamp ASC
            LIMIT %s
        """, (conversation_id, limit))
        
        messages = cursor.fetchall()
        
        # Get customer name
        cursor.execute("SELECT customer_name FROM customers WHERE phone_no = %s", (phone_no,))
        customer = cursor.fetchone()
        customer_name = customer[0] if customer else "Unknown"
        
        cursor.close()
        conn.close()
        
        if not messages:
            return {
                "found": True,
                "loaded": False,
                "message": "Conversation found but no messages"
            }
        
        # Load conversation into Redis
        redis_key = f"conversation:{phone_no}"
        
        conversation_data = {
            "phone_no": phone_no,
            "whatsapp_name": customer_name,
            "started_at": started_at.isoformat(),
            "messages": [],
            "last_activity": datetime.now().isoformat(),
            "loaded_from_db": True
        }
        
        # Add all messages
        for msg in messages:
            conversation_data["messages"].append({
                "sender": msg[0],
                "message_text": msg[1],
                "timestamp": msg[2].isoformat()
            })
        
        # Save to Redis with 30 minute expiry
        redis_client.setex(redis_key, 1800, json.dumps(conversation_data))
        
        return {
            "found": True,
            "loaded": True,
            "phone_no": phone_no,
            "messages_loaded": len(messages),
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        print(f"Error loading previous conversations: {e}")
        return {
            "found": False,
            "loaded": False,
            "message": f"Error: {str(e)}"
        }

# Add this function to store and retrieve chat history

def manage_session_chat_history(phone_no: str, user_message: str = None, bot_response: str = None, get_context: bool = False) -> Dict[str, Any]:
    """Store chat messages in Redis and retrieve context for next messages"""
    try:
        redis_key = f"chat_session:{phone_no}"
        
        # CLEANUP: Move old conversations to DB before processing new messages
        if user_message or bot_response:
            _cleanup_old_conversations()
            # Get existing chat history
            existing_chat = redis_client.get(redis_key)
            if existing_chat:
                chat_history = json.loads(existing_chat)
            else:
                chat_history = {
                    "phone_no": phone_no,
                    "messages": [],
                    "started_at": datetime.now().isoformat()
                }
            
            # Add user message
            if user_message:
                chat_history["messages"].append({
                    "sender": "user",
                    "message": user_message,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Add bot response
            if bot_response:
                chat_history["messages"].append({
                    "sender": "bot",
                    "message": bot_response,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Update last activity
            chat_history["last_activity"] = datetime.now().isoformat()
            
            # Store back to Redis with 23 minutes expiry
            redis_client.setex(redis_key, 1800, json.dumps(chat_history))  
        
        # Get context if requested
        if get_context:
            chat_data = redis_client.get(redis_key)
            if chat_data:
                chat_history = json.loads(chat_data)
                
                # Get last 10 messages for context
                recent_messages = chat_history["messages"][-10:]
                
                # Format context
                context_text = "Previous conversation:\n"
                for msg in recent_messages:
                    sender = "User" if msg["sender"] == "user" else "Assistant"
                    context_text += f"{sender}: {msg['message']}\n"
                
                return {
                    "success": True,
                    "phone_no": phone_no,
                    "total_messages": len(chat_history["messages"]),
                    "context_messages": len(recent_messages),
                    "context": context_text,
                    "raw_messages": recent_messages
                }
            else:
                return {
                    "success": True,
                    "phone_no": phone_no,
                    "total_messages": 0,
                    "context": "No previous conversation history.",
                    "raw_messages": []
                }
        
        return {
            "success": True,
            "phone_no": phone_no,
            "message": "Chat history updated"
        }
        
    except Exception as e:
        print(f"Error managing chat history: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }



def _cleanup_old_conversations():
    """Check all Redis chat sessions and move expired ones to DB"""
    try:
        chat_keys = redis_client.keys("chat_session:*")
        current_time = datetime.now()
        
        for key in chat_keys:
            chat_data = redis_client.get(key)
            if not chat_data:
                continue
                
            chat_history = json.loads(chat_data)
            last_activity = datetime.fromisoformat(chat_history.get("last_activity", chat_history["started_at"]))
            
            # If older than 30 minutes, move to DB
            if current_time - last_activity >= timedelta(minutes=30):
                phone_no = chat_history["phone_no"]
                _save_chat_to_db(phone_no, chat_history)
                redis_client.delete(key)
                print(f"Moved conversation for {phone_no} to DB (inactive for 30+ minutes)")
                
    except Exception as e:
        print(f"Cleanup error: {e}")

def _save_chat_to_db(phone_no: str, chat_history: Dict[str, Any]):
    """Save chat session to database"""
    try:
        # ENSURE CUSTOMER EXISTS using existing function
        customer_result = get_or_create_customer(phone_no, "Unknown User")
        if not customer_result["found"]:
            print(f"Error: Could not create customer for {phone_no}")
            return
        
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Insert conversation
        cursor.execute("""
            INSERT INTO conversations (phone_no, started_at, ended_at)
            VALUES (%s, %s, %s)
            RETURNING conversation_id
        """, (
            phone_no,
            datetime.fromisoformat(chat_history["started_at"]),
            datetime.fromisoformat(chat_history["last_activity"])
        ))
        conversation_id = cursor.fetchone()[0]
        
        # Insert messages
        for msg in chat_history["messages"]:
            cursor.execute("""
                INSERT INTO messages (conversation_id, sender, message_text, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (
                conversation_id,
                msg["sender"],
                msg["message"],
                datetime.fromisoformat(msg["timestamp"])
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Chat saved to DB: Conversation ID {conversation_id}")
        
    except Exception as e:
        print(f"Error saving chat to DB: {e}")




# ======================
# PRODUCT FUNCTIONS
# ======================

def get_products(product_name: Optional[str] = None) -> Dict[str, Any]:
    """Get product catalog or specific product details"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        if product_name:
            # Get specific product details
            cursor.execute("""
                SELECT 
                    product_id,
                    product_name,
                    size,
                    price,
                    stock_quantity
                FROM products 
                WHERE LOWER(product_name) LIKE LOWER(%s)
                ORDER BY product_name, size, price
            """, [f"%{product_name}%"])
        else:
            # Get all products catalog
            cursor.execute("""
                SELECT 
                    product_id,
                    product_name,
                    size,
                    price,
                    stock_quantity
                FROM products 
                WHERE stock_quantity > 0
                ORDER BY product_name, size
            """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            return {
                "found": False,
                "message": f"No products found{f' for {product_name}' if product_name else ''}",
                "products": []
            }
        
        products = []
        for row in results:
            products.append({
                "product_id": row[0],
                "product_name": row[1],
                "size": row[2],
                "price": float(row[3]),
                "stock_quantity": row[4],
                "available": row[4] > 0
            })
        
        return {
            "found": True,
            "total_products": len(products),
            "products": products
        }
        
    except Exception as e:
        print(f"Error getting products: {e}")
        return {
            "found": False,
            "message": f"Error retrieving products: {str(e)}",
            "products": []
        }

# ======================
# CUSTOMER FUNCTIONS
# ======================

def get_or_create_customer(phone_no: str, customer_name: str = None) -> Dict[str, Any]:
    """Get existing customer or create new one"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Check if customer exists
        cursor.execute("SELECT phone_no, customer_name FROM customers WHERE phone_no = %s", (phone_no,))
        customer = cursor.fetchone()
        
        if customer:
            cursor.close()
            conn.close()
            return {
                "found": True,
                "phone_no": customer[0],
                "customer_name": customer[1]
            }
        
        # Create new customer if name provided
        if customer_name:
            cursor.execute("""
                INSERT INTO customers (phone_no, customer_name) 
                VALUES (%s, %s)
            """, (phone_no, customer_name))
            conn.commit()
            
            cursor.close()
            conn.close()
            return {
                "found": True,
                "phone_no": phone_no,
                "customer_name": customer_name,
                "created": True
            }
        
        cursor.close()
        conn.close()
        return {
            "found": False,
            "message": "Customer not found and no name provided for creation"
        }
        
    except Exception as e:
        print(f"Error with customer: {e}")
        return {
            "found": False,
            "message": f"Error: {str(e)}"
        }

# ======================
# ORDER FUNCTIONS
# ======================

def check_order_status(phone_no: str) -> Dict[str, Any]:
    """Check order status for a customer"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Check if customer exists
        cursor.execute("SELECT phone_no, customer_name FROM customers WHERE phone_no = %s", (phone_no,))
        customer = cursor.fetchone()
        
        if not customer:
            cursor.close()
            conn.close()
            return {
                "found": False,
                "message": f"No customer found with phone number {phone_no}"
            }
        
        # Get orders with product details
        cursor.execute("""
            SELECT 
                o.order_id,
                o.quantity,
                o.order_date,
                o.status,
                p.product_name,
                p.size,
                p.price
            FROM orders o
            JOIN products p ON o.product_id = p.product_id
            WHERE o.phone_no = %s
            ORDER BY o.order_date DESC
        """, (phone_no,))
        
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not orders:
            return {
                "found": True,
                "customer_name": customer[1],
                "phone_no": customer[0],
                "order_count": 0,
                "orders": [],
                "message": "No orders found for this customer"
            }
        
        order_list = []
        for order in orders:
            total_amount = order[1] * float(order[6])  # quantity * price
            order_list.append({
                "order_id": order[0],
                "quantity": order[1],
                "order_date": order[2].strftime('%Y-%m-%d %H:%M:%S') if order[2] else None,
                "status": order[3],
                "product_name": order[4],
                "size": order[5],
                "unit_price": float(order[6]),
                "total_amount": total_amount
            })
        
        return {
            "found": True,
            "customer_name": customer[1],
            "phone_no": customer[0],
            "order_count": len(orders),
            "orders": order_list
        }
        
    except Exception as e:
        print(f"Error checking order status: {e}")
        return {
            "found": False,
            "message": f"Error checking orders: {str(e)}"
        }

def place_order(phone_no: str, product_name: str, size: str, quantity: int = 1, customer_name: str = None) -> Dict[str, Any]:
    """Place a new order"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Get or create customer
        customer_result = get_or_create_customer(phone_no, customer_name)
        if not customer_result["found"]:
            return {
                "success": False,
                "message": customer_result["message"]
            }
        
        # Find product
        cursor.execute("""
            SELECT product_id, product_name, size, price, stock_quantity 
            FROM products 
            WHERE LOWER(product_name) LIKE LOWER(%s) AND LOWER(size) = LOWER(%s)
        """, (f"%{product_name}%", size))
        
        product = cursor.fetchone()
        
        if not product:
            cursor.close()
            conn.close()
            return {
                "success": False,
                "message": f"Product '{product_name}' with size '{size}' not found"
            }
        
        # Check stock
        if product[4] < quantity:
            cursor.close()
            conn.close()
            return {
                "success": False,
                "message": f"Insufficient stock. Available: {product[4]}, Requested: {quantity}"
            }
        
        # Place order
        cursor.execute("""
            INSERT INTO orders (phone_no, product_id, quantity)
            VALUES (%s, %s, %s)
            RETURNING order_id
        """, (phone_no, product[0], quantity))
        
        order_id = cursor.fetchone()[0]
        
        # Update stock
        cursor.execute("""
            UPDATE products 
            SET stock_quantity = stock_quantity - %s 
            WHERE product_id = %s
        """, (quantity, product[0]))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        total_amount = quantity * float(product[3])
        
        return {
            "success": True,
            "order_id": order_id,
            "customer_name": customer_result["customer_name"],
            "phone_no": phone_no,
            "product_name": product[1],
            "size": product[2],
            "quantity": quantity,
            "unit_price": float(product[3]),
            "total_amount": total_amount,
            "status": "Placed"
        }
        
    except Exception as e:
        print(f"Error placing order: {e}")
        return {
            "success": False,
            "message": f"Error placing order: {str(e)}"
        }

# ======================
# RETURN FUNCTIONS
# ======================

def process_return(phone_no: str, order_id: Optional[int] = None, reason: str = "Customer request") -> Dict[str, Any]:
    """Process a return request"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Check if customer exists
        cursor.execute("SELECT phone_no, customer_name FROM customers WHERE phone_no = %s", (phone_no,))
        customer = cursor.fetchone()
        
        if not customer:
            cursor.close()
            conn.close()
            return {
                "success": False,
                "message": f"No customer found with phone number {phone_no}"
            }
        
        # If no order_id provided, get most recent order
        if not order_id:
            cursor.execute("""
                SELECT order_id FROM orders 
                WHERE phone_no = %s 
                ORDER BY order_date DESC 
                LIMIT 1
            """, (phone_no,))
            
            recent_order = cursor.fetchone()
            if not recent_order:
                cursor.close()
                conn.close()
                return {
                    "success": False,
                    "message": "No recent orders found for return"
                }
            order_id = recent_order[0]
        
        # Get order details including product_id
        cursor.execute("""
            SELECT o.order_id, o.quantity, o.status, o.product_id, p.product_name, p.size, p.price
            FROM orders o
            JOIN products p ON o.product_id = p.product_id
            WHERE o.order_id = %s AND o.phone_no = %s
        """, (order_id, phone_no))
        
        order = cursor.fetchone()
        
        if not order:
            cursor.close()
            conn.close()
            return {
                "success": False,
                "message": f"Order {order_id} not found for this customer"
            }
        
        # Create return
        cursor.execute("""
            INSERT INTO returns (order_id, phone_no, reason)
            VALUES (%s, %s, %s)
            RETURNING return_id
        """, (order_id, phone_no, reason))
        
        return_id = cursor.fetchone()[0]
        
        # ADD THIS: Restore stock quantity
        cursor.execute("""
            UPDATE products 
            SET stock_quantity = stock_quantity + %s 
            WHERE product_id = %s
        """, (order[1], order[3]))  # quantity, product_id
        
        conn.commit()
        cursor.close()
        conn.close()
        
        refund_amount = order[1] * float(order[6])  # quantity * price (adjusted index)
        
        return {
            "success": True,
            "return_id": return_id,
            "order_id": order[0],
            "product_name": order[4],
            "size": order[5],
            "quantity": order[1],
            "refund_amount": refund_amount,
            "reason": reason,
            "status": "Pending",
            "stock_restored": True
        }
        
    except Exception as e:
        print(f"Error processing return: {e}")
        return {
            "success": False,
            "message": f"Error processing return: {str(e)}"
        }

# ======================
# EXTERNAL API FUNCTIONS
# ======================

def compare_products_serper(query: str) -> Dict[str, Any]:
    """Compare products using Serper API"""
    try:
        serper_key = os.getenv('SERPER_API_KEY')
        
        if not serper_key:
            return {
                "success": False,
                "message": "Product comparison service is currently unavailable"
            }
        
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': serper_key,
            'Content-Type': 'application/json'
        }
        payload = {
            'q': f"{query} comparison review features specs vs differences",
            'num': 6
        }
        
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if 'organic' in data and data['organic']:
            comparison_results = []
            
            for result in data['organic'][:4]:  # Top 4 results
                comparison_results.append({
                    "title": result.get('title', 'N/A'),
                    "snippet": result.get('snippet', 'No description'),
                    "link": result.get('link', ''),
                    "source": result.get('source', 'Unknown')
                })
            
            return {
                "success": True,
                "query": query,
                "results": comparison_results,
                "result_count": len(comparison_results)
            }
        else:
            return {
                "success": False,
                "message": "No comparison data found. Try being more specific with product names."
            }
            
    except Exception as e:
        print(f"Error in product comparison: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }