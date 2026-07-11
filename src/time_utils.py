#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Datetime parsing helpers shared by collectors and filters."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from dateutil import parser as date_parser


def parse_datetime_utc(value) -> Optional[datetime]:
    """Parse common feed/API datetime values as timezone-aware UTC datetimes."""
    if not value:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None

        dt = None
        try:
            dt = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            pass

        if dt is None:
            try:
                dt = date_parser.parse(text)
            except (TypeError, ValueError, OverflowError):
                return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def parse_datetime_naive_utc(value) -> Optional[datetime]:
    """Parse a datetime and return a timezone-naive UTC value for SQLite."""
    dt = parse_datetime_utc(value)
    if dt is None:
        return None
    return dt.replace(tzinfo=None)
