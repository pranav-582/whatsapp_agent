const { Pool } = require('pg');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../../.env') });

class CustomerService {
  constructor() {
    console.log('Database URL:', process.env.DATABASE_URL);
    this.pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      max: 50,
      idleTimeoutMillis: 10000,
      connectionTimeoutMillis: 5000,
      acquireTimeoutMillis: 10000
    });
  }

  async getOrCreateCustomer(phoneNumber, whatsappName = null) {
    try {
      // Check if customer exists
      const result = await this.pool.query(
        'SELECT * FROM customers WHERE phone_no = $1',
        [phoneNumber]
      );

      if (result.rows.length > 0) {
        console.log(`✅ Existing customer found: ${phoneNumber}`);
        // Add customer_id field for compatibility
        const customer = result.rows[0];
        customer.customer_id = customer.phone_no; // Use phone_no as customer_id
        return customer;
      }

      // Create new customer
      const newCustomer = await this.pool.query(
        `INSERT INTO customers (phone_no, customer_name)
         VALUES ($1, $2)
         RETURNING *`,
        [phoneNumber, whatsappName || 'WhatsApp User']
      );

      console.log(`✅ New customer created: ${phoneNumber}`);
      // Add customer_id field for compatibility
      const customer = newCustomer.rows[0];
      customer.customer_id = customer.phone_no; // Use phone_no as customer_id
      return customer;

    } catch (error) {
      console.error('Error managing customer:', error);
      throw error;
    }
  }
}

module.exports = CustomerService;