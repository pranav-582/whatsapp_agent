const axios = require('axios');

async function testTwilioWebhook() {
  try {
    // Test with Twilio webhook format
    const twilioPayload = {
      From: 'whatsapp:+9971720258',
      To: 'whatsapp:+14155238886',
      Body: 'Tell me price of iphone 15',
      ProfileName: 'Test User'
    };
    
    const response = await axios.post('http://localhost:3000/api/whatsapp/webhook', twilioPayload, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      }
    });
    
    console.log('✅ Twilio webhook test successful:', response.status);
  } catch (error) {
    console.error('❌ Twilio webhook test failed:', error.response?.status, error.response?.data || error.message);
  }
}

testTwilioWebhook();