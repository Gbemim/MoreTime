"""
Rule persistence and schedule evaluation services.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List


_STORE_LOCK = threading.Lock()
_STORE_PATH = Path(__file__).resolve().parent / "data" / "rules.json"


def _ensure_store() -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _STORE_PATH.exists():
        _STORE_PATH.write_text("{}", encoding="utf-8")


def _read_store() -> Dict[str, List[Dict[str, Any]]]:
    _ensure_store()
    raw = _STORE_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    return json.loads(raw)


def _write_store(data: Dict[str, List[Dict[str, Any]]]) -> None:
    _ensure_store()
    _STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _parse_time_to_minutes(time_str: str) -> int:
    hour, minute = [int(part) for part in time_str.split(":")]
    return hour * 60 + minute


def _is_duration_active(schedule: Dict[str, Any]) -> bool:
    now_ms = int(time.time() * 1000)
    start = int(schedule["startTime"])
    end = start + int(schedule["durationMinutes"]) * 60 * 1000
    return start <= now_ms < end


def _is_daily_active(schedule: Dict[str, Any]) -> bool:
    now = time.localtime()
    current_day = (now.tm_wday + 1) % 7  # Python Monday=0, JS Sunday=0
    current_time = now.tm_hour * 60 + now.tm_min
    days = schedule.get("daysOfWeek", [])
    if current_day not in days:
        return False
    start = _parse_time_to_minutes(str(schedule["startTime"]))
    end = _parse_time_to_minutes(str(schedule["endTime"]))
    if end < start:
        return current_time >= start or current_time < end
    return start <= current_time < end


def is_rule_active(rule: Dict[str, Any]) -> bool:
    if not bool(rule.get("enabled", True)):
        return False
    schedule = rule.get("schedule", {})
    if schedule.get("type") == "duration":
        return _is_duration_active(schedule)
    return _is_daily_active(schedule)


def list_rules(tenant_id: str) -> List[Dict[str, Any]]:
    with _STORE_LOCK:
        data = _read_store()
        return list(data.get(tenant_id, []))


def list_active_rules(tenant_id: str) -> List[Dict[str, Any]]:
    return [rule for rule in list_rules(tenant_id) if is_rule_active(rule)]


def create_rule(
    tenant_id: str,
    user_description: str,
    ai_summary: str,
    schedule: Dict[str, Any],
) -> Dict[str, Any]:
    rule = {
        "id": str(uuid.uuid4()),
        "userDescription": user_description,
        "aiSummary": ai_summary,
        "patterns": [],
        "schedule": schedule,
        "enabled": True,
        "createdAt": int(time.time() * 1000),
    }
    with _STORE_LOCK:
        data = _read_store()
        tenant_rules = data.get(tenant_id, [])
        tenant_rules.append(rule)
        data[tenant_id] = tenant_rules
        _write_store(data)
    return rule


def toggle_rule(tenant_id: str, rule_id: str, enabled: bool) -> Dict[str, Any] | None:
    with _STORE_LOCK:
        data = _read_store()
        tenant_rules = data.get(tenant_id, [])
        for rule in tenant_rules:
            if rule.get("id") == rule_id:
                rule["enabled"] = enabled
                _write_store(data)
                return rule
    return None


def delete_rule(tenant_id: str, rule_id: str) -> bool:
    with _STORE_LOCK:
        data = _read_store()
        tenant_rules = data.get(tenant_id, [])
        new_rules = [rule for rule in tenant_rules if rule.get("id") != rule_id]
        deleted = len(new_rules) != len(tenant_rules)
        if deleted:
            data[tenant_id] = new_rules
            _write_store(data)
        return deleted
