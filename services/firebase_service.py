"""Firebase / Firestore 연결 전용 서비스 모듈."""

from __future__ import annotations

from typing import Any, Dict

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore


def _get_firebase_secrets() -> Dict[str, Any]:
    """Streamlit Secrets에서 Firebase 설정을 안전하게 가져온다."""
    if "firebase" not in st.secrets:
        raise RuntimeError(
            "Firebase 설정을 찾을 수 없습니다. Streamlit Secrets의 [firebase] section을 확인해주세요."
        )

    firebase_config = dict(st.secrets["firebase"])

    if not firebase_config:
        raise RuntimeError(
            "Firebase 설정이 비어 있습니다. Streamlit Secrets를 다시 확인해주세요."
        )

    required_keys = {
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
    }
    missing_keys = sorted(required_keys - set(firebase_config.keys()))
    if missing_keys:
        raise RuntimeError(
            "Firebase 설정에 필수 값이 누락되었습니다. 필요한 값: "
            + ", ".join(missing_keys)
        )

    private_key = str(firebase_config.get("private_key", ""))
    firebase_config["private_key"] = private_key.replace("\\n", "\n")
    return firebase_config


def initialize_firebase():
    """Firebase 앱을 초기화한다. 중복 초기화를 막아 안전하게 처리한다."""
    try:
        firebase_config = _get_firebase_secrets()
    except RuntimeError:
        raise

    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)

    return firebase_admin.get_app()


def get_firestore_client():
    """초기화된 Firestore client를 반환한다."""
    app = initialize_firebase()
    if app is None:
        raise RuntimeError("Firebase 앱 초기화에 실패했습니다.")

    try:
        db = firestore.client()
        return db
    except Exception as exc:  # pragma: no cover - runtime-specific path
        raise RuntimeError("Firebase Firestore 연결 생성에 실패했습니다.") from exc


def check_firebase_connection():
    """Firestore 연결 상태를 확인한다. 민감 정보는 노출하지 않는다."""
    try:
        db = get_firestore_client()
        db.collection("_healthcheck").limit(1).get()
        return {
            "success": True,
            "message": "Firebase Firestore 연결 성공",
        }
    except Exception:
        return {
            "success": False,
            "message": "Firebase Firestore 연결 실패",
        }
