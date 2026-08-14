import streamlit as st
import pandas as pd
from pathlib import Path
from utils.calculator import format_currency

# ============================================================================
# 페이지 설정
# ============================================================================

st.set_page_config(
    page_title="Eduino 구매 체크 확인",
    page_icon="🤖",
    layout="wide",
)

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


@st.cache_data
def load_products():
    """products.csv를 로드하고 필요한 컬럼을 정규화한다."""
    data_path = Path(__file__).parent / "data/products.csv"

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

        text_columns = [
            "category",
            "subcategories",
            "code",
            "name",
            "url",
            "option_name",
            "options",
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
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, dict) else value


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


def add_to_cart(row, quantity, option=""):
    """상품을 장바구니에 추가한다. 같은 코드+옵션이면 수량을 누적한다."""
    code = str(row["code"]).strip()
    quantity = max(1, int(quantity))
    option = str(option).strip() if option else ""

    cart_key = make_cart_key(code, option)

    if cart_key in st.session_state["cart"]:
        st.session_state["cart"][cart_key]["quantity"] += quantity
    else:
        st.session_state["cart"][cart_key] = {
            "code": code,
            "name": str(row["name"]),
            "option": option,
            "price": int(row["price"]),
            "quantity": quantity,
            "category": str(row["category"]),
            "subcategories": str(row.get("subcategories", "")),
            "url": str(row.get("url", "")),
        }


def remove_from_cart(cart_key):
    """장바구니 항목을 삭제한다."""
    st.session_state["cart"].pop(cart_key, None)


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

    with col_price:
        st.text(f"{format_currency(row['price'])}원")

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
        preview_amount = int(row["price"]) * int(quantity)
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
            )

            option_text = f" / {selected_option}" if selected_option else ""

            st.toast(
                f"{row['name']}{option_text} {int(quantity)}개를 담았습니다."
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
            quantity = st.number_input(
                "장바구니 수량",
                min_value=1,
                value=max(1, int(item["quantity"])),
                step=1,
                key=f"cart_qty_{cart_key}",
                label_visibility="collapsed",
            )

            st.session_state["cart"][cart_key]["quantity"] = int(quantity)

        with col_amount:
            amount = int(item["price"]) * int(quantity)
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


def main():
    st.title("🤖 Eduino 구매 체크 확인")
    st.markdown("---")

    init_session_state()

    products_df = load_products()

    if products_df.empty:
        st.stop()

    # ------------------------------------------------------------------------
    # 학생/팀 정보
    # ------------------------------------------------------------------------

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
        st.text_input(
            "팀명",
            placeholder="예: Arduino 팀",
            key="input_team_name",
        )

    with col4:
        st.text_input(
            "학생명 / 팀원명",
            placeholder="예: 김철수, 이영희",
            key="input_student_name",
        )

    st.markdown("---")
    st.subheader("🛒 구매 체크리스트")
    st.caption(
        "필요한 상품의 옵션과 수량을 정한 뒤 **담기** 버튼을 눌러주세요. "
        "같은 상품을 다시 담으면 동일한 옵션 기준으로 수량이 누적됩니다."
    )

    # ------------------------------------------------------------------------
    # 상품 영역
    # ------------------------------------------------------------------------

    categories = products_df["category"].dropna().unique().tolist()

    # 보드는 우선 고정적으로 먼저 표시
    if "보드" in categories:
        render_board_category(products_df)
        st.markdown("")

    # 센서
    if "센서" in categories:
        render_sensor_category(products_df)
        st.markdown("")

    # 전자부품
    if "전자부품" in categories:
        render_electronic_parts_category(products_df)
        st.markdown("")

    # 향후 추가되는 다른 카테고리도 동일한 담기 방식으로 자동 처리
    reserved_categories = {"보드", "센서", "전자부품"}

    for category in categories:
        if category in reserved_categories:
            continue

        render_generic_category(products_df, category)
        st.markdown("")

    # ------------------------------------------------------------------------
    # 장바구니 및 요약
    # ------------------------------------------------------------------------

    render_cart()
    render_selected_summary()


if __name__ == "__main__":
    main()