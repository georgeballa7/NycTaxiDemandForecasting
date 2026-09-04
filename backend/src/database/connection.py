from sqlalchemy import create_engine

from backend.src.config.settings import (
    DATABASE_URL,
    SUPABASE_DATABASE_URL,
)


engine = create_engine(DATABASE_URL)

supabase_engine = (
    create_engine(SUPABASE_DATABASE_URL)
    if SUPABASE_DATABASE_URL
    else None
)