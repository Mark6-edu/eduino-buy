import streamlit as st
import pandas as pd
from pathlib import Path
from utils.calculator import calculate_product_amount, calculate_totals, format_currency

# ============================================================================
# 페이지 설정
# ============================================================================

st.set_page_config(
    page_title='Eduino 구매 체크 확인',
    page_icon='🤖',
    layout='wide'
)

# ============================================================================
# 데이터 로드 함수
# ============================================================================


def normalize_subcategories(value):
    """상품의 분류 문자열을 리스트로 변환한다."""
    if pd.isna(value):
        return []

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        return [item.strip() for item in cleaned.split('|') if item.strip()]

    return [str(value).strip()] if str(value).strip() else []


@st.cache_data
def load_products():
    """
    products.csv를 로드하고 가격을 숫자형으로 변환한다.
    """
    data_path = Path(__file__).parent / 'data/products.csv'

    try:
        df = pd.read_csv(data_path)

        if 'subcategories' not in df.columns:
            df['subcategories'] = ''

        if 'subcategory' in df.columns:
            df['subcategories'] = df['subcategories'].fillna(df['subcategory'])

        df['subcategories'] = df['subcategories'].fillna('').map(
            lambda v: '' if pd.isna(v) else str(v).strip()
        )
        df['category'] = df['category'].fillna('').map(
            lambda v: '' if pd.isna(v) else str(v).strip()
        )

        if 'subcategory' not in df.columns:
            df['subcategory'] = df['subcategories']
        else:
            df['subcategory'] = df['subcategory'].fillna(df['subcategories']).map(
                lambda v: '' if pd.isna(v) else str(v).strip()
            )

        df['price'] = pd.to_numeric(df['price'], errors='coerce')

        nan_count = df['price'].isna().sum()
        if nan_count > 0:
            st.warning(f"⚠️ {nan_count}개 상품의 가격 변환 실패. 해당 상품은 0원으로 처리됩니다.")
            df['price'] = df['price'].fillna(0)

        return df

    except FileNotFoundError:
        st.error("❌ products.csv 파일을 찾을 수 없습니다.")
        return pd.DataFrame()


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

    if 'selected_sensor_category' not in st.session_state:
        st.session_state['selected_sensor_category'] = "환경"
    if st.session_state['selected_sensor_category'] not in sensor_categories:
        st.session_state['selected_sensor_category'] = "환경"

    selected_sensor_category = st.session_state['selected_sensor_category']

    st.subheader("📡 센서 & 모듈")
    st.caption("센서 유형을 선택하면 해당 분류의 상품을 확인할 수 있습니다.")

    cols = st.columns(6)
    for idx, category_name in enumerate(sensor_categories):
        with cols[idx % len(cols)]:
            is_selected = selected_sensor_category == category_name
            if st.button(
                category_name,
                key=f"sensor_category_{category_name}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state['selected_sensor_category'] = category_name
                st.rerun()

    st.info(f"현재 선택: **{selected_sensor_category}**")

    sensor_df = products_df[
        (products_df['category'] == '센서') &
        products_df.apply(
            lambda row: selected_sensor_category in normalize_subcategories(
                row.get('subcategories', row.get('subcategory', ''))
            ),
            axis=1,
        )
    ].copy()

    if sensor_df.empty:
        st.info("해당 분류의 상품은 추후 추가될 예정입니다.")
        return

    for _, row in sensor_df.iterrows():
        code = str(row['code']).strip()
        check_key = f"check_{code}"
        qty_key = f"qty_{code}"

        col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 1.5, 1.5, 1, 1.5])

        with col1:
            is_selected = st.checkbox(
                "선택",
                key=check_key,
                value=st.session_state['selections'].get(code, False),
                label_visibility="collapsed",
            )
            st.session_state['selections'][code] = is_selected

        with col2:
            product_name = row['name']
            product_url = row['url']
            if pd.notna(product_url) and str(product_url).strip() and str(product_url).strip() != 'nan':
                st.markdown(f"[{product_name}]({product_url})")
            else:
                st.text(product_name)

        with col3:
            st.text(f"{code}")

        with col4:
            st.text(f"{format_currency(row['price'])}원")

        with col5:
            current_qty = max(1, int(st.session_state['quantities'].get(code, 1)))
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
                st.session_state['quantities'][code] = max(1, int(quantity))
            else:
                st.session_state['quantities'][code] = 0

        with col6:
            amount = calculate_product_amount(
                is_selected,
                st.session_state['quantities'].get(code, 0),
                row['price']
            )
            st.text(f"{format_currency(amount)}원")

        st.markdown("")


