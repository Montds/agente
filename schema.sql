 -- ==========================================
-- 1. CREACIÓN DE TABLAS
-- ==========================================

CREATE TABLE IF NOT EXISTS leads (
    id VARCHAR(50) PRIMARY KEY,
    company_name VARCHAR(150),
    contact_name VARCHAR(150),
    phone_number VARCHAR(30),
    region VARCHAR(100),
    industry VARCHAR(100),
    notes TEXT,
    prefered_language VARCHAR(10) DEFAULT 'es',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pendiente',
    attempts_counts_today INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS calls (
    id SERIAL PRIMARY KEY,
    lead_id VARCHAR(50) NOT NULL,
    call_status VARCHAR(50) NOT NULL,
    durations_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_calls_lead
        FOREIGN KEY (lead_id)
        REFERENCES leads(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_predictions (
    id SERIAL PRIMARY KEY,
    lead_id VARCHAR(50) NOT NULL,
    call_id INTEGER,
    call_state VARCHAR(50) NOT NULL,
    lead_classification VARCHAR(50) NOT NULL,
    lead_interest_level VARCHAR(20) NOT NULL,
    classification_reason TEXT,
    recommended_next_action TEXT,
    observations JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_predictions_lead
        FOREIGN KEY (lead_id)
        REFERENCES leads(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_predictions_call
        FOREIGN KEY (call_id)
        REFERENCES calls(id)
        ON DELETE CASCADE
);

-- ==========================================
-- 2. INSERCIÓN DE DATOS INICIALES
-- ==========================================

INSERT INTO leads (
    id,
    company_name,
    contact_name,
    phone_number,
    region,
    industry,
    notes,
    prefered_language,
    created_at,
    status,
    attempts_counts_today
)
VALUES
('1', 'compañia001', 'nombre_Contacto01', '60000001', 'region1', 'industria1', 'nota1', 'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('2', 'compañia002', 'nombre_Contacto02', '60000002', 'region2', 'industria2', 'nota2', 'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('3', 'compañia003', 'nombre_Contacto03', '60000003', 'region3', 'industria3', 'nota3', 'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('4', 'compañia004', 'nombre_Contacto04', '60000004', 'region4', 'industria4', 'nota4', 'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('5', 'compañia005', 'nombre_Contacto05', '60000005', 'region5', 'industria5', 'nota5', 'es', CURRENT_TIMESTAMP, 'pendiente', 0);