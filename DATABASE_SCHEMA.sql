-- PostgreSQL Database Schema for Legal Document Assistance Platform
-- Date: January 2026

-- ==================== USERS & AUTHENTICATION ====================

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    phone_number VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    full_name VARCHAR(200),
    preferred_language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(user_id),
    jwt_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE
);

-- ==================== DOCUMENT CASES ====================

CREATE TABLE legal_cases (
    case_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    reference_number VARCHAR(50) UNIQUE NOT NULL, -- e.g., "LDA-2026-0001"
    issue_type VARCHAR(50) NOT NULL, -- 'police_complaint', 'civil_suit', 'government_application'
    sub_category VARCHAR(50) NOT NULL, -- 'theft', 'assault', 'property_dispute', etc.
    status VARCHAR(30) DEFAULT 'draft', -- 'draft', 'in_progress', 'ready', 'completed'
    suggested_authority VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- ==================== EXTRACTED ENTITIES ====================

CREATE TABLE case_entities (
    entity_id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES legal_cases(case_id) ON DELETE CASCADE,
    field_name VARCHAR(50) NOT NULL, -- 'name', 'date', 'location', 'accused', etc.
    field_value TEXT,
    is_confirmed BOOLEAN DEFAULT FALSE,
    confirmed_at TIMESTAMP,
    extracted_by VARCHAR(20) DEFAULT 'nlp', -- 'nlp', 'user', 'voice'
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== Q&A INTERACTION LOG ====================

CREATE TABLE qa_interactions (
    interaction_id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES legal_cases(case_id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    user_response TEXT,
    field_targeted VARCHAR(50),
    input_method VARCHAR(20), -- 'text', 'voice_transcribed'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== VOICE TRANSCRIPTS ====================

CREATE TABLE voice_transcripts (
    transcript_id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES legal_cases(case_id) ON DELETE CASCADE,
    audio_duration_seconds INTEGER,
    transcribed_text TEXT,
    language_detected VARCHAR(10),
    is_confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== GENERATED DOCUMENTS ====================

CREATE TABLE generated_documents (
    document_id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES legal_cases(case_id) ON DELETE CASCADE,
    document_type VARCHAR(50), -- 'fir_draft', 'application', 'affidavit', etc.
    language VARCHAR(10), -- 'en', 'hi', 'ta', etc.
    file_format VARCHAR(10), -- 'pdf', 'docx'
    file_path TEXT, -- Storage path or S3 URL
    file_size_kb INTEGER,
    is_bilingual BOOLEAN DEFAULT TRUE,
    is_preview BOOLEAN DEFAULT FALSE,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    downloaded_at TIMESTAMP
);

-- ==================== DOCUMENT VERSIONS (Edit History) ====================

CREATE TABLE document_versions (
    version_id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES generated_documents(document_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content_snapshot JSONB, -- Store the full content for that version
    edited_by INTEGER REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== AUDIT LOG ====================

CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    case_id INTEGER REFERENCES legal_cases(case_id),
    action VARCHAR(100), -- 'case_created', 'entity_confirmed', 'document_generated', etc.
    details JSONB,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== AUTHORITY TEMPLATES ====================

CREATE TABLE document_templates (
    template_id SERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,
    issue_type VARCHAR(50) NOT NULL,
    sub_category VARCHAR(50),
    language VARCHAR(10) DEFAULT 'en',
    template_content TEXT, -- Template with placeholders like {{name}}, {{date}}
    required_fields TEXT[], -- Array of required field names
    format_type VARCHAR(10) DEFAULT 'pdf', -- 'pdf', 'docx'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== REFERENCE NUMBER SEQUENCE ====================

CREATE SEQUENCE reference_number_seq START 1;

-- Function to generate reference number
CREATE OR REPLACE FUNCTION generate_reference_number()
RETURNS VARCHAR(50) AS $$
DECLARE
    ref_num VARCHAR(50);
BEGIN
    ref_num := 'LDA-' || TO_CHAR(CURRENT_DATE, 'YYYY') || '-' ||
               LPAD(nextval('reference_number_seq')::TEXT, 6, '0');
    RETURN ref_num;
END;
$$ LANGUAGE plpgsql;

-- ==================== INDEXES FOR PERFORMANCE ====================

CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_cases_user ON legal_cases(user_id);
CREATE INDEX idx_cases_status ON legal_cases(status);
CREATE INDEX idx_cases_reference ON legal_cases(reference_number);
CREATE INDEX idx_entities_case ON case_entities(case_id);
CREATE INDEX idx_documents_case ON generated_documents(case_id);
CREATE INDEX idx_qa_case ON qa_interactions(case_id);

-- ==================== SAMPLE DATA (Optional) ====================

-- Insert default document templates
INSERT INTO document_templates (template_name, issue_type, sub_category, language, template_content, required_fields) VALUES
('Police FIR - Theft (English)', 'police_complaint', 'theft', 'en',
'To,\nThe Station House Officer,\n{{police_station}}\n\nSub: Complaint regarding theft\n\nRespected Sir/Madam,\n\nI, {{name}}, residing at {{address}}, would like to report that on {{date}}, at {{location}}, the following items were stolen from my possession:\n\n{{stolen_items}}\n\n{{description}}\n\nI request you to register an FIR and take necessary action.\n\nThank you.\n\nSincerely,\n{{name}}\nDate: {{current_date}}',
ARRAY['name', 'address', 'date', 'location', 'stolen_items', 'description']),

('RTI Application (English)', 'government_application', 'rti', 'en',
'To,\nThe Public Information Officer,\n{{department}}\n\nSub: Application under Right to Information Act, 2005\n\nRespected Sir/Madam,\n\nI, {{name}}, residing at {{address}}, am seeking the following information under the RTI Act, 2005:\n\n{{description}}\n\nPlease provide the information within the stipulated period.\n\nThank you.\n\nSincerely,\n{{name}}\nDate: {{current_date}}',
ARRAY['name', 'address', 'department', 'description']);

-- ==================== TRIGGERS ====================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cases_updated_at BEFORE UPDATE ON legal_cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON document_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
