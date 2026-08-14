"""Google Apps Script Web App을 통해 학생 주문을 Google Sheets에 제출한다."""

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
