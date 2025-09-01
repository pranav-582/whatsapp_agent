import os
from typing import TypedDict, Annotated, Sequence
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
import operator
from dotenv import load_dotenv

from functions import get_or_create_customer, load_previous_conversations_to_redis, manage_session_chat_history
from ai_agents import ProductDetailsAgent, InventoryManagementAgent, ProductComparisonAgent

load_dotenv()

class IntentRouterState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    phone_no: str
    whatsapp_name: str
    user_message: str
    customer_data: dict
    is_new_user: bool
    previous_conversations: dict
    message_category: str
    agent_response: str
    
class IntentRouter:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.1,
        )

        self.product_details_agent = ProductDetailsAgent()
        self.inventory_management_agent = InventoryManagementAgent()
        self.product_comparison_agent = ProductComparisonAgent()
        
        self.graph = self._create_graph()
    
    def _create_graph(self):
        workflow = StateGraph(IntentRouterState)

        workflow.add_node("user_checker", self._user_checker_node)
        workflow.add_node("load_conversations", self._load_conversations_node)
        workflow.add_node("new_user_handler", self._new_user_handler_node)
        workflow.add_node("message_analyzer", self._message_analyzer_node)
        workflow.add_node("product_details_agent", self._product_details_agent_node)
        workflow.add_node("inventory_management_agent", self._inventory_management_agent_node)
        workflow.add_node("product_comparison_agent", self._product_comparison_agent_node)

        workflow.set_entry_point("user_checker")

        workflow.add_conditional_edges(
            "user_checker",
            self._route_by_user_type,
            {
                "load_conversations": "load_conversations",
                "new_user": "new_user_handler"
            }
        )

        workflow.add_edge("load_conversations", "message_analyzer")
        workflow.add_edge("new_user_handler", "message_analyzer")

        workflow.add_conditional_edges(
            "message_analyzer",
            self._route_to_agent,
            {
                "product_details": "product_details_agent",
                "inventory_management": "inventory_management_agent",
                "product_comparison": "product_comparison_agent"
            }
        )

        workflow.add_edge("product_details_agent", END)
        workflow.add_edge("inventory_management_agent", END)
        workflow.add_edge("product_comparison_agent", END)
        
        return workflow.compile()
    
    def _user_checker_node(self, state: IntentRouterState):
        """Check if user is new or existing"""
        phone_no = state["phone_no"]
        whatsapp_name = state["whatsapp_name"]
        
        customer_result = get_or_create_customer(phone_no, whatsapp_name)
        is_new_user = customer_result.get("created", False)
        
        return {
            "customer_data": customer_result,
            "is_new_user": is_new_user
        }
    
    def _route_by_user_type(self, state: IntentRouterState):
        """Route based on user type"""
        if state["is_new_user"]:
            return "new_user"
        else:
            return "load_conversations"
    
    def _load_conversations_node(self, state: IntentRouterState):
        """Load previous conversations for existing users"""
        phone_no = state["phone_no"]
        
        conversation_result = load_previous_conversations_to_redis(phone_no, limit=20)
        
        return {"previous_conversations": conversation_result}
    
    def _new_user_handler_node(self, state: IntentRouterState):
        """Handle new users - no conversation loading needed"""
        return {"previous_conversations": {"loaded": False, "message": "New user - no previous conversations"}}
    
    def _message_analyzer_node(self, state: IntentRouterState):
        """Analyze user message using Gemini LLM to categorize intent"""
        user_message = state["user_message"]
        
        system_prompt = """You are a message categorization expert. Analyze the user's message and classify it into ONE of these categories:

1. PRODUCT_DETAILS - User wants information about products, specifications, features, pricing, availability
2. INVENTORY_MANAGEMENT - User wants to check order status, place an order, return an item, track shipments
3. PRODUCT_COMPARISON - User wants to compare products with others in the market, features comparison, vs other brands

Respond with ONLY the category name: PRODUCT_DETAILS, INVENTORY_MANAGEMENT, or PRODUCT_COMPARISON"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Categorize this message: '{user_message}'")
        ]
        
        response = self.llm.invoke(messages)
        category = response.content.strip().upper()

        valid_categories = ["PRODUCT_DETAILS", "INVENTORY_MANAGEMENT", "PRODUCT_COMPARISON"]
        if category not in valid_categories:
            category = "PRODUCT_DETAILS" 
        
        return {"message_category": category}
    
    def _route_to_agent(self, state: IntentRouterState):
        """Route to appropriate AI agent based on message category"""
        category = state["message_category"]
        
        if category == "PRODUCT_DETAILS":
            return "product_details"
        elif category == "INVENTORY_MANAGEMENT":
            return "inventory_management"
        elif category == "PRODUCT_COMPARISON":
            return "product_comparison"
        else:
            return "product_details"  
    
    def _product_details_agent_node(self, state: IntentRouterState):
        """PRODUCT_DETAILS AI Agent - handles product information requests"""
        user_message = state["user_message"]
        phone_no = state["phone_no"]
        customer_data = state["customer_data"]
        previous_conversations = state["previous_conversations"]

        chat_context = manage_session_chat_history(phone_no, get_context=True)
        formatted_context = chat_context.get("context", "No previous conversation.")

        agent_response = self.product_details_agent.process_message(
            user_message, phone_no, customer_data, previous_conversations, formatted_context
        )
        
        manage_session_chat_history(phone_no, user_message, agent_response)
        
        return {"agent_response": agent_response}
    
    def _inventory_management_agent_node(self, state: IntentRouterState):
        """INVENTORY_MANAGEMENT AI Agent - handles orders, returns, status checks"""
        user_message = state["user_message"]
        phone_no = state["phone_no"]
        customer_data = state["customer_data"]
        previous_conversations = state["previous_conversations"]
        
        agent_response = self.inventory_management_agent.process_message(user_message, phone_no, customer_data, previous_conversations)

        chat_context = manage_session_chat_history(phone_no, get_context=True)
        formatted_context = chat_context.get("context", "No previous conversation.")
        

        agent_response = self.product_details_agent.process_message(
            user_message, phone_no, customer_data, previous_conversations, formatted_context
        )

        manage_session_chat_history(phone_no, user_message, agent_response)

        return {"agent_response": agent_response}
    
    def _product_comparison_agent_node(self, state: IntentRouterState):
        """PRODUCT_COMPARISON AI Agent - handles product comparisons"""
        user_message = state["user_message"]
        phone_no = state["phone_no"]
        customer_data = state["customer_data"]
        previous_conversations = state["previous_conversations"]

        agent_response = self.product_comparison_agent.process_message(user_message, phone_no, customer_data, previous_conversations)

        chat_context = manage_session_chat_history(phone_no, get_context=True)
        formatted_context = chat_context.get("context", "No previous conversation.")

        agent_response = self.product_details_agent.process_message(
            user_message, phone_no, customer_data, previous_conversations, formatted_context
        )

        manage_session_chat_history(phone_no, user_message, agent_response)

        return {"agent_response": agent_response}
    
    def process_user_message(self, phone_no: str, user_message: str, whatsapp_name: str = "Unknown"):
        """Full workflow: Check user → Load conversations → Analyze → Route to appropriate AI agent"""
        result = self.graph.invoke({
            "messages": [],
            "phone_no": phone_no,
            "whatsapp_name": whatsapp_name,
            "user_message": user_message,
            "customer_data": {},
            "is_new_user": False,
            "previous_conversations": {},
            "message_category": "",
            "agent_response": ""
        })
        
        return {
            "is_new_user": result["is_new_user"],
            "customer_data": result["customer_data"],
            "previous_conversations": result["previous_conversations"],
            "message_category": result["message_category"],
            "agent_response": result["agent_response"],
            "user_message": user_message,
            "phone_no": phone_no
        }

        