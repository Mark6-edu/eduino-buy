import streamlit as st
import pandas as pd
from pathlib import Path
import re
import io
import csv
from services.auth_service import is_teacher, render_auth_sidebar
from services.excel_service import create_order_excel
from services.google_sheet_service import submit_order_to_sheet
from utils.calculator import format_currency

# ============================================================================
# 데이터 유틸
# ============================================================================


def normalize_subcategories(value):
    """상품의 세부 분류 문자열을 리스트로 변환한다."""
    if pd.isna(value):
        return []

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []

    return [item.strip() for item in text.split("|") if item.strip()]


def parse_options(value):
    """CSV options 문자열을 리스트로 변환한다."""
    if pd.isna(value):
        return []

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []

    return [item.strip() for item in text.split("|") if item.strip()]


def parse_option_price_map(value):
    """
    옵션별 추가금액 문자열을 dict로 변환한다.

    CSV 예:
    50RPM:0|100RPM:1100|300RPM:2200

    반환:
    {
        "50RPM": 0,
        "100RPM": 1100,
        "300RPM": 2200,
    }
    """
    if pd.isna(value):
        return {}

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return {}

    result = {}

    for item in text.split("|"):
        item = item.strip()
        if not item or ":" not in item:
            continue

        option, adjustment = item.rsplit(":", 1)
        option = option.strip()

        try:
            adjustment = int(str(adjustment).replace(",", "").strip())
        except ValueError:
            adjustment = 0

        if option:
            result[option] = adjustment

    return result


def get_effective_price(row, selected_option=""):
    """
    기본 판매가 + 선택 옵션 추가금액을 반환한다.

    옵션 추가금액이 없으면 기존 판매가를 그대로 반환한다.
    """
    base_price = int(row["price"])
    option_price_map = parse_option_price_map(row.get("option_prices", ""))

    if not selected_option:
        return base_price

    return base_price + int(option_price_map.get(selected_option, 0))


@st.cache_data
def load_products(data_path_str, file_mtime_ns):
    """
    products.csv를 로드하고 필요한 컬럼을 정규화한다.

    file_mtime_ns를 캐시 키에 포함시켜 CSV 파일 내용이 바뀌면
    Streamlit 캐시가 자동으로 무효화되도록 한다.
    """
    data_path = Path(data_path_str)

    try:
        df = pd.read_csv(data_path)

        required_columns = ["category", "code", "name", "price", "url"]
        missing = [column for column in required_columns if column not in df.columns]

        if missing:
            st.error(
                "❌ products.csv에 필요한 컬럼이 없습니다: "
                + ", ".join(missing)
            )
            return pd.DataFrame()

        if "subcategories" not in df.columns:
            df["subcategories"] = ""

        if "subcategory" in df.columns:
            df["subcategories"] = df["subcategories"].fillna(df["subcategory"])

        if "option_name" not in df.columns:
            df["option_name"] = ""

        if "options" not in df.columns:
            df["options"] = ""

        # 옵션별 추가금액을 저장하는 선택 컬럼.
        # 예: 50RPM:0|100RPM:1100|300RPM:2200
        if "option_prices" not in df.columns:
            df["option_prices"] = ""

        text_columns = [
            "category",
            "subcategories",
            "code",
            "name",
            "url",
            "option_name",
            "options",
            "option_prices",
        ]

        for column in text_columns:
            df[column] = df[column].fillna("").map(
                lambda value: str(value).strip()
            )

        df["price"] = pd.to_numeric(df["price"], errors="coerce")

        invalid_price_count = df["price"].isna().sum()
        if invalid_price_count > 0:
            st.warning(
                f"⚠️ {invalid_price_count}개 상품의 가격을 숫자로 변환하지 못했습니다. "
                "해당 상품은 0원으로 처리됩니다."
            )
            df["price"] = df["price"].fillna(0)

        return df

    except FileNotFoundError:
        st.error("❌ data/products.csv 파일을 찾을 수 없습니다.")
        return pd.DataFrame()


# ============================================================================
# Session State
# ============================================================================


def init_session_state():
    """앱에서 사용하는 상태값을 초기화한다."""
    defaults = {
        "cart": {},
        "selected_sensor_category": "환경",
        "selected_parts_category": "IC/기본소자",
        "top_notification_message": "",
        "top_notification_pending": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, dict) else value



