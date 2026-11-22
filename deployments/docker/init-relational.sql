CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS admin_users (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    name          VARCHAR(120) NOT NULL,
    password_hash TEXT         NOT NULL,
    role          VARCHAR(20)  NOT NULL CHECK (role IN ('editor', 'coordenador')),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS course_info (
    id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    slug               VARCHAR(64)  NOT NULL UNIQUE,
    title              VARCHAR(180) NOT NULL,
    summary            TEXT         NOT NULL,
    graduate_profile   TEXT         NOT NULL,
    duration_semesters SMALLINT     NOT NULL CHECK (duration_semesters BETWEEN 1 AND 12),
    shifts             JSONB        NOT NULL DEFAULT '[]'::jsonb,
    admission_forms    JSONB        NOT NULL DEFAULT '[]'::jsonb,
    status             VARCHAR(24)  NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'pendente_aprovacao', 'publicado', 'arquivado')),
    created_by         UUID         REFERENCES admin_users(id),
    approved_by        UUID         REFERENCES admin_users(id),
    approved_at        TIMESTAMPTZ,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS curriculum_subjects (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code           VARCHAR(32)  NOT NULL UNIQUE,
    name           VARCHAR(150) NOT NULL,
    semester       SMALLINT     NOT NULL CHECK (semester BETWEEN 1 AND 6),
    workload_hours SMALLINT     NOT NULL CHECK (workload_hours > 0),
    description    TEXT         NOT NULL,
    status         VARCHAR(24)  NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'pendente_aprovacao', 'publicado', 'arquivado')),
    created_by     UUID         REFERENCES admin_users(id),
    approved_by    UUID         REFERENCES admin_users(id),
    approved_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    title          VARCHAR(180) NOT NULL,
    summary        VARCHAR(400) NOT NULL,
    description    TEXT         NOT NULL,
    image_url      TEXT,
    technologies   JSONB        NOT NULL DEFAULT '[]'::jsonb,
    semester_label VARCHAR(32)  NOT NULL,
    authors        JSONB        NOT NULL DEFAULT '[]'::jsonb,
    repository_url TEXT,
    status         VARCHAR(24)  NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'pendente_aprovacao', 'publicado', 'arquivado')),
    created_by     UUID         REFERENCES admin_users(id),
    approved_by    UUID         REFERENCES admin_users(id),
    approved_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS testimonials (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    author_name     VARCHAR(120) NOT NULL,
    author_role     VARCHAR(20)  NOT NULL CHECK (author_role IN ('estudante', 'egresso')),
    graduation_year SMALLINT     CHECK (graduation_year BETWEEN 2015 AND 2100),
    quote           TEXT         NOT NULL,
    photo_url       TEXT,
    status          VARCHAR(24)  NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'pendente_aprovacao', 'publicado', 'arquivado')),
    created_by      UUID         REFERENCES admin_users(id),
    approved_by     UUID         REFERENCES admin_users(id),
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
    id            UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    title         VARCHAR(180)     NOT NULL,
    description   TEXT             NOT NULL,
    event_type    VARCHAR(24)      NOT NULL CHECK (event_type IN ('divulgacao', 'vestibular', 'palestra', 'feira', 'outro')),
    location_name VARCHAR(200)     NOT NULL,
    latitude      DOUBLE PRECISION CHECK (latitude BETWEEN -90 AND 90),
    longitude     DOUBLE PRECISION CHECK (longitude BETWEEN -180 AND 180),
    starts_at     TIMESTAMPTZ      NOT NULL,
    ends_at       TIMESTAMPTZ      NOT NULL,
    qr_token      VARCHAR(64)      NOT NULL UNIQUE,
    status        VARCHAR(24)      NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'pendente_aprovacao', 'publicado', 'arquivado')),
    created_by    UUID             REFERENCES admin_users(id),
    approved_by   UUID             REFERENCES admin_users(id),
    approved_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ      NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ      NOT NULL DEFAULT now(),
    CONSTRAINT events_valid_window CHECK (ends_at > starts_at)
);

