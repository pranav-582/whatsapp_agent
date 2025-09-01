const axios = require('axios');

async function sendRequest(id) {
  try {
    const start = Date.now();
    const response = await axios.post('http://localhost:3000/api/whatsapp/webhook', {
      phone_number: ['9876543210', '9876501234'][id % 2], // Alternate between existing customers
      message: 'Where is my order?',
      sender_name: `TestUser${id}`
    }, {
      timeout: 30000 // 30 second timeout
    });
    
    const duration = Date.now() - start;
    return { success: true, duration, id };
  } catch (error) {
    return { success: false, error: error.message, id };
  }
}

async function concurrentTest(numRequests) {
  console.log(`🧪 Testing ${numRequests} CONCURRENT requests...`);
  
  const promises = [];
  for (let i = 1; i <= numRequests; i++) {
    promises.push(sendRequest(i));
  }
  
  const start = Date.now();
  const results = await Promise.all(promises);
  const totalTime = Date.now() - start;
  
  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  
  console.log(`\n📊 RESULTS:`);
  console.log(`✅ Successful: ${successful.length}/${numRequests}`);
  console.log(`❌ Failed: ${failed.length}/${numRequests}`);
  console.log(`⏱️ Total time: ${totalTime}ms`);
  console.log(`📈 Avg response time: ${successful.reduce((sum, r) => sum + r.duration, 0) / successful.length || 0}ms`);
  
  if (failed.length > 0) {
    console.log(`\n❌ Failed requests:`, failed.slice(0, 3)); // Show first 3 failures
  }
}

// Test progressively higher loads
async function progressiveTest() {
    const testSizes = [1000]; // Start small and increase
  
  for (const size of testSizes) {
    await concurrentTest(size);
    console.log(`\n⏳ Waiting 5 seconds before next test...\n`);
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}

progressiveTest().catch(console.error);