# ============================================================================
# 상단 알림
# ============================================================================


def set_top_notification(message):
    """다음 rerun에서 화면 상단에 표시할 1회성 알림을 저장한다."""
    st.session_state["top_notification_message"] = str(message)
    st.session_state["top_notification_pending"] = True


def render_top_notification():
    """
    현재 스크롤 위치와 관계없이 브라우저 viewport 상단 중앙에
    약 3초 동안 표시되는 고정형 팝업 알림을 렌더링한다.
    """
    if not st.session_state.get("top_notification_pending", False):
        return

    message = st.session_state.get(
        "top_notification_message",
        "장바구니에 담았습니다.",
    )

    safe_message = (
        str(message)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

    st.markdown(
        f"""
        <style>
        @keyframes eduinoCartPopupFade {{
            0% {{
                opacity: 0;
                transform: translate(-50%, -12px) scale(0.98);
            }}
            10% {{
                opacity: 1;
                transform: translate(-50%, 0) scale(1);
            }}
            82% {{
                opacity: 1;
                transform: translate(-50%, 0) scale(1);
            }}
            100% {{
                opacity: 0;
                transform: translate(-50%, -8px) scale(0.98);
                visibility: hidden;
            }}
        }}

        .eduino-cart-popup {{
            position: fixed;
            top: 28px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 999999;
            width: min(760px, calc(100vw - 32px));
            padding: 16px 24px;
            border-radius: 999px;
            background: #9bddec;
            color: #111827;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.20);
            text-align: center;
            font-size: 1.15rem;
            font-weight: 800;
            line-height: 1.35;
            pointer-events: none;
            animation: eduinoCartPopupFade 3s ease-in-out forwards;
        }}

        @media (max-width: 768px) {{
            .eduino-cart-popup {{
                top: 16px;
                width: calc(100vw - 24px);
                padding: 13px 18px;
                border-radius: 18px;
                font-size: 1rem;
            }}
        }}
        </style>

        <div class="eduino-cart-popup">
            🛒 {safe_message}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.session_state["top_notification_pending"] = False


# ============================================================================
# 장바구니
# ============================================================================


def make_cart_key(code, option=""):
    """
    같은 상품이라도 옵션이 다르면 다른 주문 항목으로 처리한다.

    예:
    E-14::노랑색
    E-14::파랑색
    C-21::__NO_OPTION__
    """
    normalized_option = option.strip() if option else "__NO_OPTION__"
    return f"{code}::{normalized_option}"


def add_to_cart(row, quantity, option="", unit_price=None):
    """
    상품을 장바구니에 추가한다.
    같은 코드+옵션이면 수량을 누적한다.

    unit_price를 전달하면 옵션 추가금액까지 반영된 최종 단가를 저장한다.
    """
    code = str(row["code"]).strip()
    quantity = max(1, int(quantity))
    option = str(option).strip() if option else ""

    if unit_price is None:
        unit_price = get_effective_price(row, option)

    unit_price = int(unit_price)
    cart_key = make_cart_key(code, option)

    if cart_key in st.session_state["cart"]:
        st.session_state["cart"][cart_key]["quantity"] += quantity
        # CSV 가격이 수정된 경우를 대비해 담을 때 최신 단가로 갱신
        st.session_state["cart"][cart_key]["price"] = unit_price
    else:
        st.session_state["cart"][cart_key] = {
            "code": code,
            "name": str(row["name"]),
            "option": option,
            "price": unit_price,
            "quantity": quantity,
            "category": str(row["category"]),
            "subcategories": str(row.get("subcategories", "")),
            "url": str(row.get("url", "")),
        }

    # 중요:
    # 장바구니 number_input은 자체 widget state를 유지하므로
    # 상품을 다시 담아 수량이 누적되었을 때 widget state도 함께 갱신해야 한다.
    cart_qty_key = f"cart_qty_{cart_key}"
    st.session_state[cart_qty_key] = int(
        st.session_state["cart"][cart_key]["quantity"]
    )


def remove_from_cart(cart_key):
    """장바구니 항목과 연결된 수량 widget state를 함께 삭제한다."""
    st.session_state["cart"].pop(cart_key, None)
    st.session_state.pop(f"cart_qty_{cart_key}", None)


def calculate_cart_totals():
    """장바구니 기준으로 선택 상품, 총수량, 총액을 계산한다."""
    selected_items = []

    for cart_key, item in st.session_state["cart"].items():
        quantity = max(1, int(item["quantity"]))
        price = int(item["price"])
        amount = price * quantity

        selected_items.append(
            {
                "상품코드": item["code"],
                "상품명": item["name"],
                "옵션": item["option"] if item["option"] else "-",
                "단가": price,
                "수량": quantity,
                "금액": amount,
            }
        )

    total_quantity = sum(item["수량"] for item in selected_items)
    total_amount = sum(item["금액"] for item in selected_items)

    return {
        "selected_items": selected_items,
        "selected_count": len(selected_items),
        "total_quantity": total_quantity,
        "total_amount": total_amount,
    }


# ============================================================================
# 공통 상품 렌더링
# ============================================================================


def render_product_header():
    """상품 목록의 공통 헤더를 출력한다."""
    columns = st.columns([3.4, 1.2, 1.2, 1.8, 1.3, 1.2, 1.0])
    labels = ["상품명", "상품코드", "단가", "옵션", "수량", "금액", "담기"]

    for column, label in zip(columns, labels):
        with column:
            st.markdown(
                f'<div class="eduino-product-header">{label}</div>',
                unsafe_allow_html=True,
            )


def render_product_row(row, key_prefix="product"):
    """
    모든 상품을 동일한 '수량/옵션 선택 → 담기' 방식으로 렌더링한다.

    - 옵션 없는 상품: 수량 + 담기
    - 옵션 있는 상품: 옵션 + 수량 + 담기
    - 체크박스는 사용하지 않는다.
    """
    code = str(row["code"]).strip()
    option_name = str(row.get("option_name", "") or "").strip()
    option_values = parse_options(row.get("options", ""))

    unique_prefix = f"{key_prefix}_{code}"

    (
        col_name,
        col_code,
        col_price,
        col_option,
        col_qty,
        col_amount,
        col_add,
    ) = st.columns([3.4, 1.2, 1.2, 1.8, 1.3, 1.2, 1.0])

    with col_name:
        product_name = str(row["name"])
        product_url = str(row.get("url", "")).strip()

        if product_url and product_url.lower() != "nan":
            st.markdown(f"[{product_name}]({product_url})")
        else:
            st.text(product_name)

    with col_code:
        st.text(code)

    # 먼저 옵션을 선택해야 실제 단가를 계산할 수 있다.
    with col_option:
        if option_values:
            selected_option = st.selectbox(
                option_name or "옵션",
                options=option_values,
                key=f"option_draft_{unique_prefix}",
                label_visibility="collapsed",
            )
        else:
            selected_option = ""
            st.text("-")

    effective_price = get_effective_price(row, selected_option)

    with col_price:
        # 옵션 추가금액이 있는 상품은 선택 옵션에 따라 단가가 즉시 변경된다.
        st.text(f"{format_currency(effective_price)}원")

    with col_qty:
        quantity = st.number_input(
            "수량",
            min_value=1,
            value=1,
            step=1,
            key=f"qty_draft_{unique_prefix}",
            label_visibility="collapsed",
        )

    with col_amount:
        preview_amount = int(effective_price) * int(quantity)
        st.text(f"{format_currency(preview_amount)}원")

    with col_add:
        if st.button(
            "담기",
            key=f"add_{unique_prefix}",
            use_container_width=True,
            type="primary",
        ):
            add_to_cart(
                row=row,
                quantity=quantity,
                option=selected_option,
                unit_price=effective_price,
            )

            option_text = f" / {selected_option}" if selected_option else ""

            set_top_notification(
                f"{row['name']}{option_text} {int(quantity)}개를 장바구니에 담았습니다."
            )
            st.rerun()


# ============================================================================
# 보드
# ============================================================================


def render_board_category(products_df):
    board_df = products_df[products_df["category"] == "보드"].copy()

    if board_df.empty:
        return

    st.subheader("📌 보드")
    render_product_header()

    for _, row in board_df.iterrows():
        render_product_row(row, key_prefix="board")
        st.markdown("")


# ============================================================================
# 센서 & 모듈
# ============================================================================


def render_sensor_category(products_df):
    sensor_categories = [
        "환경",
        "거리/위치",
        "수질/토양",
        "압력/접촉",
        "조도/적외선/컬러",
        "LCD/디스플레이",
        "릴레이/스위치",
        "모터/제어",
        "통신",
        "LED/네오픽셀",
        "소리/영상",
        "가속도/자이로",
    ]

    if st.session_state["selected_sensor_category"] not in sensor_categories:
        st.session_state["selected_sensor_category"] = "환경"

    selected_category = st.session_state["selected_sensor_category"]

    st.subheader("📡 센서 & 모듈")
    st.caption("센서 유형을 선택하면 해당 분류의 상품을 확인할 수 있습니다.")

    # 6개씩 2줄
    for row_start in range(0, len(sensor_categories), 6):
        columns = st.columns(6)
        current_row = sensor_categories[row_start : row_start + 6]

        for column_index, category_name in enumerate(current_row):
            with columns[column_index]:
                is_selected = selected_category == category_name

                if st.button(
                    category_name,
                    key=f"sensor_category_{category_name}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state["selected_sensor_category"] = category_name
                    st.rerun()

    st.info(f"현재 선택: **{selected_category}**")

    sensor_df = products_df[
        (products_df["category"] == "센서")
        & products_df.apply(
            lambda row: selected_category
            in normalize_subcategories(row.get("subcategories", "")),
            axis=1,
        )
    ].copy()

    if sensor_df.empty:
        st.info("해당 분류의 상품은 추후 추가될 예정입니다.")
        return

    render_product_header()

    for _, row in sensor_df.iterrows():
        render_product_row(
            row,
            key_prefix=f"sensor_{selected_category}",
        )
        st.markdown("")


# ============================================================================
# 전자부품
# ============================================================================


def render_electronic_parts_category(products_df):
    parts_categories = [
        "IC/기본소자",
        "주변부품",
        "브레드보드",
        "케이블",
        "배터리/전원",
    ]

    if st.session_state["selected_parts_category"] not in parts_categories:
        st.session_state["selected_parts_category"] = "IC/기본소자"

    selected_category = st.session_state["selected_parts_category"]

    st.subheader("🔌 전자부품")
    st.caption("전자부품 유형을 선택하면 해당 분류의 상품을 확인할 수 있습니다.")

    columns = st.columns(5)

    for index, category_name in enumerate(parts_categories):
        with columns[index]:
            is_selected = selected_category == category_name

            if st.button(
                category_name,
                key=f"parts_category_{category_name}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state["selected_parts_category"] = category_name
                st.rerun()

    st.info(f"현재 선택: **{selected_category}**")

    parts_df = products_df[
        (products_df["category"] == "전자부품")
        & products_df.apply(
            lambda row: selected_category
            in normalize_subcategories(row.get("subcategories", "")),
            axis=1,
        )
    ].copy()

    if parts_df.empty:
        st.info("해당 분류의 상품은 추후 추가될 예정입니다.")
        return

    render_product_header()

    for _, row in parts_df.iterrows():
        render_product_row(
            row,
            key_prefix=f"parts_{selected_category}",
        )
        st.markdown("")


# ============================================================================
# 기타 향후 카테고리
# ============================================================================


def render_generic_category(products_df, category):
    category_df = products_df[products_df["category"] == category].copy()

    if category_df.empty:
        return

    st.subheader(f"📌 {category}")
    render_product_header()

    for _, row in category_df.iterrows():
        render_product_row(
            row,
            key_prefix=f"generic_{category}",
        )
        st.markdown("")


# ============================================================================
# 장바구니
# ============================================================================


def render_cart():
    st.markdown("---")
    st.subheader("🧺 담은 상품")

    if not st.session_state["cart"]:
        st.info("아직 담은 상품이 없습니다.")
        return

    header_columns = st.columns([1.0, 2.8, 1.6, 1.1, 1.2, 1.4, 0.8])
    labels = ["상품코드", "상품명", "옵션", "단가", "수량", "금액", "삭제"]

    for column, label in zip(header_columns, labels):
        with column:
            st.caption(label)

    # dict를 순회하면서 삭제가 발생할 수 있으므로 list로 복사
    for cart_key, item in list(st.session_state["cart"].items()):
        (
            col_code,
            col_name,
            col_option,
            col_price,
            col_qty,
            col_amount,
            col_remove,
        ) = st.columns([1.0, 2.8, 1.6, 1.1, 1.2, 1.4, 0.8])

        with col_code:
            st.text(item["code"])

        with col_name:
            st.text(item["name"])

        with col_option:
            st.text(item["option"] if item["option"] else "-")

        with col_price:
            st.text(f"{format_currency(item['price'])}원")

        with col_qty:
            cart_qty_key = f"cart_qty_{cart_key}"

            # 처음 렌더링되는 장바구니 항목만 cart의 수량으로 widget state 초기화
            if cart_qty_key not in st.session_state:
                st.session_state[cart_qty_key] = max(
                    1,
                    int(item["quantity"]),
                )

            quantity = st.number_input(
                "장바구니 수량",
                min_value=1,
                step=1,
                key=cart_qty_key,
                label_visibility="collapsed",
            )

            # 사용자가 장바구니에서 직접 수량을 바꾸면 cart 데이터에도 즉시 반영
            st.session_state["cart"][cart_key]["quantity"] = int(quantity)

        with col_amount:
            amount = int(item["price"]) * int(
                st.session_state["cart"][cart_key]["quantity"]
            )
            st.text(f"{format_currency(amount)}원")

        with col_remove:
            if st.button(
                "🗑️",
                key=f"remove_{cart_key}",
                help="장바구니에서 삭제",
            ):
                remove_from_cart(cart_key)
                st.rerun()



# ============================================================================
# CSV 구매 명세서 다운로드
# ============================================================================


def sanitize_filename(value):
    """다운로드 파일명에서 사용할 수 없는 문자를 안전하게 치환한다."""
    text = str(value or "").strip()
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", "_", text)
    return text or "미입력"


def build_order_csv_bytes():
    """
    기안문 품목내역 형식으로 CSV를 생성한다.

    상단:
    - 학년 / 반 / 번호 / 학생명(팀원명)

    품목내역:
    - 순번
    - 내용
    - 규격
    - 수량
    - 단위
    - 예상단가
    - 예상금액

    규격:
    - 옵션이 있으면 옵션값
    - 옵션이 없으면 상품코드
    """
    totals = calculate_cart_totals()

    grade = st.session_state.get("select_grade", "")
    class_name = st.session_state.get("select_class", "")
    student_number = int(st.session_state.get("input_student_number", 1))
    student_name = st.session_state.get("input_student_name", "").strip()

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    writer.writerow(["<품목내역>"])
    writer.writerow([])

    writer.writerow(["학년", grade])
    writer.writerow(["반", class_name])
    writer.writerow(["번호", f"{student_number}번"])
    writer.writerow(["학생명/팀원명", student_name])
    writer.writerow([])

    writer.writerow(
        [
            "순번",
            "내용",
            "규격",
            "수량",
            "단위",
            "예상단가",
            "예상금액",
        ]
    )

    for index, item in enumerate(totals["selected_items"], start=1):
        option = str(item.get("옵션", "")).strip()

        if not option or option == "-":
            specification = item["상품코드"]
        else:
            specification = option

        writer.writerow(
            [
                f"1-{index}",
                item["상품명"],
                specification,
                item["수량"],
                "개",
                item["단가"],
                item["금액"],
            ]
        )

    writer.writerow([])
    writer.writerow(
        [
            "",
            "합계",
            "",
            "",
            "",
            "",
            totals["total_amount"],
        ]
    )

    csv_bytes = output.getvalue().encode("utf-8-sig")

    filename = (
        "Eduino_품목내역_"
        f"{sanitize_filename(grade)}_"
        f"{sanitize_filename(class_name)}_"
        f"{student_number}번_"
        f"{sanitize_filename(student_name)}.csv"
    )

    return csv_bytes, filename

def render_csv_download():
    """현재 장바구니를 학생별 CSV 구매 명세서로 다운로드한다."""
    st.markdown("---")
    st.subheader("⬇️ 품목내역 CSV 다운로드")

    totals = calculate_cart_totals()

    if totals["selected_count"] == 0:
        st.info("담긴 상품이 있어야 품목내역 CSV를 다운로드할 수 있습니다.")
        return

    student_name = st.session_state.get("input_student_name", "").strip()

    if not student_name:
        st.warning(
            "학생명 / 팀원명을 입력해주세요. "
            "현재 상태에서도 다운로드는 가능하지만 학생 구분이 어렵습니다."
        )

    csv_bytes, filename = build_order_csv_bytes()

    st.download_button(
        label="📥 품목내역 CSV 다운로드",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
        type="primary",
    )

    st.caption(
        "CSV는 기안문 품목내역 형식으로 생성됩니다. "
        "열 구성: 순번 · 내용 · 규격 · 수량 · 단위 · 예상단가 · 예상금액"
    )


def render_excel_download():
    """현재 장바구니를 학생별 Excel 구매 명세서로 다운로드한다."""
    st.markdown("---")
    st.subheader("⬇️ 품목내역 Excel 다운로드")

    totals = calculate_cart_totals()

    if totals["selected_count"] == 0:
        st.info("담긴 상품이 있어야 품목내역 Excel을 다운로드할 수 있습니다.")
        return

    student_name = st.session_state.get("input_student_name", "").strip()
    if not student_name:
        st.warning(
            "학생명 / 팀원명을 입력해주세요. "
            "현재 상태에서도 다운로드는 가능하지만 학생 구분이 어렵습니다."
        )

    grade = st.session_state.get("select_grade", "")
    class_name = st.session_state.get("select_class", "")
    student_number = int(st.session_state.get("input_student_number", 1))

    excel_bytes = create_order_excel(
        grade=grade,
        class_name=class_name,
        student_number=student_number,
        student_name=student_name,
        selected_items=totals["selected_items"],
        total_amount=totals["total_amount"],
    )

    filename = (
        "Eduino_품목내역_"
        f"{sanitize_filename(grade)}_"
        f"{sanitize_filename(class_name)}_"
        f"{student_number}번_"
        f"{sanitize_filename(student_name)}.xlsx"
    )

    st.download_button(
        label="📗 Excel 품목내역 다운로드",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )

    st.caption(
        "Excel은 기안문형 품목내역으로 생성되며, 학생 정보와 합계가 함께 포함됩니다."
    )


def render_final_submit():
    """Google Sheets 제출 섹션을 렌더링한다."""
    st.markdown("---")
    st.subheader("📤 최종 제출")
    st.caption("현재 장바구니 내용을 학교 주문 시스템에 제출합니다.")

    totals = calculate_cart_totals()

    if totals["selected_count"] == 0:
        st.warning("제출할 상품이 없습니다.")
        return

    student_name = st.session_state.get("input_student_name", "").strip()
    if not student_name:
        st.warning("학생명 / 팀원명을 입력해주세요.")
        return

    if st.button(
        "📤 주문 내역 최종 제출",
        use_container_width=True,
        type="primary",
        disabled=st.session_state.get("submit_in_progress", False),
    ):
        st.session_state["submit_in_progress"] = True
        st.rerun()

    if st.session_state.get("submit_in_progress", False):
        with st.spinner("주문 내역을 제출하고 있습니다..."):
            result = submit_order_to_sheet(
                grade=st.session_state.get("select_grade", ""),
                class_name=st.session_state.get("select_class", ""),
                student_number=st.session_state.get("input_student_number", 1),
                student_name=student_name,
                selected_items=totals["selected_items"],
                total_amount=totals["total_amount"],
            )

        if result.get("success"):
            st.success("✅ 주문 내역이 정상적으로 제출되었습니다.")
            st.session_state["submit_in_progress"] = False
        else:
            st.error(f"❌ 제출에 실패했습니다.\n{result.get('message', 'Google Sheets 제출 실패')}")
            st.session_state["submit_in_progress"] = False


# ============================================================================
# 선택 상품 요약
# ============================================================================


def render_selected_summary():
    totals = calculate_cart_totals()

    st.markdown("---")
    st.subheader("📋 선택 상품 요약")

    if totals["selected_count"] == 0:
        st.info("✅ 담긴 상품이 없습니다.")
    else:
        selected_df = pd.DataFrame(totals["selected_items"])

        selected_df = selected_df[
            ["상품코드", "상품명", "옵션", "단가", "수량", "금액"]
        ]

        st.dataframe(
            selected_df,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "선택 주문 항목",
                f"{totals['selected_count']}종",
            )

        with col2:
            st.metric(
                "전체 구매 수량",
                f"{totals['total_quantity']}개",
            )

        with col3:
            st.metric(
                "총 구매 예상금액",
                f"{format_currency(totals['total_amount'])}원",
            )

    st.markdown("---")
    st.subheader("💰 총 구매 금액 요약")

    if totals["selected_count"] == 0:
        st.info("담긴 상품이 없으므로 총액을 계산할 수 없습니다.")
    else:
        st.markdown(
            f"### 💵 총 구매 예상금액: "
            f"**{format_currency(totals['total_amount'])}원**"
        )

        st.markdown(
            f"""
            - 선택 주문 항목: **{totals['selected_count']}종**
            - 전체 구매 수량: **{totals['total_quantity']}개**
            - 총액: **{format_currency(totals['total_amount'])}원**
            """
        )


# ============================================================================
# 메인 앱
# ============================================================================


def render_student_app():
    st.markdown(
        """
        <style>
            div[data-testid="stSelectbox"] {
                min-width: 140px;
            }

            .eduino-product-header {
                font-weight: 700;
                font-size: 0.92rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🤖 Eduino 구매 체크 확인")
    st.markdown("---")

    init_session_state()

    data_path = Path(__file__).parent / "data/products.csv"

    if not data_path.exists():
        st.error("❌ data/products.csv 파일을 찾을 수 없습니다.")
        st.stop()

    products_df = load_products(
        str(data_path),
        data_path.stat().st_mtime_ns,
    )

    if products_df.empty:
        st.stop()

    st.subheader("📝 학생/팀 기본정보")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.selectbox(
            "학년",
            options=["1학년", "2학년", "3학년", "기타"],
            key="select_grade",
        )

    with col2:
        st.selectbox(
            "반",
            options=["1반", "2반", "3반", "4반", "5반"],
            key="select_class",
        )

    with col3:
        st.number_input(
            "번호",
            min_value=1,
            max_value=50,
            value=1,
            step=1,
            key="input_student_number",
        )

    with col4:
        st.text_input(
            "학생명 / 팀원명",
            placeholder="예: 김철수 또는 김철수, 이영희",
            key="input_student_name",
        )

    st.markdown("---")
    st.subheader("🛒 구매 체크리스트")
    st.caption(
        "필요한 상품의 옵션과 수량을 정한 뒤 **담기** 버튼을 눌러주세요. "
        "옵션에 추가금액이 있는 상품은 선택한 옵션에 따라 단가와 금액이 자동으로 변경됩니다. "
        "같은 상품을 다시 담으면 동일한 옵션 기준으로 수량이 누적됩니다."
    )

    categories = products_df["category"].dropna().unique().tolist()

    if "보드" in categories:
        render_board_category(products_df)
        st.markdown("")

    if "센서" in categories:
        render_sensor_category(products_df)
        st.markdown("")

    if "전자부품" in categories:
        render_electronic_parts_category(products_df)
        st.markdown("")

    reserved_categories = {"보드", "센서", "전자부품"}

    for category in categories:
        if category in reserved_categories:
            continue

        render_generic_category(products_df, category)
        st.markdown("")

    render_cart()
    render_selected_summary()
    render_csv_download()
    render_excel_download()
    render_final_submit()

    render_top_notification()


def main():
    st.set_page_config(
        page_title="Eduino 구매",
        page_icon="🛒",
        layout="wide",
    )

    render_auth_sidebar()

    student_page = st.Page(
        "views/student_page.py",
        title="Eduino 구매",
        icon="🛒",
        default=True,
    )

    teacher_page = st.Page(
        "pages/1_교사용_주문관리.py",
        title="교사용 주문관리",
        icon="🧑‍🏫",
    )

    pages = [student_page]
    if is_teacher():
        pages.append(teacher_page)

    navigation = st.navigation(pages)
    navigation.run()


if __name__ == "__main__":
    main()