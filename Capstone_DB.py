from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "mysql+pymysql://root:1234@localhost/heyyo"

engine = create_engine(DATABASE_URL) #DB 연결
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    password = Column(String(128), nullable=False)
    images = relationship("Image", back_populates="owner")
    stories = relationship("Story", back_populates="owner")

class Image(Base):
    __tablename__ = "images"

    image_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    owner = relationship("User", back_populates="images")
    image_info = relationship("ImageInfo", back_populates="image", uselist=False)
    story = relationship("Story", back_populates="image", uselist=False)

class ImageInfo(Base):
    __tablename__ = "image_info"

    image_info_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("images.image_id"), nullable=False)
    image_url = Column(String(255))
    image_description = Column(Text)
    image = relationship("Image", back_populates="image_info")

class Story(Base):
    __tablename__ = "stories"

    story_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), unique=True, nullable=False)
    story_name = Column(String(255), nullable=False)
    story_content = Column(Text, nullable=False)
    image_id = Column(Integer, ForeignKey("images.image_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    owner = relationship("User", back_populates="stories")
    image = relationship("Image", back_populates="story")

def init_db():
    Base.metadata.create_all(bind=engine)