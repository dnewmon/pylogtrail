from sqlalchemy import (
    Column,
    Integer,
    String,
    Index,
    Text,
    Enum,
    JSON,
    DOUBLE,
)
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()


class LogLevel(enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogEntry(Base):
    """Represents a standard Python LogRecord with additional metadata"""

    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DOUBLE, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)  # logger name
    level = Column(Enum(LogLevel), nullable=False, index=True)
    pathname = Column(String(512), nullable=True)  # path to source file
    lineno = Column(Integer, nullable=True)  # line number in source file
    msg = Column(Text, nullable=False)  # the actual log message
    args = Column(JSON, nullable=True)  # arguments to the logging call
    exc_info = Column(Text, nullable=True)  # exception info if any
    func = Column(String(255), nullable=True)  # function name
    extra_metadata = Column(JSON, nullable=True)  # additional custom metadata

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_name_timestamp", "name", "timestamp"),
        Index("idx_level_timestamp", "level", "timestamp"),
    )

    def __repr__(self):
        return f"<LogEntry(id={self.id}, name='{self.name}', level='{self.level}', timestamp='{self.timestamp}')>"
