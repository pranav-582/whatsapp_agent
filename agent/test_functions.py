import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'agent'))

from functions import get_products, place_order, process_return

def test_order_and_return():
    print("🧪 Testing Order and Return Flow")
    print("=" * 50)
    
    phone_no = "+1234567890"
    customer_name = "John Doe"
    product_name = "Levi's T-Shirt"
    size = ""
    quantity = 1
    
    # Step 1: Check initial stock
    print("📦 Step 1: Check initial stock")
    initial_products = get_products(product_name)
    if initial_products['found']:
        for product in initial_products['products']:
            if product['size'] == size:
                initial_stock = product['stock_quantity']
                print(f"   Initial stock for {product_name} ({size}): {initial_stock}")
                break
    else:
        print("   ❌ Product not found")
        return
    
    # Step 2: Place order
    print(f"\n🛒 Step 2: Place order for {quantity}x {product_name} ({size})")
    order_result = place_order(phone_no, product_name, size, quantity, customer_name)
    
    if order_result['success']:
        order_id = order_result['order_id']
        print(f"   ✅ Order placed successfully! Order ID: {order_id}")
        print(f"   Total amount: ${order_result['total_amount']:.2f}")
    else:
        print(f"   ❌ Order failed: {order_result['message']}")
        return
    
    # Step 3: Check stock after order
    print("\n📦 Step 3: Check stock after order")
    after_order_products = get_products(product_name)
    if after_order_products['found']:
        for product in after_order_products['products']:
            if product['size'] == size:
                after_order_stock = product['stock_quantity']
                print(f"   Stock after order: {after_order_stock}")
                print(f"   Stock reduced by: {initial_stock - after_order_stock}")
                break
    
    # Step 4: Process return
    print(f"\n🔄 Step 4: Process return for Order #{order_id}")
    return_result = process_return(phone_no, order_id, "Testing return process")
    
    if return_result['success']:
        return_id = return_result['return_id']
        print(f"   ✅ Return processed successfully! Return ID: {return_id}")
        print(f"   Refund amount: ${return_result['refund_amount']:.2f}")
        print(f"   Stock restored: {return_result.get('stock_restored', 'Unknown')}")
    else:
        print(f"   ❌ Return failed: {return_result['message']}")
        return
    
    # Step 5: Check final stock
    print("\n📦 Step 5: Check stock after return")
    final_products = get_products(product_name)
    if final_products['found']:
        for product in final_products['products']:
            if product['size'] == size:
                final_stock = product['stock_quantity']
                print(f"   Final stock: {final_stock}")
                
                # Verify stock is restored
                if final_stock == initial_stock:
                    print("   ✅ SUCCESS: Stock fully restored!")
                elif final_stock == after_order_stock + quantity:
                    print("   ✅ SUCCESS: Stock correctly increased by returned quantity!")
                else:
                    print(f"   ❌ ERROR: Stock mismatch. Expected {initial_stock}, got {final_stock}")
                break
    
    # Summary
    print("\n📊 SUMMARY:")
    print(f"   Initial stock: {initial_stock}")
    print(f"   After order: {after_order_stock} (reduced by {quantity})")
    print(f"   After return: {final_stock}")
    print(f"   Order ID: {order_id}")
    print(f"   Return ID: {return_id}")

if __name__ == "__main__":
    test_order_and_return()