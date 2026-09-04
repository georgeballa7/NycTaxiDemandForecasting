CREATE SCHEMA IF NOT EXISTS taxi_analytics;


CREATE TABLE IF NOT EXISTS taxi_analytics.dim_zone (
    location_id INTEGER PRIMARY KEY,
    borough VARCHAR NOT NULL,
    zone VARCHAR NOT NULL,
    service_zone VARCHAR
);


CREATE TABLE IF NOT EXISTS taxi_analytics.dim_date (
    full_date DATE PRIMARY KEY,
    year SMALLINT NOT NULL,
    month SMALLINT NOT NULL,
    month_name VARCHAR NOT NULL,
    day SMALLINT NOT NULL,
    weekday_number SMALLINT NOT NULL,
    weekday VARCHAR NOT NULL,
    is_weekend BOOLEAN NOT NULL,

    CONSTRAINT chk_month CHECK (month BETWEEN 1 AND 12),
    CONSTRAINT chk_weekday_number CHECK (weekday_number BETWEEN 1 AND 7)
);


CREATE TABLE IF NOT EXISTS taxi_analytics.dim_hour (
    hour SMALLINT PRIMARY KEY,
    day_part VARCHAR NOT NULL,
    CONSTRAINT chk_hour CHECK (hour BETWEEN 0 AND 23)
);


CREATE TABLE IF NOT EXISTS taxi_analytics.dim_payment (
    payment_type SMALLINT PRIMARY KEY,
    payment_method VARCHAR NOT NULL
);


CREATE TABLE IF NOT EXISTS taxi_analytics.fact_demand (
    location_id INTEGER NOT NULL,
    pickup_date DATE NOT NULL,
    hour SMALLINT NOT NULL,
    demand INTEGER NOT NULL,

    CONSTRAINT pk_fact_demand PRIMARY KEY (location_id, pickup_date, hour),
    CONSTRAINT fk_fact_demand_zone FOREIGN KEY (location_id)
        REFERENCES taxi_analytics.dim_zone (location_id),
    CONSTRAINT fk_fact_demand_date FOREIGN KEY (pickup_date)
        REFERENCES taxi_analytics.dim_date (full_date),
    CONSTRAINT fk_fact_demand_hour FOREIGN KEY (hour)
        REFERENCES taxi_analytics.dim_hour (hour),
    CONSTRAINT chk_fact_demand_nonnegative CHECK (demand >= 0)
);


CREATE TABLE IF NOT EXISTS taxi_analytics.fact_trips (
    location_id INTEGER NOT NULL,
    pickup_date DATE NOT NULL,
    hour SMALLINT NOT NULL,
    payment_type SMALLINT NOT NULL,
    trip_count INTEGER NOT NULL,
    fare_amount NUMERIC NOT NULL,
    total_amount NUMERIC NOT NULL,
    tip_amount NUMERIC NOT NULL,
    trip_distance NUMERIC NOT NULL,
    tolls_amount NUMERIC NOT NULL,
    congestion_surcharge NUMERIC NOT NULL,
    airport_fee NUMERIC NOT NULL,
    cbd_congestion_fee NUMERIC NOT NULL,

    CONSTRAINT pk_fact_trips PRIMARY KEY (
        location_id, pickup_date, hour, payment_type
    ),
    CONSTRAINT fk_fact_trips_zone FOREIGN KEY (location_id)
        REFERENCES taxi_analytics.dim_zone (location_id),
    CONSTRAINT fk_fact_trips_date FOREIGN KEY (pickup_date)
        REFERENCES taxi_analytics.dim_date (full_date),
    CONSTRAINT fk_fact_trips_hour FOREIGN KEY (hour)
        REFERENCES taxi_analytics.dim_hour (hour),
    CONSTRAINT fk_fact_trips_payment FOREIGN KEY (payment_type)
        REFERENCES taxi_analytics.dim_payment (payment_type)
);


CREATE TABLE IF NOT EXISTS taxi_analytics.pipeline_runs (
    dataset_month DATE PRIMARY KEY,
    source_file VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,

    CONSTRAINT chk_pipeline_status
        CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED'))
);
