
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import func
from sqlmodel import SQLModel, Field, Session, create_engine, select
EXPIRATION_HOURS = 24
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
DEFAULT_DB_URL = "sqlite:///./scans.db"

""" This module defines the database models and operations for the code review platform.
 It uses SQLModel to interact with a SQLite database."""

""" The Scan model represents a code review scan. """

class Scan(SQLModel, table=True):
    __tablename__ = "scans"
    scan_id: str = Field(primary_key=True)
    filename: str
    code_hash: str = Field(index=True)
    status: str = Field(index=True)
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    expires_at: datetime = Field(index=True)


""" The Database class provides methods to create and manage scans in the database. """

class Database:
    def __init__(self, db_url: str = DEFAULT_DB_URL):        
        self.engine = create_engine(db_url, echo=False,connect_args={"check_same_thread": False})

    def create_tables(self) -> None:
        SQLModel.metadata.create_all(self.engine)

    def create_scan(self, scan_id: str, file_name: str, code_hash: str, status: str = STATUS_RUNNING) -> Scan:
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=EXPIRATION_HOURS)

        scan = Scan(
            scan_id=scan_id,
            filename=file_name,
            code_hash=code_hash,
            status=status,
            created_at=created_at,
            expires_at=expires_at,
            result=None,
            error_message=None
        )

        with Session(self.engine) as session:
            session.add(scan)
            session.commit()
            session.refresh(scan)
            return scan

    def update_scan_result(self, scan_id: str, result: str) -> Optional[Scan]:
        
        with Session(self.engine) as session:
            scan = session.get(Scan, scan_id)

            if scan is None:
                return None

            scan.status = STATUS_COMPLETED
            scan.result = result
            scan.error_message = None

            session.add(scan)
            session.commit()
            session.refresh(scan)
            return scan

    def mark_scan_failed(self, scan_id: str, error_message: str) -> Optional[Scan]:
       
        with Session(self.engine) as session:
            scan = session.get(Scan, scan_id)

            if scan is None:
                return None

            scan.status = STATUS_FAILED
            scan.error_message = error_message

            session.add(scan)
            session.commit()
            session.refresh(scan)
            return scan

    def get_scan_by_id(self, scan_id: str) -> Optional[Scan]:
        with Session(self.engine) as session:
            return session.get(Scan, scan_id)

    def get_scan_by_hash(self, code_hash: str) -> Optional[Scan]:
        """
        Check if the same code was already scanned in the last 24 hours.
        Returns an existing non-expired scan with the same code hash.
        This can return a scan that is running, completed."""
        self.delete_expired_scans()
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            statement = (
                select(Scan)
                .where(Scan.code_hash == code_hash)
                .where(Scan.expires_at > now)
                .where(Scan.status != STATUS_FAILED)
                .order_by(Scan.created_at.desc())
            )
            return session.exec(statement).first()


    def delete_expired_scans(self) -> None:
        now = datetime.now(timezone.utc)

        with Session(self.engine) as session:
            statement = select(Scan).where(Scan.expires_at <= now)
            expired_scans = session.exec(statement).all()

            for scan in expired_scans:
                session.delete(scan)

            session.commit()

    def count_running_scans(self) -> int:
        self.delete_expired_scans()
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            statement = (
                select(func.count())
                .select_from(Scan)
                .where(Scan.status == STATUS_RUNNING)
                .where(Scan.expires_at > now)
            )
            # return a plain int scalar (scalar_one() returns the single column value)
            return int(session.exec(statement).one())
