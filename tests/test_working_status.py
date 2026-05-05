from __future__ import annotations

from wxpi.working_status import format_working_status


def test_working_status_reports_seconds():
    assert format_working_status(0) == "Working for 0 seconds"
    assert format_working_status(1) == "Working for 1 second"
    assert format_working_status(12) == "Working for 12 seconds"


def test_working_status_reports_minutes_and_seconds():
    assert format_working_status(60) == "Working for 1 minute 0 seconds"
    assert format_working_status(121) == "Working for 2 minutes 1 second"


def test_working_status_clamps_negative_elapsed_time():
    assert format_working_status(-3) == "Working for 0 seconds"
