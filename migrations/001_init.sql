CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE managers (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    bin CHAR(12) NOT NULL UNIQUE CHECK (bin ~ '^[0-9]{12}$'),
    phone TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'no_answer', 'refused', 'meeting_set')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE meetings (
    id SERIAL PRIMARY KEY,
    manager_id INT NOT NULL REFERENCES managers (id),
    company_id INT NOT NULL REFERENCES companies (id),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at),
    -- у менеджера не может быть пересекающихся встреч
    -- '[)' - конец не входит, поэтому 10-11 и 11-12 не конфликт
    CONSTRAINT meetings_manager_overlap EXCLUDE USING gist (
        manager_id WITH =,
        tstzrange(starts_at, ends_at, '[)') WITH &&
    ) WHERE (status = 'scheduled')
);

-- у компании только одна активная встреча
CREATE UNIQUE INDEX meetings_company_active ON meetings (company_id) WHERE status = 'scheduled';

-- история встречи: создание, переносы, отмена
CREATE TABLE meeting_events (
    id SERIAL PRIMARY KEY,
    meeting_id INT NOT NULL REFERENCES meetings (id),
    kind TEXT NOT NULL CHECK (kind IN ('created', 'rescheduled', 'cancelled')),
    starts_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX meeting_events_meeting_id ON meeting_events (meeting_id);

CREATE TABLE calls (
    id SERIAL PRIMARY KEY,
    company_id INT NOT NULL REFERENCES companies (id),
    result TEXT NOT NULL CHECK (result IN ('no_answer', 'refused', 'meeting_set')),
    meeting_id INT REFERENCES meetings (id),
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- meeting_id есть только у meeting_set
    CHECK ((result = 'meeting_set') = (meeting_id IS NOT NULL))
);

-- эндпоинта для менеджеров нет, поэтому добавляем сразу
INSERT INTO managers (first_name, last_name, email) VALUES
    ('Айгуль', 'Сейткали', 'aigul_seitkali@whitelist.local'),
    ('Ерлан', 'Жумабаев', 'erlan_zhumabaev@whitelist.local'),
    ('Динара', 'Ахметова', 'dinara_akhmetova@whitelist.local');
