"""Google Apps Script Web App을 통해 학생 주문을 Google Sheets에 제출하고 조회한다."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

import requests
import streamlit as st


def make_submission_id(
    grade,
    class_name,
    student_number,
):
    """학생 제출 식별 ID를 생성한다. 예: 1-3-15"""
    def _extract_number(value: Any, default: str = "0") -> str:
        if value is None:
            return default

        text = str(value).strip()
        if not text:
            return default

        match = re.search(r"\d+", text)
        if match:
            return match.group(0)

        return default

    grade_value = _extract_number(grade, "0")
    class_value = _extract_number(class_name, "0")
    student_value = _extract_number(student_number, "0")

    return f"{grade_value}-{class_value}-{student_value}"


def _get_web_app_url() -> str:
    """Streamlit Secrets에서 Google Apps Script Web App URL을 가져온다."""
    try:
        if "google_sheet" not in st.secrets:
            raise KeyError("google_sheet")

        config = dict(st.secrets["google_sheet"])
        web_app_url = str(config.get("web_app_url", "")).strip()

        if not web_app_url:
            raise ValueError("web_app_url is empty")

        return web_app_url
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Google Apps Script Web App URL이 설정되지 않았습니다.")


def _normalize_selected_items(selected_items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apps Script로 보낼 수 있는 기본 JSON 타입만 남긴다."""
    normalized = []

    for item in selected_items:
        if not isinstance(item, dict):
            raise ValueError("잘못된 상품 데이터입니다.")

        normalized_item = {
            "상품코드": str(item.get("상품코드", "")),
            "상품명": str(item.get("상품명", "")),
            "옵션": str(item.get("옵션", "-")),
            "단가": int(item.get("단가", 0) or 0),
            "수량": int(item.get("수량", 0) or 0),
            "금액": int(item.get("금액", 0) or 0),
        }
        normalized.append(normalized_item)

    return normalized


