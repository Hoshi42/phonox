"""Database connection management with retry logic and alerting."""

import logging
import time
import os
from typing import Optional
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """Manages database connections with retry logic and alerting."""

    def __init__(
        self,
        database_url: str,
        max_retries: int = 5,
        initial_retry_delay: int = 2,
        max_retry_delay: int = 30,
    ):
        """
        Initialize database connection manager.

        Args:
            database_url: PostgreSQL connection URL
            max_retries: Maximum number of connection attempts
            initial_retry_delay: Initial delay between retries in seconds
            max_retry_delay: Maximum delay between retries in seconds
        """
        self.database_url = database_url
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.engine: Optional[Engine] = None
        self.session_maker: Optional[sessionmaker] = None
        self._connection_failed = False

    def _alert_connection_failure(self, attempt: int, error: Exception) -> None:
        """Alert about connection failure."""
        logger.error(
            f"DATABASE CONNECTION ATTEMPT {attempt}/{self.max_retries} FAILED: {error}"
        )

    def _alert_max_retries_exceeded(self) -> None:
        """Alert when max retries exceeded."""
        alert_msg = (
            f"\n{'='*70}\n"
            f"🚨 CRITICAL: DATABASE CONNECTION FAILED AFTER {self.max_retries} RETRIES\n"
            f"{'='*70}\n"
            f"DATABASE URL: {self._mask_url(self.database_url)}\n"
            f"The application cannot connect to the database.\n"
            f"Possible causes:\n"
            f"  - PostgreSQL service is not running\n"
            f"  - Network connectivity issues (Docker network DNS resolution)\n"
            f"  - Incorrect credentials in DATABASE_URL\n"
            f"  - Database server is unreachable\n"
            f"\nActions to take:\n"
            f"  1. Check if PostgreSQL container is running: docker-compose ps\n"
            f"  2. Try restarting containers: docker-compose restart\n"
            f"  3. Check container logs: docker-compose logs db\n"
            f"  4. Verify DATABASE_URL environment variable\n"
            f"{'='*70}\n"
        )
        logger.critical(alert_msg)
        self._connection_failed = True

    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask password in URL for logging."""
        if "@" in url:
            protocol, rest = url.split("://", 1)
            if "@" in rest:
                creds, host = rest.rsplit("@", 1)
                user = creds.split(":")[0]
                return f"{protocol}://{user}:***@{host}"
        return url

    def _get_retry_delay(self, attempt: int) -> int:
        """Calculate exponential backoff delay."""
        # Exponential backoff: 2^attempt seconds, capped at max_retry_delay
        delay = min(
            self.initial_retry_delay * (2 ** (attempt - 1)), self.max_retry_delay
        )
        return delay

    def connect(self) -> None:
        """
        Connect to database with retry logic.

        Raises:
            OperationalError: If connection fails after max retries
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Attempting database connection (attempt {attempt}/{self.max_retries})..."
                )

                # Create engine with connection pool settings
                self.engine = create_engine(
                    self.database_url,
                    pool_pre_ping=True,  # Test connections before using them
                    pool_recycle=3600,  # Recycle connections after 1 hour
                    echo=False,
                )

                # Test the connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

                # If we get here, connection successful
                logger.info("✅ Database connection established successfully!")
                self._connection_failed = False

                # Create session maker
                self.session_maker = sessionmaker(
                    autocommit=False, autoflush=False, bind=self.engine
                )

                return

            except (OperationalError, Exception) as e:
                last_error = e
                self._alert_connection_failure(attempt, e)

                if attempt < self.max_retries:
                    retry_delay = self._get_retry_delay(attempt)
                    logger.warning(
                        f"Retrying in {retry_delay} seconds... "
                        f"({self.max_retries - attempt} retries remaining)"
                    )
                    time.sleep(retry_delay)
                else:
                    self._alert_max_retries_exceeded()

        # If we get here, all retries failed
        raise OperationalError(
            f"Failed to connect to database after {self.max_retries} attempts: {last_error}",
            None,
            None,
        )

    def get_engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        if self.engine is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.engine

    def get_session_maker(self) -> sessionmaker:
        """Get the session maker."""
        if self.session_maker is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.session_maker

    def is_connected(self) -> bool:
        """Check if database is currently connected."""
        if self.engine is None:
            return False

        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connectivity check failed: {e}")
            return False

    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
