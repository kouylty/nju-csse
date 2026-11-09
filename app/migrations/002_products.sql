CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    storage_key TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
    width INTEGER NOT NULL CHECK (width > 0),
    height INTEGER NOT NULL CHECK (height > 0),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    seller_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    product_type TEXT NOT NULL DEFAULT 'GOODS' CHECK (product_type IN ('GOODS', 'SERVICE')),
    price_cents INTEGER CHECK (price_cents > 0),
    available_stock INTEGER NOT NULL DEFAULT 1 CHECK (available_stock >= 0),
    allow_post INTEGER NOT NULL DEFAULT 0 CHECK (allow_post IN (0, 1)),
    allow_meet INTEGER NOT NULL DEFAULT 1 CHECK (allow_meet IN (0, 1)),
    free_shipping INTEGER NOT NULL DEFAULT 1 CHECK (free_shipping IN (0, 1)),
    postage_cents INTEGER NOT NULL DEFAULT 0 CHECK (postage_cents >= 0),
    meeting_description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PENDING', 'REJECTED', 'PUBLISHED', 'OFFLINE', 'BLOCKED')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    rectification_note TEXT NOT NULL DEFAULT '',
    moderation_reason TEXT NOT NULL DEFAULT '',
    rectification_requested_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_products_search ON products(status, category, product_type, price_cents);
CREATE INDEX IF NOT EXISTS idx_products_seller ON products(seller_id, status, id);

CREATE TABLE IF NOT EXISTS product_images (
    product_id INTEGER NOT NULL REFERENCES products(id),
    file_id INTEGER NOT NULL REFERENCES files(id),
    position INTEGER NOT NULL,
    PRIMARY KEY (product_id, file_id),
    UNIQUE (product_id, position)
);

CREATE TABLE IF NOT EXISTS product_reviews (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    submitted_json TEXT NOT NULL,
    result TEXT NOT NULL DEFAULT 'PENDING' CHECK (result IN ('PENDING', 'APPROVED', 'REJECTED')),
    reviewer_id INTEGER REFERENCES users(id),
    reason TEXT NOT NULL DEFAULT '',
    submitted_at TEXT NOT NULL,
    reviewed_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_pending ON product_reviews(product_id)
    WHERE result = 'PENDING';

CREATE TABLE IF NOT EXISTS review_images (
    review_id INTEGER NOT NULL REFERENCES product_reviews(id),
    file_id INTEGER NOT NULL REFERENCES files(id),
    PRIMARY KEY (review_id, file_id)
);
