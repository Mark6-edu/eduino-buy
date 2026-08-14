"""교사용 Google OIDC 인증과 권한 체크를 처리한다."""

from __future__ import annotations

import streamlit as st


def _normalize_email(value) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def _get_auth_config() -> dict:
    try:
        if "auth" not in st.secrets:
            return {}
        return dict(st.secrets["auth"])
    except Exception:
        return {}


def get_teacher_emails() -> list[str]:
    """허용된 교사 이메일 목록을 읽는다."""
    config = _get_auth_config()
    raw_values = config.get("teacher_emails", [])

    if isinstance(raw_values, str):
        items = [item.strip() for item in raw_values.split(",")]
    elif isinstance(raw_values, (list, tuple, set)):
        items = list(raw_values)
    else:
        items = []

    emails = set()
    for item in items:
        normalized = _normalize_email(item)
        if normalized:
            emails.add(normalized)

    return sorted(emails)


def is_auth_configured() -> bool:
    """필수 Google OIDC 설정이 있는지 확인한다."""
    config = _get_auth_config()
    required_keys = [
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    ]
    return bool(config) and all(
        str(config.get(key, "")).strip() for key in required_keys
    )


def is_logged_in() -> bool:
    """현재 사용자가 로그인했는지 확인한다."""
    user = getattr(st, "user", None)
    if user is None:
        return False

    if isinstance(user, dict):
        return bool(user.get("is_logged_in") or user.get("logged_in"))

    return bool(getattr(user, "is_logged_in", False))


def get_current_user_email() -> str:
    """현재 로그인 사용자 이메일을 안전하게 반환한다."""
    if not is_logged_in():
        return ""

    user = st.user

    if isinstance(user, dict):
        candidates = [
            user.get("email"),
            user.get("user_email"),
            user.get("preferred_username"),
        ]
        userinfo = user.get("userinfo") or user.get("userInfo") or {}
        if isinstance(userinfo, dict):
            candidates.extend([
                userinfo.get("email"),
                userinfo.get("user_email"),
            ])
        for candidate in candidates:
            normalized = _normalize_email(candidate)
            if normalized:
                return normalized
        return ""

    for attr_name in ("email", "user_email", "preferred_username"):
        candidate = getattr(user, attr_name, None)
        normalized = _normalize_email(candidate)
        if normalized:
            return normalized

    userinfo = getattr(user, "userinfo", None)
    if isinstance(userinfo, dict):
        for key in ("email", "user_email"):
            normalized = _normalize_email(userinfo.get(key))
            if normalized:
                return normalized

    return ""


def is_teacher() -> bool:
    """현재 사용자가 허용된 교사 계정인지 확인한다."""
    if not is_logged_in():
        return False

    email = get_current_user_email()
    if not email:
        return False

    return email in set(get_teacher_emails())


def login_with_google():
    """Google 로그인 시도. 설정이 없으면 안내만 표시한다."""
    if not is_auth_configured():
        st.warning("Google 로그인 설정이 아직 구성되지 않았습니다.")
        return

    try:
        st.login("google")
    except Exception:
        st.warning("Google 로그인 초기화에 실패했습니다. 설정을 확인해주세요.")


def logout_with_google():
    """Google 로그아웃 시도."""
    try:
        st.logout()
    except Exception:
        st.warning("로그아웃에 실패했습니다.")


def render_auth_sidebar():
    """교사용 인증 UI를 사이드바에 표시한다."""
    st.sidebar.markdown("---")
    st.sidebar.caption("교사용")

    if not is_auth_configured():
        st.sidebar.info("Google 로그인 설정이 아직 구성되지 않았습니다.")
        return

    if not is_logged_in():
        if st.sidebar.button("🔐 Google 계정으로 로그인", use_container_width=True):
            login_with_google()
        return

    email = get_current_user_email()
    if is_teacher():
        st.sidebar.success("🟢 교사 인증됨")
        if email:
            st.sidebar.write(email)
    else:
        st.sidebar.warning("🟡 교사용 계정으로 등록되지 않았습니다.")
        if email:
            st.sidebar.write(email)

    if st.sidebar.button("🔓 로그아웃", use_container_width=True):
        logout_with_google()
