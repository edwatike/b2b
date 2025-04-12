from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

class SupplierResult(Base):
    __tablename__ = "supplier_results"
    id = Column(Integer, primary_key=True, index=True)
    company = Column(String)
    website = Column(String)
    email = Column(String)
    product_found = Column(Boolean)
