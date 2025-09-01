const express = require('express');
const axios = require('axios');
const twilio = require('twilio');
const router = express.Router();

// Initialize Twilio client lazily (after env is loaded)
let twilioClient;

function getTwilioClient() {
  if (!twilioClient) {
    twilioClient = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);
  }
  return twilioClient;
}

// Twilio webhook endpoint
router.post('/webhook', async (req, res) => {
  try {
    console.log('📱 Raw Twilio webhook data:', req.body);
    console.log('📱 Headers:', req.headers);
    
    // Handle both URL-encoded and JSON data from Twilio
    const from = req.body.From || req.body.from;
    const messageBody = req.body.Body || req.body.body || '';
    const profileName = req.body.ProfileName || req.body.profileName || 'WhatsApp User';
    
    if (!from) {
      console.log('❌ No From field found in request');
      return res.sendStatus(400);
    }
    
    // Clean phone number (remove whatsapp: prefix)
    const phoneNumber = from.replace('whatsapp:', '');
    
    console.log(`📱 Processing WhatsApp message from ${phoneNumber}: "${messageBody}"`);
    
    // Process message through your existing pipeline
    await processWhatsAppMessage(phoneNumber, messageBody, profileName);
    
    res.sendStatus(200);
  } catch (error) {
    console.error('❌ Error processing Twilio webhook:', error);
    res.sendStatus(500);
  }
});

// Health check endpoint
router.get('/webhook', (req, res) => {
  res.status(200).send('Twilio WhatsApp webhook is ready!');
});

async function processWhatsAppMessage(phone_number, message_text, sender_name) {
  try {
    console.log(`🔄 Processing message: ${message_text} from ${phone_number}`);
    
    console.log('🤖 Calling Python agent...');
    const agentResponse = await axios.post('http://localhost:5000/agent', {
      query: message_text,
      phone_number: phone_number,
      whatsapp_name: sender_name  // Add this line
    });
    
    const botResponse = agentResponse.data.response;
    console.log(`🤖 Agent response: ${botResponse}`);
    
    // Send response back to WhatsApp
    if (botResponse && botResponse.trim() !== '') {
      await sendTwilioWhatsAppMessage(phone_number, botResponse);
    }
    
  } catch (error) {
    console.error('❌ Error processing message:', error);
    await sendTwilioWhatsAppMessage(phone_number, "Sorry, I'm having trouble processing your request right now.");
  }
}


// Add this new function to send messages via Twilio
async function sendTwilioWhatsAppMessage(phone_number, message) {
  try {
    const client = getTwilioClient(); // Use lazy initialization
    const response = await client.messages.create({
      body: message,
      from: process.env.TWILIO_PHONE_NUMBER,
      to: `whatsapp:${phone_number}`
    });
    
    console.log(`✅ Twilio message sent to ${phone_number}: ${response.sid}`);
  } catch (error) {
    console.error('❌ Error sending Twilio WhatsApp message:', error);
    console.error('Error details:', error.message);
  }
}

module.exports = router;