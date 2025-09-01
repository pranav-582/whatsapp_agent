const axios = require('axios');
const readline = require('readline');

class ConversationTester {
  constructor() {
    this.phoneNumber = '+9971720258';
    this.conversationHistory = [];
  }

  // Test a single message and show response
  async testMessage(message) {
    try {
      console.log(`\n🔵 USER: ${message}`);
      
      const twilioPayload = {
        From: `whatsapp:${this.phoneNumber}`,
        To: 'whatsapp:+14155238886',
        Body: message,
        ProfileName: 'Test User'
      };

      const startTime = Date.now();
      
      // Send to webhook (simulates WhatsApp → Backend → Python Agent)
      const response = await axios.post('http://localhost:3000/api/whatsapp/webhook', twilioPayload, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        }
      });

      const duration = Date.now() - startTime;

      if (response.status === 200) {
        console.log(`✅ Message processed successfully (${duration}ms)`);
        
        // Store in conversation history
        this.conversationHistory.push({
          user: message,
          timestamp: new Date().toISOString(),
          status: 'sent'
        });

        // Wait a moment for processing
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        console.log(`🤖 AGENT: [Response sent via WhatsApp/logged - check backend logs]`);
        
      } else {
        console.log(`❌ Failed with status: ${response.status}`);
      }

    } catch (error) {
      console.error(`❌ Error: ${error.response?.status} - ${error.response?.data || error.message}`);
    }
  }

  // Test direct Python agent (bypasses WhatsApp webhook)
  async testDirectAgent(message) {
    try {
      console.log(`\n🔵 USER (Direct): ${message}`);
      
      const startTime = Date.now();
      
      const response = await axios.post('http://localhost:5000/agent', {
        query: message,
        phone_number: this.phoneNumber
      }, {
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const duration = Date.now() - startTime;
      
      if (response.data) {
        console.log(`✅ Direct agent response (${duration}ms):`);
        console.log(`🤖 AGENT: ${response.data.response}`);
        console.log(`📊 Intent: ${response.data.intent}`);
        console.log(`🏷️  Entities: ${JSON.stringify(response.data.entities)}`);
        console.log(`🔧 Agent Used: ${response.data.agent_used}`);
        
        this.conversationHistory.push({
          user: message,
          agent: response.data.response,
          intent: response.data.intent,
          entities: response.data.entities,
          agent_used: response.data.agent_used,
          duration: duration,
          timestamp: new Date().toISOString()
        });
      }

    } catch (error) {
      console.error(`❌ Direct agent error: ${error.response?.data || error.message}`);
    }
  }

  // Run predefined test scenarios
  async runTestScenarios() {
    console.log('\n🧪 Running Test Scenarios...\n');

    const scenarios = [
      // Greeting
      'Hello',
      
      // Product inquiry
      'What products do you have?',
      
      // Specific product
      'Tell me about iPhone 15',
      
      // Stock check
      'Do you have iPhone 15 in stock?',
      
      // Order placement
      'I want to buy iPhone 15',
      
      // Order status
      'Where is my order?',
      
      // Product comparison
      'Compare iPhone 15 vs Samsung Galaxy S24',
      
      // Acknowledgment
      'OK'
    ];

    for (let i = 0; i < scenarios.length; i++) {
      console.log(`\n--- Test ${i + 1}/${scenarios.length} ---`);
      await this.testDirectAgent(scenarios[i]);
      
      // Wait between tests
      if (i < scenarios.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }

    this.showSummary();
  }

  // Interactive conversation mode
  async startInteractiveMode() {
    console.log('\n💬 Interactive Conversation Mode');
    console.log('Type messages to chat with the agent. Type "exit" to quit, "webhook" to test via webhook, "scenarios" to run test scenarios.\n');

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    const askQuestion = () => {
      rl.question('YOU: ', async (message) => {
        if (message.toLowerCase() === 'exit') {
          console.log('\n👋 Goodbye!');
          this.showSummary();
          rl.close();
          return;
        }

        if (message.toLowerCase() === 'webhook') {
          await this.testMessage(message);
          askQuestion();
          return;
        }

        if (message.toLowerCase() === 'scenarios') {
          await this.runTestScenarios();
          askQuestion();
          return;
        }

        if (message.toLowerCase() === 'history') {
          this.showHistory();
          askQuestion();
          return;
        }

        await this.testDirectAgent(message);
        askQuestion();
      });
    };

    askQuestion();
  }

  // Show conversation history
  showHistory() {
    console.log('\n📜 Conversation History:');
    this.conversationHistory.forEach((turn, index) => {
      console.log(`\n${index + 1}. ${turn.timestamp}`);
      console.log(`   USER: ${turn.user}`);
      if (turn.agent) {
        console.log(`   AGENT: ${turn.agent}`);
        console.log(`   Intent: ${turn.intent} | Agent: ${turn.agent_used} | Time: ${turn.duration}ms`);
      }
    });
  }

  // Show test summary
  showSummary() {
    console.log('\n📊 Test Summary:');
    console.log(`Total interactions: ${this.conversationHistory.length}`);
    
    const intents = {};
    const agents = {};
    
    this.conversationHistory.forEach(turn => {
      if (turn.intent) {
        intents[turn.intent] = (intents[turn.intent] || 0) + 1;
      }
      if (turn.agent_used) {
        agents[turn.agent_used] = (agents[turn.agent_used] || 0) + 1;
      }
    });

    console.log('\nIntents detected:');
    Object.entries(intents).forEach(([intent, count]) => {
      console.log(`  ${intent}: ${count}`);
    });

    console.log('\nAgents used:');
    Object.entries(agents).forEach(([agent, count]) => {
      console.log(`  ${agent}: ${count}`);
    });
  }
}

// Main execution
async function main() {
  const tester = new ConversationTester();

  const args = process.argv.slice(2);
  
  if (args[0] === 'scenarios') {
    await tester.runTestScenarios();
  } else if (args[0] === 'single' && args[1]) {
    await tester.testDirectAgent(args.slice(1).join(' '));
  } else if (args[0] === 'webhook' && args[1]) {
    await tester.testMessage(args.slice(1).join(' '));
  } else {
    await tester.startInteractiveMode();
  }
}

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
  console.log('\n\n👋 Goodbye!');
  process.exit(0);
});

main().catch(console.error);