CREATE TABLE IF NOT EXISTS faqs (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    question      VARCHAR(300) NOT NULL,
    answer        TEXT         NOT NULL,
    display_order INT          NOT NULL DEFAULT 0,
    status        VARCHAR(24)  NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'pendente_aprovacao', 'publicado', 'arquivado')),
    created_by    UUID         REFERENCES admin_users(id),
    approved_by   UUID         REFERENCES admin_users(id),
    approved_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt        TEXT        NOT NULL,
    display_order INT         NOT NULL DEFAULT 0,
    status        VARCHAR(24) NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'pendente_aprovacao', 'publicado', 'arquivado')),
    created_by    UUID        REFERENCES admin_users(id),
    approved_by   UUID        REFERENCES admin_users(id),
    approved_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quiz_options (
    id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id            UUID         NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    label                  VARCHAR(300) NOT NULL,
    display_order          INT          NOT NULL DEFAULT 0,
    weight_frontend_mobile SMALLINT     NOT NULL DEFAULT 0 CHECK (weight_frontend_mobile >= 0),
    weight_backend_dados   SMALLINT     NOT NULL DEFAULT 0 CHECK (weight_backend_dados >= 0),
    weight_infra_iot       SMALLINT     NOT NULL DEFAULT 0 CHECK (weight_infra_iot >= 0),
    weight_fullstack       SMALLINT     NOT NULL DEFAULT 0 CHECK (weight_fullstack >= 0)
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID,
    sender_name  VARCHAR(120),
    sender_email VARCHAR(255),
    subject      VARCHAR(150) NOT NULL,
    message      TEXT         NOT NULL,
    is_resolved  BOOLEAN      NOT NULL DEFAULT FALSE,
    resolved_by  UUID         REFERENCES admin_users(id),
    resolved_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS event_checkins (
    id              UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID             NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    session_id      UUID             NOT NULL,
    method          VARCHAR(16)      NOT NULL CHECK (method IN ('qr_code', 'geolocation')),
    latitude        DOUBLE PRECISION CHECK (latitude BETWEEN -90 AND 90),
    longitude       DOUBLE PRECISION CHECK (longitude BETWEEN -180 AND 180),
    distance_meters DOUBLE PRECISION CHECK (distance_meters >= 0),
    checked_in_at   TIMESTAMPTZ      NOT NULL DEFAULT now(),
    CONSTRAINT event_checkins_unique_session_event UNIQUE (session_id, event_id)
);

CREATE TABLE IF NOT EXISTS quiz_submissions (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID        NOT NULL,
    answers          JSONB       NOT NULL,
    scores           JSONB       NOT NULL,
    percentages      JSONB       NOT NULL,
    dominant_profile VARCHAR(24) NOT NULL CHECK (dominant_profile IN ('frontend_mobile', 'backend_dados', 'infra_iot', 'fullstack')),
    submitted_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_curriculum_subjects_status_semester
    ON curriculum_subjects (status, semester, code);

CREATE INDEX IF NOT EXISTS idx_projects_status_created
    ON projects (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_testimonials_status_role
    ON testimonials (status, author_role);

CREATE INDEX IF NOT EXISTS idx_events_status_starts
    ON events (status, starts_at ASC);

CREATE INDEX IF NOT EXISTS idx_faqs_status_order
    ON faqs (status, display_order ASC);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_status_order
    ON quiz_questions (status, display_order ASC);

CREATE INDEX IF NOT EXISTS idx_quiz_options_question_order
    ON quiz_options (question_id, display_order ASC);

CREATE INDEX IF NOT EXISTS idx_event_checkins_session
    ON event_checkins (session_id, checked_in_at DESC);

CREATE INDEX IF NOT EXISTS idx_quiz_submissions_session
    ON quiz_submissions (session_id, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_contact_messages_resolved
    ON contact_messages (is_resolved, created_at DESC);
