const axios = require('axios');

async function debugEntityExtraction() {
  console.log('🔍 Debugging Entity Extraction...\n');
  
  const testMessages = [
    'MacBook Air',
    'macbook air', 
    'do you have MacBook Air?',
    'iPhone 15',
    'iphone 15'
  ];

  for (const message of testMessages) {
    console.log(`\n--- Testing: "${message}" ---`);
    
    try {
      const response = await axios.post('http://localhost:5000/agent', {
        query: message,
        phone_number: '+9971720258'
      });

      console.log(`Intent: ${response.data.intent}`);
      console.log(`Entities: ${JSON.stringify(response.data.entities, null, 2)}`);
      console.log(`Agent: ${response.data.agent_used}`);
      console.log(`Response: ${response.data.response.substring(0, 100)}...`);
      
    } catch (error) {
      console.error(`Error: ${error.message}`);
    }
  }
}

debugEntityExtraction();