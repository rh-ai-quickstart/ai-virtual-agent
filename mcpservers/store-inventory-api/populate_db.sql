-- Sample data for Store Inventory API Database
-- This script populates the database with initial product data

INSERT INTO products (name, description, inventory, price) VALUES
('Laptop', 'High-performance laptop for work and gaming', 50, 999.99),
('Wireless Mouse', 'Ergonomic wireless mouse with long battery life', 200, 29.99),
('Mechanical Keyboard', 'RGB mechanical keyboard with blue switches', 75, 149.99),
('Monitor', '27-inch 4K monitor with USB-C connectivity', 30, 399.99),
('Webcam', 'HD webcam with auto-focus and noise cancellation', 100, 89.99),
('Headphones', 'Noise-cancelling over-ear headphones', 80, 199.99),
('USB Cable', 'USB-C to USB-A cable, 6 feet long', 500, 12.99),
('Desk Lamp', 'Adjustable LED desk lamp with touch controls', 40, 59.99),
('Phone Charger', 'Fast wireless charging pad', 150, 39.99),
('Tablet', '10-inch tablet with stylus support', 60, 299.99)
ON CONFLICT (name) DO NOTHING;
