from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession, AsyncAttrs
from .config import DatabaseSettings
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy import String, create_engine
from typing import Annotated
from contextlib import asynccontextmanager, contextmanager

settings = DatabaseSettings()

as_engine = create_async_engine(url=settings.DATABASE_URL_aiosqlite, echo=True) #TODO: have to change to pg for prod
s_engine = create_engine(url=settings.DATABASE_URL_sqlite, echo=True)

async_session = async_sessionmaker(as_engine, class_=AsyncSession, expire_on_commit=False)
sync_session = sessionmaker(s_engine, class_=Session, expire_on_commit=False)

str_100 = Annotated[str, 100]
str_25 = Annotated[str, 25]

class Base(AsyncAttrs, DeclarativeBase):
    type_annotation_map = {
        str_100: String(100),
        str_25: String(25)
    }
    
    repr_cols_num = 3
    repr_cols = tuple()
    
    def __repr__(self):
        cols = [f"{col}={getattr(self, col)}" for idx, col in enumerate(self.__table__.columns.keys()) if col in self.repr_cols or idx < self.repr_cols_num]
        return f"<{self.__class__.__name__} {','.join(cols)}>"
    
async def get_async_db():
    async with async_session() as session:
        yield session
        
                
def get_sync_db():
    session = sync_session()
    try:
        yield session
    finally:
        session.close()
        
@contextmanager
def get_sync_session():
    session = sync_session()
    try:
        yield session
    finally:
        session.close()         
            
@asynccontextmanager
async def get_session():
    async with async_session() as session:
        yield session
        

