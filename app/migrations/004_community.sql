CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    buyer_id INTEGER NOT NULL REFERENCES users(id),
    seller_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (product_id, buyer_id),
    CHECK (buyer_id != seller_id)
);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    sender_id INTEGER NOT NULL REFERENCES users(id),
    order_id INTEGER REFERENCES orders(id),
    body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 2000),
    client_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (sender_id, client_key)
);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, id);
CREATE INDEX idx_conversations_buyer ON conversations(buyer_id, updated_at);
CREATE INDEX idx_conversations_seller ON conversations(seller_id, updated_at);
CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    author_id INTEGER NOT NULL REFERENCES users(id),
    recipient_id INTEGER NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 1000),
    created_at TEXT NOT NULL,
    UNIQUE (order_id, author_id),
    CHECK (author_id != recipient_id)
);
CREATE INDEX idx_evaluations_recipient ON evaluations(recipient_id, id);
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    object_type TEXT NOT NULL CHECK (object_type IN ('PRODUCT', 'ORDER', 'CONVERSATION', 'CASE')),
    object_id INTEGER NOT NULL,
    event_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT,
    UNIQUE (user_id, event_key)
);
CREATE INDEX idx_notifications_user ON notifications(user_id, read_at, id);
CREATE TABLE cases (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('PRODUCT_REPORT', 'CHAT_REPORT', 'DISPUTE')),
    reporter_id INTEGER NOT NULL REFERENCES users(id),
    respondent_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    conversation_id INTEGER REFERENCES conversations(id),
    order_id INTEGER REFERENCES orders(id),
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'PROCESSING', 'RESOLVED')),
    handler_id INTEGER REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    resolution TEXT,
    decision TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    CHECK (reporter_id != respondent_id),
    CHECK ((kind = 'PRODUCT_REPORT' AND order_id IS NULL AND conversation_id IS NULL) OR
           (kind = 'CHAT_REPORT' AND conversation_id IS NOT NULL AND order_id IS NULL) OR
           (kind = 'DISPUTE' AND order_id IS NOT NULL)),
    CHECK ((status = 'OPEN' AND handler_id IS NULL) OR (status != 'OPEN' AND handler_id IS NOT NULL))
);
CREATE UNIQUE INDEX idx_cases_one_dispute ON cases(order_id)
    WHERE kind = 'DISPUTE' AND status != 'RESOLVED';
CREATE INDEX idx_cases_queue ON cases(status, kind, id);
CREATE INDEX idx_cases_parties ON cases(reporter_id, respondent_id, id);
CREATE TABLE case_actions (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id),
    actor_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,
    body TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX idx_case_actions_case ON case_actions(case_id, id);
CREATE TABLE case_images (
    action_id INTEGER NOT NULL REFERENCES case_actions(id),
    file_id INTEGER NOT NULL REFERENCES files(id),
    PRIMARY KEY (action_id, file_id)
);
CREATE TRIGGER immutable_message_update BEFORE UPDATE ON messages
BEGIN SELECT RAISE(ABORT, 'messages are append only'); END;
CREATE TRIGGER immutable_message_delete BEFORE DELETE ON messages
BEGIN SELECT RAISE(ABORT, 'messages are append only'); END;
CREATE TRIGGER immutable_evaluation_update BEFORE UPDATE ON evaluations
BEGIN SELECT RAISE(ABORT, 'evaluations are immutable'); END;
CREATE TRIGGER immutable_evaluation_delete BEFORE DELETE ON evaluations
BEGIN SELECT RAISE(ABORT, 'evaluations are immutable'); END;
CREATE TRIGGER immutable_case_action_update BEFORE UPDATE ON case_actions
BEGIN SELECT RAISE(ABORT, 'case history is append only'); END;
CREATE TRIGGER immutable_case_action_delete BEFORE DELETE ON case_actions
BEGIN SELECT RAISE(ABORT, 'case history is append only'); END;
