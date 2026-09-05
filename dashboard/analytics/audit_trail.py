"""
AUREVIX — Enterprise Audit Trail & Governance Engine
Tracks dataset uploads, cleaning steps, filter mutations, goal tracking, and export events.
"""
from typing import Dict, Any, List
import datetime
import streamlit as st

_NS = "workspace"


class AuditTrail:
    """Records chronological analytical audit records under st.session_state['workspace']['audit_trail']."""

    @classmethod
    def log_event(cls, action: str, dataset_id: str, details: str = "") -> Dict[str, Any]:
        if _NS not in st.session_state:
            st.session_state[_NS] = {}
        ws = st.session_state[_NS]
        trail = ws.setdefault("audit_trail", [])

        event = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "dataset_id": dataset_id[:12] if dataset_id else "N/A",
            "details": details
        }
        trail.append(event)
        # Keep last 100 events
        if len(trail) > 100:
            trail.pop(0)
        return event

    @classmethod
    def get_logs(cls, limit: int = 20) -> List[Dict[str, Any]]:
        if _NS not in st.session_state:
            return []
        trail = st.session_state[_NS].get("audit_trail", [])
        return list(reversed(trail[-limit:]))

    @classmethod
    def clear_logs(cls) -> None:
        if _NS in st.session_state:
            st.session_state[_NS]["audit_trail"] = []
