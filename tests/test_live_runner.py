"""Unit tests for Live Market Surveillance Runner."""
import tempfile
import os
import gc
from stocklens.live_runner import LiveRunner


def test_live_runner_single_cycle():
    """Verify live runner initializes SQLite tables and executes a cycle without crashing."""
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        runner = LiveRunner(
            symbols=["INFY", "TCS"],
            poll_interval_seconds=1,
            trial_days=1,
            db_path=temp_db,
        )
        res = runner.run_cycle()
        assert "stocks" in res
        assert "alerts" in res
        assert len(res["stocks"]) == 2
        for sym, d in res["stocks"].items():
            assert "price" in d
            assert "verdict" in d
            assert "explanation" in d
    finally:
        gc.collect()
        try:
            if os.path.exists(temp_db):
                os.remove(temp_db)
        except PermissionError:
            pass