def _to_int(value: Any, default: int = 0) -> int:
    """문자열/숫자 값을 안전하게 int로 변환한다."""
    if value is None or value == "":
        return default

    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip().replace(",", "")
    if text in {"", "-", "nan", "None"}:
        return default

    try:
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _safe_string(value: Any, default: str = "") -> str:
    """값을 문자열로 안전하게 변환한다."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def submit_order_to_sheet(
    grade,
    class_name,
    student_number,
    student_name,
    selected_items,
    total_amount,
):
    """Google Apps Script Web App에 주문 데이터를 전송한다."""
    try:
        if not isinstance(selected_items, list) or not selected_items:
            return {
                "success": False,
                "message": "제출할 상품이 없습니다.",
            }

        web_app_url = _get_web_app_url()

        normalized_items = _normalize_selected_items(selected_items)
        submission_id = make_submission_id(
            grade=grade,
            class_name=class_name,
            student_number=student_number,
        )

        payload = {
            "action": "submit_order",
            "submission_id": submission_id,
            "student": {
                "grade": grade,
                "class_name": class_name,
                "student_number": student_number,
                "student_name": student_name,
            },
            "items": normalized_items,
            "total_amount": int(total_amount or 0),
        }

        response = requests.post(
            web_app_url,
            json=payload,
            timeout=15,
        )

        if response.status_code != 200:
            return {
                "success": False,
                "message": f"Google Sheets 제출 실패 (HTTP {response.status_code})",
            }

        try:
            result = response.json()
        except ValueError:
            return {
                "success": False,
                "message": "Google Sheets 응답을 읽을 수 없습니다.",
            }

        if not isinstance(result, dict):
            return {
                "success": False,
                "message": "Google Sheets 응답 형식이 올바르지 않습니다.",
            }

        success = bool(result.get("success", False))
        message = str(result.get("message") or "Google Sheets 제출 실패")

        return {
            "success": success,
            "message": message if success else "Google Sheets 제출 실패",
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
        }
    except requests.exceptions.RequestException:
        return {
            "success": False,
            "message": "네트워크 연결에 실패했습니다. 잠시 후 다시 시도해주세요.",
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "잘못된 상품 데이터입니다.",
        }
    except Exception:
        return {
            "success": False,
            "message": "Google Sheets 제출 실패",
        }


def fetch_submissions():
    """Apps Script에서 최신 학생 제출 리스트를 조회한다."""
    try:
        web_app_url = _get_web_app_url()
        response = requests.get(
            web_app_url,
            params={"action": "get_submissions"},
            timeout=15,
        )

        if response.status_code != 200:
            return {
                "success": False,
                "message": f"학생 제출 데이터를 불러오지 못했습니다. (HTTP {response.status_code})",
            }

        try:
            payload = response.json()
        except ValueError:
            return {
                "success": False,
                "message": "학생 제출 응답 JSON을 파싱할 수 없습니다.",
            }

        if not isinstance(payload, dict):
            return {
                "success": False,
                "message": "학생 제출 응답 형식이 올바르지 않습니다.",
            }

        if payload.get("success") is False:
            return {
                "success": False,
                "message": str(payload.get("message") or "학생 제출 데이터를 불러오지 못했습니다."),
            }

        data = payload.get("data") or []
        if not isinstance(data, list):
            return {
                "success": False,
                "message": "학생 제출 데이터 형식이 올바르지 않습니다.",
            }

        return {
            "success": True,
            "data": data,
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "학생 제출 조회 시간이 초과되었습니다.",
        }
    except requests.exceptions.RequestException:
        return {
            "success": False,
            "message": "네트워크 연결에 실패했습니다.",
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    except Exception:
        return {
            "success": False,
            "message": "학생 제출 데이터를 불러오지 못했습니다.",
        }


def fetch_order_summary():
    """Apps Script에서 상품별 집계 데이터를 조회한다."""
    try:
        web_app_url = _get_web_app_url()
        response = requests.get(
            web_app_url,
            params={"action": "get_summary"},
            timeout=15,
        )

        if response.status_code != 200:
            return {
                "success": False,
                "message": f"주문 집계 데이터를 불러오지 못했습니다. (HTTP {response.status_code})",
            }

        try:
            payload = response.json()
        except ValueError:
            return {
                "success": False,
                "message": "주문 집계 응답 JSON을 파싱할 수 없습니다.",
            }

        if not isinstance(payload, dict):
            return {
                "success": False,
                "message": "주문 집계 응답 형식이 올바르지 않습니다.",
            }

        if payload.get("success") is False:
            return {
                "success": False,
                "message": str(payload.get("message") or "주문 집계 데이터를 불러오지 못했습니다."),
            }

        data = payload.get("data") or []
        if not isinstance(data, list):
            return {
                "success": False,
                "message": "주문 집계 데이터 형식이 올바르지 않습니다.",
            }

        return {
            "success": True,
            "data": data,
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "주문 집계 조회 시간이 초과되었습니다.",
        }
    except requests.exceptions.RequestException:
        return {
            "success": False,
            "message": "네트워크 연결에 실패했습니다.",
        }
    except RuntimeError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    except Exception:
        return {
            "success": False,
            "message": "주문 집계 데이터를 불러오지 못했습니다.",
        }


def get_latest_submissions(rows):
    """동일 submission_id의 중복 제출을 제거하고 가장 최근 제출만 유지한다."""
    if not rows:
        return []

    latest_by_submission = {}

    for row in rows:
        if not isinstance(row, dict):
            continue

        submission_id = _safe_string(row.get("submission_id") or row.get("제출ID"), "")
        if not submission_id:
            continue

        submitted_at = _safe_string(row.get("submitted_at") or row.get("제출일시"), "")
        if submitted_at:
            current_key = (submission_id, submitted_at)
            latest_by_submission.setdefault(submission_id, row)
            if submitted_at > _safe_string(latest_by_submission[submission_id].get("submitted_at") or latest_by_submission[submission_id].get("제출일시"), ""):
                latest_by_submission[submission_id] = row
        else:
            latest_by_submission.setdefault(submission_id, row)

    result = []
    for row in latest_by_submission.values():
        cleaned = {
            "submission_id": _safe_string(row.get("submission_id") or row.get("제출ID"), ""),
            "submitted_at": _safe_string(row.get("submitted_at") or row.get("제출일시"), ""),
            "grade": _safe_string(row.get("grade") or row.get("학년"), ""),
            "class_name": _safe_string(row.get("class_name") or row.get("반"), ""),
            "student_number": _safe_string(row.get("student_number") or row.get("번호"), ""),
            "student_name": _safe_string(row.get("student_name") or row.get("학생명"), ""),
            "product_code": _safe_string(row.get("product_code") or row.get("상품코드"), ""),
            "product_name": _safe_string(row.get("product_name") or row.get("상품명"), ""),
            "option": _safe_string(row.get("option") or row.get("옵션"), "-"),
            "unit_price": _to_int(row.get("unit_price") or row.get("단가"), 0),
            "quantity": _to_int(row.get("quantity") or row.get("수량"), 0),
            "amount": _to_int(row.get("amount") or row.get("금액"), 0),
            "total_amount": _to_int(row.get("total_amount") or row.get("총액"), 0),
        }
        if cleaned["submission_id"]:
            result.append(cleaned)

    return result
