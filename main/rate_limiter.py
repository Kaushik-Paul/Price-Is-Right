"""
Rate limiter utility with GCP storage for workflow rate limiting.
Uses IST timezone for daily reset tracking.
"""
import base64
import os
import json
import logging
from datetime import datetime
from typing import Tuple
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv(override=True)


class RateLimiter:
    """
    Rate limiter that tracks workflow runs per day with GCP storage.
    Resets daily at 12 AM IST.
    """
    
    IST_TIMEZONE = ZoneInfo("Asia/Kolkata")
    
    # Configuration from environment
    USE_GCP = os.getenv("USE_GCP", "False").lower() == "true"
    GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME", "price-is-right-memory")
    MAX_DAILY_RUNS = int(os.getenv("MAX_DAILY_RUNS", "20"))
    
    def __init__(self):
        """Initialize the rate limiter with GCP storage client."""
        self.storage_client = None
        if self.USE_GCP:
            self.storage_client = self._init_gcp_client()
    
    def _init_gcp_client(self):
        """Initializes GCP storage client from base64 secret."""
        try:
            base64_secret = os.getenv("GCP_SERVICE_ACCOUNT_BASE64")
            if not base64_secret:
                raise ValueError("GCP_SERVICE_ACCOUNT_BASE64 not found in environment")
            
            json_key = base64.b64decode(base64_secret).decode("utf-8")
            service_account_info = json.loads(json_key)
            return storage.Client.from_service_account_info(service_account_info)
        except Exception as e:
            logging.error(f"Failed to initialize GCP client for rate limiter: {e}")
            return None
    
    def _get_current_ist_date(self) -> str:
        """Returns current date in IST timezone as YYYY-MM-DD string."""
        now_ist = datetime.now(self.IST_TIMEZONE)
        return now_ist.strftime("%Y-%m-%d")
    
    def _get_blob_name(self, date: str) -> str:
        """Returns the blob name for the given date."""
        return f"workflow_run_{date}.json"
    
    def _get_gcs_blob(self, blob_name: str):
        """Returns the GCS blob for the specified blob name."""
        if not self.storage_client:
            return None
        bucket = self.storage_client.bucket(self.GCP_BUCKET_NAME)
        return bucket.blob(blob_name)
    
    def _read_run_count(self) -> int:
        """
        Reads the current run count from GCP storage.
        Returns 0 if no data exists for today or on error.
        """
        if not self.USE_GCP:
            # Fallback to always allowing if GCP is not configured
            logging.warning("GCP not configured, rate limiting disabled")
            return 0
        
        current_date = self._get_current_ist_date()
        blob_name = self._get_blob_name(current_date)
        blob = self._get_gcs_blob(blob_name)
        
        if blob and blob.exists():
            try:
                content = blob.download_as_text()
                data = json.loads(content)
                return data.get("run_count", 0)
            except Exception as e:
                logging.error(f"Failed to read run count from GCP: {e}")
                return 0
        return 0
    
    def _write_run_count(self, count: int) -> bool:
        """
        Writes the run count to GCP storage.
        Returns True on success, False on failure.
        """
        if not self.USE_GCP:
            return True
        
        current_date = self._get_current_ist_date()
        blob_name = self._get_blob_name(current_date)
        blob = self._get_gcs_blob(blob_name)
        
        if blob:
            try:
                data = {
                    "date": current_date,
                    "run_count": count,
                    "last_updated": datetime.now(self.IST_TIMEZONE).isoformat()
                }
                blob.upload_from_string(
                    json.dumps(data, indent=2),
                    content_type="application/json"
                )
                return True
            except Exception as e:
                logging.error(f"Failed to write run count to GCP: {e}")
                return False
        return False
    
    def can_run(self) -> Tuple[bool, int]:
        """
        Check if a workflow run is allowed.
        
        Returns:
            Tuple of (can_run: bool, remaining_runs: int)
        """
        current_count = self._read_run_count()
        remaining = max(0, self.MAX_DAILY_RUNS - current_count)
        can_run = current_count < self.MAX_DAILY_RUNS
        return can_run, remaining
    
    def increment_run_count(self) -> bool:
        """
        Increments the run count for today.
        
        Returns:
            True if increment was successful, False otherwise.
        """
        current_count = self._read_run_count()
        new_count = current_count + 1
        return self._write_run_count(new_count)
    
    def get_status_message(self) -> str:
        """
        Returns a human-readable status message about remaining runs.
        """
        can_run, remaining = self.can_run()
        if can_run:
            return f"✓ {remaining} runs remaining today"
        else:
            return "✗ Daily limit of 20 runs reached. Resets at 12 AM IST."
