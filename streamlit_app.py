import streamlit as st
import pandas as pd
from pathlib import Path
from utils.calculator import calculate_product_amount, format_currency

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
        div[data-testid="stCheckbox"] > label > div:first-child {
            transform: scale(1.5);
            transform-origin: left center;
            margin-right: 0.5rem;
        }
        div[data-testid="stCheckbox"] {
            padding: 0.15rem 0;
        }
        div[data-testid="stSelectbox"] {
            min-width: 140px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# 공통 유틸
# ============================================================================


def normalize_subcategories(value):
    """상품의 분류 문자열을 리스트로 변환한다."""
    if pd.isna(value):
        return []

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        return [item.strip() for item in cleaned.split("|") if item.strip()]

    text = str(value).strip()
    return [text] if text else []


def parse_options(value):
    """CSV options 문자열을 리스트로 변환한다."""
    if pd.isna(value):
        return []

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []

    return [item.strip() for item in text.split("|") if item.strip()]


def has_options(row):
    return len(parse_options(row.get("options", ""))) > 0


def get_product_row(products_df, code):
    """상품코드로 첫 번째 상품 행을 조회한다."""
    matched = products_df[products_df["code"].astype(str).str.strip() == str(code).strip()]
    if matched.empty:
        return None
    return matched.iloc[0]


# ============================================================================
# 데이터 로드
# ============================================================================


@st.cache_data
def load_products():
    """products.csv를 로드하고 필요한 컬럼을 정규화한다."""
    data_path = Path(__file__).parent / "data/products.csv"

    try:
        df = pd.read_csv(data_path)

        if "subcategories" not in df.columns:
            df["subcategories"] = ""

        if "subcategory" in df.columns:
            df["subcategories"] = df["subcategories"].fillna(df["subcategory"])

        df["subcategories"] = df["subcategories"].fillna("").map(
            lambda v: "" if pd.isna(v) else str(v).strip()
        )
        df["category"] = df["category"].fillna("").map(
            lambda v: "" if pd.isna(v) else str(v).strip()
        )

        if "subcategory" not in df.columns:
            df["subcategory"] = df["subcategories"]
        else:
            df["subcategory"] = df["subcategory"].fillna(df["subcategories"]).map(
                lambda v: "" if pd.isna(v) else str(v).strip()
            )

        if "option_name" not in df.columns:
            df["option_name"] = ""
        if "options" not in df.columns:
            df["options"] = ""

        df["option_name"] = df["option_name"].fillna("").map(
            lambda v: "" if pd.isna(v) else str(v).strip()
        )
        df["options"] = df["options"].fillna("").map(
            lambda v: "" if pd.isna(v) else str(v).strip()
        )

        df["code"] = df["code"].fillna("").map(str).map(str.strip)
        df["name"] = df["name"].fillna("").map(str)
        df["url"] = df["url"].fillna("").map(str)

        df["price"] = pd.to_numeric(df["price"], errors="coerce")

        nan_count = df["price"].isna().sum()
        if nan_count > 0:
            st.warning(
                f"⚠️ {nan_count}개 상품의 가격 변환 실패. 해당 상품은 0원으로 처리됩니다."
            )
            df["price"] = df["price"].fillna(0)

        return df

    except FileNotFoundError:
        st.error("❌ products.csv 파일을 찾을 수 없습니다.")
        return pd.DataFrame()


# ============================================================================
# 세션 상태
# ============================================================================


def init_session_state():
    defaults = {
        "selections": {},
        "quantities": {},
        "product_options": {},
        # 옵션형 상품은 코드 단위가 아니라 "상품코드 + 옵션" 단위로 별도 보관
        "option_cart": {},
        "selected_sensor_category": "환경",
        "selected_parts_category": "IC/기본소자",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, dict) else value


def make_variant_key(code, option):
    return f"{code}::{option}"


def add_option_variant(row, option, quantity):
    """옵션형 상품을 옵션별 장바구니에 추가한다."""
    code = str(row["code"]).strip()
    quantity = max(1, int(quantity))
    price = int(row["price"])
    key = make_variant_key(code, option)

    if key in st.session_state["option_cart"]:
        st.session_state["option_cart"][key]["quantity"] += quantity
    else:
        st.session_state["option_cart"][key] = {
            "code": code,
            "name": row["name"],
            "option": option,
            "price": price,
            "quantity": quantity,
        }


def remove_option_variant(variant_key):
    st.session_state["option_cart"].pop(variant_key, None)


# ============================================================================
# 합계 계산
# ============================================================================


def calculate_app_totals(products_df):
    """
    일반 상품 + 옵션별 장바구니를 하나의 주문 목록으로 합친다.

    핵심:
    - 옵션이 없는 상품: 기존 selections / quantities 기준
    - 옵션이 있는 상품: option_cart 기준
    - 같은 상품코드라도 옵션이 다르면 서로 다른 주문 행으로 유지
    """
    selected_items = []

    option_product_codes = set(
        products_df[
            products_df["options"].fillna("").astype(str).str.strip().ne("")
        ]["code"].astype(str).str.strip()
    )

    # 1) 옵션이 없는 일반 상품
    for _, row in products_df.iterrows():
        code = str(row["code"]).strip()

        # 옵션형 상품은 아래 option_cart에서만 계산한다.
        if code in option_product_codes:
            continue

        is_selected = bool(st.session_state["selections"].get(code, False))
        quantity = int(st.session_state["quantities"].get(code, 0) or 0)

        if not is_selected or quantity <= 0:
            continue

        price = int(row["price"])
        amount = price * quantity

        selected_items.append(
            {
                "상품코드": code,
                "상품명": row["name"],
                "옵션": "-",
                "단가": price,
                "수량": quantity,
                "금액": amount,
            }
        )

    # 2) 옵션형 상품
    for variant_key, item in st.session_state["option_cart"].items():
        quantity = max(1, int(item["quantity"]))
        price = int(item["price"])
        amount = price * quantity

        selected_items.append(
            {
                "상품코드": item["code"],
                "상품명": item["name"],
                "옵션": item["option"],
                "단가": price,
                "수량": quantity,
                "금액": amount,
            }
        )

    total_quantity = sum(int(item["수량"]) for item in selected_items)
    total_amount = sum(int(item["금액"]) for item in selected_items)

    return {
        "selected_items": selected_items,
        # 옵션이 다르면 주문 행도 다르므로 각각 1종으로 집계
        "selected_count": len(selected_items),
        "total_quantity": total_quantity,
        "total_amount": total_amount,
    }


# ============================================================================
# 공통 일반 상품 행
# ============================================================================


def render_standard_product_row(row, layout=(1, 2, 1.5, 1.5, 1, 1.5)):
    code = str(row["code"]).strip()
    check_key = f"check_{code}"
    qty_key = f"qty_{code}"

    col1, col2, col3, col4, col5, col6 = st.columns(layout)

    with col1:
        is_selected = st.checkbox(
            "선택",
            key=check_key,
            value=st.session_state["selections"].get(code, False),
            label_visibility="collapsed",
        )
        st.session_state["selections"][code] = is_selected

    with col2:
        product_name = row["name"]
        product_url = str(row["url"]).strip()

        if product_url and product_url.lower() != "nan":
            st.markdown(f"[{product_name}]({product_url})")
        else:
            st.text(product_name)

    with col3:
        st.text(code)

    with col4:
        st.text(f"{format_currency(row['price'])}원")

    with col5:
        stored_qty = int(st.session_state["quantities"].get(code, 1) or 1)
        current_qty = max(1, stored_qty)

        quantity = st.number_input(
            "수량",
            min_value=1,
            value=current_qty if is_selected else 1,
            step=1,
            key=qty_key,
            disabled=not is_selected,
            label_visibility="collapsed",
        )

        if is_selected:
            st.session_state["quantities"][code] = max(1, int(quantity))
        else:
            st.session_state["quantities"][code] = 0

    with col6:
        amount = calculate_product_amount(
            is_selected,
            st.session_state["quantities"].get(code, 0),
            row["price"],
        )
        st.text(f"{format_currency(amount)}원")


# ============================================================================
# 센서 & 모듈
# ============================================================================


def render_sensor_category(products_df):
    """센서 & 모듈 분류형 UI를 렌더링한다."""
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

    selected_sensor_category = st.session_state["selected_sensor_category"]

    st.subheader("📡 센서 & 모듈")
    st.caption("센서 유형을 선택하면 해당 분류의 상품을 확인할 수 있습니다.")

    for row_start in range(0, len(sensor_categories), 6):
        cols = st.columns(6)
        row_categories = sensor_categories[row_start : row_start + 6]

        for col_idx, category_name in enumerate(row_categories):
            with cols[col_idx]:
                is_selected = selected_sensor_category == category_name

                if st.button(
                    category_name,
                    key=f"sensor_category_{category_name}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state["selected_sensor_category"] = category_name
                    st.rerun()

    st.info(f"현재 선택: **{selected_sensor_category}**")

    sensor_df = products_df[
        (products_df["category"] == "센서")
        & products_df.apply(
            lambda row: selected_sensor_category
            in normalize_subcategories(
                row.get("subcategories", row.get("subcategory", ""))
            ),
            axis=1,
        )
    ].copy()

    if sensor_df.empty:
        st.info("해당 분류의 상품은 추후 추가될 예정입니다.")
        return

    for _, row in sensor_df.iterrows():
        # 현재 센서 데이터는 옵션 상품이 없으므로 기존 구조 유지.
        # 향후 센서 옵션상품을 넣을 경우 전자부품과 같은 option_cart 방식으로 확장 가능.
        render_standard_product_row(row)
        st.markdown("")


# ============================================================================
# 전자부품
# ============================================================================


def render_option_cart_for_current_category(parts_df):
    """현재 전자부품 분류에서 담은 옵션 상품을 간단히 관리한다."""
    visible_codes = set(parts_df["code"].astype(str).str.strip())

    current_items = [
        (key, item)
        for key, item in st.session_state["option_cart"].items()
        if item["code"] in visible_codes
    ]

    if not current_items:
        return

    with st.expander("🧺 현재 분류에서 담은 옵션 상품", expanded=True):
        h1, h2, h3, h4, h5 = st.columns([2.8, 1.8, 1.2, 1.4, 0.8])
        h1.caption("상품명")
        h2.caption("옵션")
        h3.caption("수량")
        h4.caption("금액")
        h5.caption("삭제")

        for variant_key, item in current_items:
            c1, c2, c3, c4, c5 = st.columns([2.8, 1.8, 1.2, 1.4, 0.8])

            with c1:
                st.text(item["name"])

            with c2:
                st.text(item["option"])

            with c3:
                new_qty = st.number_input(
                    "담긴 수량",
                    min_value=1,
                    value=max(1, int(item["quantity"])),
                    step=1,
                    key=f"cart_qty_{variant_key}",
                    label_visibility="collapsed",
                )
                st.session_state["option_cart"][variant_key]["quantity"] = int(new_qty)

            with c4:
                st.text(
                    f"{format_currency(int(item['price']) * int(new_qty))}원"
                )

            with c5:
                if st.button(
                    "🗑️",
                    key=f"remove_{variant_key}",
                    help="이 옵션을 주문 목록에서 삭제",
                ):
                    remove_option_variant(variant_key)
                    st.rerun()


def render_electronic_parts_category(products_df):
    """전자부품 분류형 UI를 렌더링한다."""
    parts_categories = [
        "IC/기본소자",
        "주변부품",
        "브레드보드",
        "케이블",
        "배터리/전원",
    ]

    if st.session_state["selected_parts_category"] not in parts_categories:
        st.session_state["selected_parts_category"] = "IC/기본소자"

    selected_parts_category = st.session_state["selected_parts_category"]

    st.subheader("🔌 전자부품")
    st.caption("전자부품 유형을 선택하면 해당 분류의 상품을 확인할 수 있습니다.")

    cols = st.columns(5)
    for idx, category_name in enumerate(parts_categories):
        with cols[idx]:
            is_selected = selected_parts_category == category_name

            if st.button(
                category_name,
                key=f"parts_category_{category_name}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state["selected_parts_category"] = category_name
                st.rerun()

    st.info(f"현재 선택: **{selected_parts_category}**")

    parts_df = products_df[
        (products_df["category"] == "전자부품")
        & products_df.apply(
            lambda row: selected_parts_category
            in normalize_subcategories(
                row.get("subcategories", row.get("subcategory", ""))
            ),
            axis=1,
        )
    ].copy()

    if parts_df.empty:
        st.info("해당 분류의 상품은 추후 추가될 예정입니다.")
        return

    header_cols = st.columns([0.7, 3.0, 1.2, 1.2, 1.8, 1.3, 1.2, 1.0])
    headers = ["선택", "상품명", "상품코드", "단가", "옵션", "수량", "금액", "담기"]

    for col, text in zip(header_cols, headers):
        with col:
            st.caption(text)

    for _, row in parts_df.iterrows():
        code = str(row["code"]).strip()
        option_name = str(row.get("option_name", "") or "").strip()
        option_values = parse_options(row.get("options", ""))

        check_key = f"check_{code}"

        (
            col_check,
            col_name,
            col_code,
            col_price,
            col_option,
            col_qty,
            col_amount,
            col_add,
        ) = st.columns([0.7, 3.0, 1.2, 1.2, 1.8, 1.3, 1.2, 1.0])

        with col_check:
            is_selected = st.checkbox(
                "선택",
                key=check_key,
                value=st.session_state["selections"].get(code, False),
                label_visibility="collapsed",
            )
            st.session_state["selections"][code] = is_selected

        with col_name:
            product_url = str(row["url"]).strip()
            if product_url and product_url.lower() != "nan":
                st.markdown(f"[{row['name']}]({product_url})")
            else:
                st.text(row["name"])

        with col_code:
            st.text(code)

        with col_price:
            st.text(f"{format_currency(row['price'])}원")

        # --------------------------------------------------------------------
        # 옵션형 상품: "선택 → 옵션/수량 지정 → 담기" 방식
        # 동일 코드라도 옵션별로 option_cart에 별도 저장된다.
        # --------------------------------------------------------------------
        if option_values:
            option_widget_key = f"draft_option_{code}"
            qty_widget_key = f"draft_qty_{code}"

            with col_option:
                selected_option = st.selectbox(
                    option_name or "옵션",
                    options=option_values,
                    key=option_widget_key,
                    disabled=not is_selected,
                    label_visibility="collapsed",
                )

            with col_qty:
                draft_qty = st.number_input(
                    "수량",
                    min_value=1,
                    value=1,
                    step=1,
                    key=qty_widget_key,
                    disabled=not is_selected,
                    label_visibility="collapsed",
                )

            with col_amount:
                preview_amount = int(row["price"]) * int(draft_qty) if is_selected else 0
                st.text(f"{format_currency(preview_amount)}원")

            with col_add:
                if st.button(
                    "➕ 담기",
                    key=f"add_variant_{code}",
                    use_container_width=True,
                    disabled=not is_selected,
                ):
                    add_option_variant(
                        row=row,
                        option=selected_option,
                        quantity=draft_qty,
                    )
                    st.toast(
                        f"{row['name']} / {selected_option} {int(draft_qty)}개를 추가했습니다."
                    )
                    st.rerun()

            # 옵션형 상품은 일반 quantities 계산 대상에서 제외
            st.session_state["quantities"][code] = 0
            st.session_state["product_options"][code] = selected_option

        # --------------------------------------------------------------------
        # 일반 상품: 기존 체크 + 수량 방식
        # --------------------------------------------------------------------
        else:
            with col_option:
                st.text("-")

            with col_qty:
                stored_qty = int(st.session_state["quantities"].get(code, 1) or 1)
                current_qty = max(1, stored_qty)

                quantity = st.number_input(
                    "수량",
                    min_value=1,
                    value=current_qty if is_selected else 1,
                    step=1,
                    key=f"qty_{code}",
                    disabled=not is_selected,
                    label_visibility="collapsed",
                )

                if is_selected:
                    st.session_state["quantities"][code] = max(1, int(quantity))
                else:
                    st.session_state["quantities"][code] = 0

            with col_amount:
                amount = calculate_product_amount(
                    is_selected,
                    st.session_state["quantities"].get(code, 0),
                    row["price"],
                )
                st.text(f"{format_currency(amount)}원")

            with col_add:
                st.text("-")

            st.session_state["product_options"].pop(code, None)

        st.markdown("")

    render_option_cart_for_current_category(parts_df)


# ============================================================================
# 선택 상품 요약
# ============================================================================


def render_selected_summary(products_df):
    st.markdown("---")
    st.subheader("📋 선택 상품 요약")

    totals = calculate_app_totals(products_df)

    if totals["selected_count"] == 0:
        st.info("✅ 선택된 상품이 없습니다.")
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
            st.metric("선택 주문 항목", f"{totals['selected_count']}종")

        with col2:
            st.metric("전체 구매 수량", f"{totals['total_quantity']}개")

        with col3:
            st.metric(
                "총 구매 예상금액",
                f"{format_currency(totals['total_amount'])}원",
            )

    st.markdown("---")
    st.subheader("💰 총 구매 금액 요약")

    if totals["selected_count"] == 0:
        st.info("선택된 상품이 없으므로 총액을 계산할 수 없습니다.")
    else:
        st.markdown(
            f"### 💵 총 구매 예상금액: "
            f"**{format_currency(totals['total_amount'])}원**"
        )

        summary_text = f"""
        - 선택 주문 항목: **{totals['selected_count']}종**
        - 전체 구매 수량: **{totals['total_quantity']}개**
        - 총액: **{format_currency(totals['total_amount'])}원**
        """
        st.markdown(summary_text)


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

    categories = products_df["category"].dropna().unique()

    for category in categories:
        if category == "센서":
            render_sensor_category(products_df)
            st.markdown("")
            continue

        if category == "전자부품":
            render_electronic_parts_category(products_df)
            st.markdown("")
            continue

        category_df = products_df[products_df["category"] == category].copy()
        st.subheader(f"📌 {category}")

        for _, row in category_df.iterrows():
            render_standard_product_row(row)
            st.markdown("")

    render_selected_summary(products_df)


if __name__ == "__main__":
    main()