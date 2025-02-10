-- Insert Admin User
INSERT INTO users (username, password, is_admin) VALUES (
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewLxNfEc5Zzd6G5K', -- password: admin1234
    TRUE
);

-- Insert Sample Users
INSERT INTO users (username, password, is_admin) VALUES
('john_doe', '$2b$12$abcdefghijABCDEFGHIJ/uvwxyzUVWXYZ1234567890abcdefghi', FALSE),
('jane_doe', '$2b$12$1234567890ABCDEFGHIJabcdefghij/uvwxyzUVWXYZabcdefghi', FALSE);

-- Insert Sample Products
INSERT INTO products (name, price, description, stock) VALUES
('iPhone 15 Pro', 999.99, 'Latest iPhone model with advanced features', 50),
('iPad Air', 749.99, 'Powerful and portable iPad', 30),
('Samsung Galaxy S24', 899.99, 'Latest Android flagship phone', 40),
('Xbox Series X', 499.99, 'Next-gen gaming console', 25),
('PS5', 499.99, 'PlayStation 5 gaming console', 20);

-- Insert Sample Orders
INSERT INTO orders (user_id, total_amount, status) VALUES
(2, 1749.98, 'completed'),
(3, 499.99, 'pending');

-- Insert Sample Order Items
INSERT INTO order_items (order_id, product_id, quantity, price_at_time) VALUES
(1, 1, 1, 999.99),
(1, 2, 1, 749.99),
(2, 4, 1, 499.99);

-- Insert Sample Cart Items
INSERT INTO cart_items (user_id, product_id, quantity) VALUES
(2, 3, 1),
(3, 1, 1);