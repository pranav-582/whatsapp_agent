const express = require('express');
const path = require('path');
const { connectRedis } = require('./utils/redis_client');
const whatsappRoutes = require('./routes/whatsapp');

require('dotenv').config({ path: path.join(__dirname, '../.env') });

const app = express();
const PORT = process.env.NODE_PORT || 3000;

// Middleware - Add URL-encoded parser for Twilio
app.use(express.json());
app.use(express.urlencoded({ extended: true })); // Add this line

// Routes
app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

app.use('/api/whatsapp', whatsappRoutes);

// Start server
async function startServer() {
  try {
    await connectRedis();
    
    app.listen(PORT, () => {
      console.log(`🚀 Backend server running on port ${PORT}`);
      console.log(`📱 WhatsApp webhook: http://localhost:${PORT}/api/whatsapp/webhook`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();