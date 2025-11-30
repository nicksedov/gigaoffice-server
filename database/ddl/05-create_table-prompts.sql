-- Prompts table
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template TEXT NOT NULL,
    category_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER
);

-- Add foreign key constraint for prompts -> categories
ALTER TABLE prompts ADD CONSTRAINT fk_prompts_category 
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL;

-- Create indexes for prompts table
CREATE INDEX IF NOT EXISTS idx_prompts_is_active ON prompts(is_active);
CREATE INDEX IF NOT EXISTS idx_prompts_usage_count ON prompts(usage_count DESC);
-- Создаем индекс для связи промптов с категориями
CREATE INDEX IF NOT EXISTS idx_prompts_category_id ON prompts(category_id);