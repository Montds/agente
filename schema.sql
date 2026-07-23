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
('1',  'compañia001', 'nombre_Contacto01', '60000001', 'region1',  'industria1',  'nota1',  'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('2',  'compañia002', 'nombre_Contacto02', '60000002', 'region2',  'industria2',  'nota2',  'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('3',  'compañia003', 'nombre_Contacto03', '60000003', 'region3',  'industria3',  'nota3',  'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('4',  'compañia004', 'nombre_Contacto04', '60000004', 'region4',  'industria4',  'nota4',  'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('5',  'compañia005', 'nombre_Contacto05', '60000005', 'region5',  'industria5',  'nota5',  'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('6',  'compañia006', 'nombre_Contacto06', '60000006', 'region6',  'industria6',  'nota6',  'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('7',  'compañia007', 'nombre_Contacto07', '60000007', 'region7',  'industria7',  'nota7',  'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('8',  'compañia008', 'nombre_Contacto08', '60000008', 'region8',  'industria8',  'nota8',  'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('9',  'compañia009', 'nombre_Contacto09', '60000009', 'region9',  'industria9',  'nota9',  'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('10', 'compañia010', 'nombre_Contacto10', '60000010', 'region10', 'industria10', 'nota10', 'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('11', 'compañia011', 'nombre_Contacto11', '60000011', 'region11', 'industria11', 'nota11', 'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('12', 'compañia012', 'nombre_Contacto12', '60000012', 'region12', 'industria12', 'nota12', 'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('13', 'compañia013', 'nombre_Contacto13', '60000013', 'region13', 'industria13', 'nota13', 'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('14', 'compañia014', 'nombre_Contacto14', '60000014', 'region14', 'industria14', 'nota14', 'es', CURRENT_TIMESTAMP, 'pendiente', 0),
('15', 'compañia015', 'nombre_Contacto15', '60000015', 'region15', 'industria15', 'nota15', 'es', CURRENT_TIMESTAMP, 'pendiente', 0);


INSERT INTO calls (
    lead_id,
    call_status,
    durations_seconds,
    created_at
)
VALUES
('1',  'contestada', 180, CURRENT_TIMESTAMP),
('2',  'contestada', 500, CURRENT_TIMESTAMP),
('3',  'contestada', 245, CURRENT_TIMESTAMP),
('4',  'contestada', 600, CURRENT_TIMESTAMP),
('5',  'contestada', 470, CURRENT_TIMESTAMP),
('6',  'contestada', 320, CURRENT_TIMESTAMP),
('7',  'contestada', 210, CURRENT_TIMESTAMP),
('8',  'contestada', 415, CURRENT_TIMESTAMP),
('9',  'contestada', 290, CURRENT_TIMESTAMP),
('10', 'contestada', 530, CURRENT_TIMESTAMP),
('11', 'contestada', 360, CURRENT_TIMESTAMP),
('12', 'contestada', 275, CURRENT_TIMESTAMP),
('13', 'contestada', 490, CURRENT_TIMESTAMP),
('14', 'contestada', 340, CURRENT_TIMESTAMP),
('15', 'contestada', 450, CURRENT_TIMESTAMP);