# ============================================================================
# 메인 앱
# ============================================================================

def main():
    st.title("🤖 Eduino 구매 체크 확인")
    st.markdown("---")

    products_df = load_products()

    if products_df.empty:
        st.stop()

    st.subheader("📝 학생/팀 기본정보")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.selectbox(
            "학년",
            options=["1학년", "2학년", "3학년", "기타"],
            key="select_grade"
        )

    with col2:
        st.selectbox(
            "반",
            options=["1반", "2반", "3반", "4반", "5반"],
            key="select_class"
        )

    with col3:
        st.text_input(
            "팀명",
            placeholder="예: Arduino 팀",
            key="input_team_name"
        )

    with col4:
        st.text_input(
            "학생명 / 팀원명",
            placeholder="예: 김철수, 이영희",
            key="input_student_name"
        )

    st.markdown("---")

    st.subheader("🛒 구매 체크리스트")

    if 'selections' not in st.session_state:
        st.session_state['selections'] = {}
    if 'quantities' not in st.session_state:
        st.session_state['quantities'] = {}

    categories = products_df['category'].unique()

    for category in categories:
        if category == '센서':
            render_sensor_category(products_df)
            st.markdown("")
            continue

        category_df = products_df[products_df['category'] == category].copy()
        st.subheader(f"📌 {category}")

        for _, row in category_df.iterrows():
            code = str(row['code']).strip()
            check_key = f"check_{code}"
            qty_key = f"qty_{code}"

            col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 1.5, 1.5, 1, 1.5])

            with col1:
                is_selected = st.checkbox(
                    "선택",
                    key=check_key,
                    value=st.session_state['selections'].get(code, False),
                    label_visibility="collapsed"
                )
                st.session_state['selections'][code] = is_selected

            with col2:
                product_name = row['name']
                product_url = row['url']

                if pd.notna(product_url) and str(product_url).strip() and str(product_url).strip() != 'nan':
                    st.markdown(f"[{product_name}]({product_url})")
                else:
                    st.text(product_name)

            with col3:
                st.text(f"{code}")

            with col4:
                st.text(f"{format_currency(row['price'])}원")

            with col5:
                current_qty = max(1, int(st.session_state['quantities'].get(code, 1)))
                quantity = st.number_input(
                    "수량",
                    min_value=1,
                    value=current_qty if is_selected else 1,
                    step=1,
                    key=qty_key,
                    disabled=not is_selected,
                    label_visibility="collapsed"
                )

                if is_selected:
                    st.session_state['quantities'][code] = max(1, int(quantity))
                else:
                    st.session_state['quantities'][code] = 0

            with col6:
                amount = calculate_product_amount(
                    is_selected,
                    st.session_state['quantities'].get(code, 0),
                    row['price']
                )
                st.text(f"{format_currency(amount)}원")

        st.markdown("")

    st.markdown("---")

    st.subheader("📋 선택 상품 요약")

    totals = calculate_totals(
        products_df,
        st.session_state['selections'],
        st.session_state['quantities']
    )

    if totals['selected_count'] == 0:
        st.info("✅ 선택된 상품이 없습니다.")
    else:
        selected_df = pd.DataFrame(totals['selected_items'])
        st.dataframe(
            selected_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("선택 상품 종류", f"{totals['selected_count']}종")

        with col2:
            st.metric("전체 구매 수량", f"{totals['total_quantity']}개")

        with col3:
            st.metric(
                "총 구매 예상금액",
                f"{format_currency(totals['total_amount'])}원"
            )

    st.markdown("---")

    st.subheader("💰 총 구매 금액 요약")

    if totals['selected_count'] == 0:
        st.info("선택된 상품이 없으므로 총액을 계산할 수 없습니다.")
    else:
        st.markdown(f"### 💵 총 구매 예상금액: **{format_currency(totals['total_amount'])}원**")

        summary_text = f"""
        - 선택 상품 종류: **{totals['selected_count']}종**
        - 전체 구매 수량: **{totals['total_quantity']}개**
        - 총액: **{format_currency(totals['total_amount'])}원**
        """
        st.markdown(summary_text)


if __name__ == "__main__":
    main()
