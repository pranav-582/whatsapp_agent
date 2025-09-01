const axios = require('axios');

console.log('🤖 WhatsApp Agent Chat Test');
console.log('Starting interactive mode...\n');

// Test if basic connection works first
async function testConnection() {
  try {
    console.log('Testing connection to Python agent...');
    const response = await axios.get('http://localhost:5000/health');
    console.log('✅ Python agent is running');
    
    console.log('\n💬 Type your messages below (Ctrl+C to exit):\n');
    startInteractiveMode();
    
  } catch (error) {
    console.error('❌ Cannot connect to Python agent:', error.message);
    process.exit(1);
  }
}

function startInteractiveMode() {
  const readline = require('readline');
  
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: 'YOU: '
  });

  rl.prompt();

  rl.on('line', async (input) => {
    const message = input.trim();
    
    if (message.toLowerCase() === 'exit') {
      console.log('\n👋 Goodbye!');
      rl.close();
      return;
    }

    if (message === '') {
      rl.prompt();
      return;
    }

    try {
      console.log(`\n🔵 Testing: "${message}"`);
      
      const response = await axios.post('http://localhost:5000/agent', {
        query: message,
        phone_number: '+9971720258'
      });

      console.log(`🤖 AGENT: ${response.data.response}`);
      console.log(`📊 Intent: ${response.data.intent} | Agent: ${response.data.agent_used}\n`);
      
    } catch (error) {
      console.error(`❌ Error: ${error.message}\n`);
    }

    rl.prompt();
  });

  rl.on('close', () => {
    console.log('\nChat ended.');
    process.exit(0);
  });
}

testConnection();