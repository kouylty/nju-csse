CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    order_no TEXT NOT NULL UNIQUE,
    buyer_id INTEGER NOT NULL REFERENCES users(id),
    seller_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    request_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents > 0),
    postage_cents INTEGER NOT NULL CHECK (postage_cents >= 0),
    total_cents INTEGER NOT NULL CHECK (total_cents = unit_price_cents * quantity + postage_cents),
    delivery_mode TEXT NOT NULL CHECK (delivery_mode IN ('MEET', 'POST', 'SERVICE')),
    snapshot_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('UNPAID', 'WAITING_DELIVERY', 'SERVICE_READY', 'SERVICE_ACTIVE', 'DELIVERED', 'COMPLETED', 'CLOSED')),
    reservation_state TEXT NOT NULL CHECK (reservation_state IN ('HELD', 'RELEASED', 'CONSUMED')),
    created_at TEXT NOT NULL,
    pay_due_at TEXT NOT NULL,
    paid_at TEXT,
    delivered_at TEXT,
    auto_confirm_at TEXT,
    completed_at TEXT,
    closed_at TEXT,
    close_reason TEXT,
    dispute_open INTEGER NOT NULL DEFAULT 0 CHECK (dispute_open IN (0, 1)),
    UNIQUE (buyer_id, request_key),
    CHECK (buyer_id != seller_id),
    CHECK ((status = 'COMPLETED' AND reservation_state = 'CONSUMED') OR
           (status = 'CLOSED' AND reservation_state IN ('RELEASED', 'CONSUMED')) OR
           (status IN ('UNPAID', 'WAITING_DELIVERY', 'SERVICE_READY', 'SERVICE_ACTIVE', 'DELIVERED') AND reservation_state = 'HELD'))
);
CREATE UNIQUE INDEX idx_orders_one_unpaid ON orders(buyer_id, product_id) WHERE status = 'UNPAID';
CREATE INDEX idx_orders_buyer ON orders(buyer_id, status, id);
CREATE INDEX idx_orders_seller ON orders(seller_id, status, id);
CREATE INDEX idx_orders_expiry ON orders(status, pay_due_at, product_id);
CREATE INDEX idx_orders_reservations ON orders(product_id, reservation_state);

CREATE TABLE order_images (
    order_id INTEGER NOT NULL REFERENCES orders(id),
    file_id INTEGER NOT NULL REFERENCES files(id),
    PRIMARY KEY (order_id, file_id)
);

CREATE TABLE fund_transactions (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    kind TEXT NOT NULL CHECK (kind IN ('PAYMENT', 'REFUND', 'SETTLEMENT')),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    operation_key TEXT NOT NULL UNIQUE,
    actor_id INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    UNIQUE (order_id, kind)
);
CREATE INDEX idx_funds_order ON fund_transactions(order_id, id);

CREATE TRIGGER immutable_order_contract
BEFORE UPDATE OF order_no, buyer_id, seller_id, product_id, request_key, request_fingerprint,
    quantity, unit_price_cents, postage_cents, total_cents, delivery_mode, snapshot_json ON orders
BEGIN
    SELECT RAISE(ABORT, 'order contract is immutable');
END;
CREATE TRIGGER immutable_fund_update BEFORE UPDATE ON fund_transactions
BEGIN
    SELECT RAISE(ABORT, 'fund records are append only');
END;
CREATE TRIGGER immutable_fund_delete BEFORE DELETE ON fund_transactions
BEGIN
    SELECT RAISE(ABORT, 'fund records are append only');
END;
