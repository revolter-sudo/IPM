-- Create the default_config table
CREATE TABLE IF NOT EXISTS default_config (
    id SERIAL PRIMARY KEY,
    uuid UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    item_id UUID NOT NULL REFERENCES items(uuid),
    admin_amount FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);
