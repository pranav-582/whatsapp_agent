const express = require('express');
const axios = require('axios');
const app = express();
const PORT = process.env.PORT || 8000;

app.get('/health', (req, res) => {
  res.send('Backend is running!');
});

app.post('/webhook', express.json(), async (req, res) => {
  const userQuery = req.body.message; // Adjust based on WhatsApp payload structure

  // Forward to Python FastAPI agent
  try {
    const agentRes = await axios.post('http://localhost:5000/agent', { query: userQuery });
    const agentReply = agentRes.data.response;

    // TODO: Send agentReply back to WhatsApp user

    res.sendStatus(200);
  } catch (err) {
    console.error(err);
    res.sendStatus(500);
  }
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});