# WhatsApp Customer Support Agent

An intelligent WhatsApp-based customer support system that automates customer service queries using a LangChain/LangGraph multi-agent architecture with persistent conversation memory.

## Overview

This project implements a sophisticated WhatsApp chatbot that handles:
- Order Management: Check status, place orders, process returns
- Product Information: Inventory checks, product details, availability
- Product Comparisons: External API integration for competitive analysis
- Conversation Context: Redis-based session memory with PostgreSQL persistence

## Architecture

- Node.js Backend: Webhook handling, real-time messaging
- Python AI Agent: LangChain/LangGraph intelligent routing
- PostgreSQL: Customer, product, and order data
- Redis: Session management and chat history caching

### Data Flow

WhatsApp → Twilio → Node.js → Python Agent → LangGraph → Database

## Key Features

### Multi-Agent Intelligence

- ProductDetailsAgent: Handles inventory and product queries
- InventoryManagementAgent: Manages orders, returns, and status checks
- ProductComparisonAgent: External research via SerperAPI

### Persistent Memory System

- Redis Sessions: 30-minute active conversation context
- PostgreSQL Storage: Long-term customer relationship history
- Context-Aware Responses: AI remembers previous interactions

### Natural Language Processing

- Intent classification and routing
- Context-aware response generation
- Specialized prompts for each agent type

## Tech Stack

| Component      | Technology                | Purpose                        |
|----------------|--------------------------|--------------------------------|
| Messaging      | Twilio WhatsApp API       | Message delivery               |
| Backend        | Node.js + Express         | Webhook handling               |
| AI Engine      | Python + LangChain/LangGraph | Intent routing and processing |
| LLM            | Google Gemini 2.0 Flash   | Natural language generation    |
| Database       | PostgreSQL                | Persistent data storage        |
| Cache          | Redis                     | Session and context management |
| External API   | SerpAPI                   | Product comparison data        |

## Project Structure

whatsapp_agent/
├── backend/                # Node.js API server  
│   ├── routes/whatsapp.js  # Twilio webhook endpoints  
│   ├── utils/redis_client.js # Redis connection  
│   └── index.js            # Main server entry  
├── agent/                  # Python AI system  
│   ├── pathing.py          # FastAPI endpoints  
│   ├── intent_router.py    # LangGraph workflow  
│   ├── ai_agents.py        # Specialized AI agents  
│   └── functions.py        # Database and utility functions  

## Performance Features

- Redis Caching: Reduces database load significantly
- Async Processing: Non-blocking webhook responses
- Session Management: 30-minute context windows
- Error Handling: Graceful fallbacks and logging

## Use Cases Demonstrated

| Query Type    | Example                      | Agent Used                |
|---------------|------------------------------|---------------------------|
| Product Info  | "Do you have iPhone 15?"     | ProductDetailsAgent       |
| Order Status  | "Where is my order?"         | InventoryManagementAgent  |
| Returns       | "I want to return my shoes"  | InventoryManagementAgent  |
| Comparisons   | "iPhone vs Samsung Galaxy"   | ProductComparisonAgent    |

## Key Technical Decisions

### Why Hybrid Architecture

- Node.js: Excellent for webhook handling and concurrent connections
- Python: Rich AI/ML ecosystem (LangChain, Redis-py, PostgreSQL adapters)
- Separation of Concerns: Webhook reliability versus AI processing complexity

### Why LangGraph

- Conditional Routing: Intelligent agent selection based on intent
- State Management: Maintains conversation context across nodes
- Extensibility: Easy to add new agent types and workflows

## Scalability Considerations

- Horizontal Scaling: Each service can scale independently
- Database Optimization: Indexed queries and connection pooling
- Caching Strategy: Multi-layer caching (Redis and in-memory)
- Load Balancing: Health check endpoints for container