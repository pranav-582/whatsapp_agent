const CustomerService = require('../services/customer_service');

async function testCustomerService() {
  try {
    const cs = new CustomerService();
    
    // Test customer creation
    const customer = await cs.getOrCreateCustomer('9876543210', 'John Doe');
    console.log('✅ Customer result:', customer);
    
    // Test getting existing customer
    const existingCustomer = await cs.getOrCreateCustomer('9876543210', 'John Doe');
    console.log('✅ Existing customer:', existingCustomer);
    
    console.log('🎉 Customer service working!');
    process.exit(0);
  } catch (error) {
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

testCustomerService();
