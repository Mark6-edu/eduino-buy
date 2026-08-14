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

@st.cache_data
def load_products():
    """
    products.csv를 로드하고 가격을 숫자형으로 변환한다.
    """
    data_path = Path(__file__).parent / 'data/products.csv'
    
    try:
        df = pd.read_csv(data_path)
        
        # price 컬럼을 숫자형으로 변환
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        # 가격 변환 실패 시 NaN 값이 생기는데, 0으로 채우고 경고
        nan_count = df['price'].isna().sum()
        if nan_count > 0:
            st.warning(f"⚠️ {nan_count}개 상품의 가격 변환 실패. 해당 상품은 0원으로 처리됩니다.")
            df['price'] = df['price'].fillna(0)
        
        return df
    
    except FileNotFoundError:
        st.error("❌ products.csv 파일을 찾을 수 없습니다.")
        return pd.DataFrame()


# ============================================================================
# 메인 앱
# ============================================================================

def main():
    # 제목
    st.title("🤖 Eduino 구매 체크 확인")
    st.markdown("---")
    
    # 데이터 로드
    products_df = load_products()
    
    if products_df.empty:
        st.stop()
    
    # ========================================================================
    # 1. 학생/팀 기본정보 입력
    # ========================================================================
    st.subheader("📝 학생/팀 기본정보")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        grade = st.selectbox(
            "학년",
            options=["1학년", "2학년", "3학년", "기타"],
            key="select_grade"
        )
    
    with col2:
        class_num = st.selectbox(
            "반",
            options=["1반", "2반", "3반", "4반", "5반"],
            key="select_class"
        )
    
    with col3:
        team_name = st.text_input(
            "팀명",
            placeholder="예: Arduino 팀",
            key="input_team_name"
        )
    
    with col4:
        student_name = st.text_input(
            "학생명 / 팀원명",
            placeholder="예: 김철수, 이영희",
            key="input_student_name"
        )
    
    st.markdown("---")
    
    # ========================================================================
    # 2. 구매 체크리스트 (카테고리별)
    # ========================================================================
    st.subheader("🛒 구매 체크리스트")
    
    # 세션 상태 초기화
    if 'selections' not in st.session_state:
        st.session_state['selections'] = {}
    if 'quantities' not in st.session_state:
        st.session_state['quantities'] = {}
    
    # 카테고리별 그룹화
    categories = products_df['category'].unique()
    
    for category in categories:
        category_df = products_df[products_df['category'] == category].reset_index(drop=True)
        
        st.subheader(f"📌 {category}")
        
        for idx, row in category_df.iterrows():
            # 유니크한 key 생성
            code = row['code']
            row_key = f"{category}_{code}_{idx}"
            check_key = f"check_{row_key}"
            qty_key = f"qty_{row_key}"
            
            col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 1.5, 1.5, 1, 1.5])
            
            with col1:
                is_selected = st.checkbox(
                    "선택",
                    key=check_key,
                    label_visibility="collapsed"
                )
                st.session_state['selections'][idx] = is_selected
            
            with col2:
                # 상품명을 마크다운 링크로 표시
                product_name = row['name']
                product_url = row['url']
                
                if pd.notna(product_url) and str(product_url).strip():
                    st.markdown(f"[{product_name}]({product_url})")
                else:
                    st.text(product_name)
            
            with col3:
                st.text(f"{row['code']}")
            
            with col4:
                st.text(f"{format_currency(row['price'])}원")
            
            with col5:
                quantity = st.number_input(
                    "수량",
                    min_value=1,
                    value=1,
                    step=1,
                    key=qty_key,
                    disabled=not is_selected,
                    label_visibility="collapsed"
                )
                
                if is_selected:
                    st.session_state['quantities'][idx] = quantity
                else:
                    st.session_state['quantities'][idx] = 0
            
            with col6:
                # 상품별 금액 계산
                amount = calculate_product_amount(
                    is_selected,
                    st.session_state['quantities'].get(idx, 0),
                    row['price']
                )
                st.text(f"{format_currency(amount)}원")
        
        st.markdown("")
    
    st.markdown("---")
    
    # ========================================================================
    # 3. 선택 상품 요약 표
    # ========================================================================
    st.subheader("📋 선택 상품 요약")
    
    # 총 계산
    totals = calculate_totals(
        products_df,
        st.session_state['selections'],
        st.session_state['quantities']
    )
    
    if totals['selected_count'] == 0:
        st.info("✅ 선택된 상품이 없습니다.")
    else:
        # 선택된 상품 데이터프레임 생성
        selected_df = pd.DataFrame(totals['selected_items'])
        
        # 테이블 표시
        st.dataframe(
            selected_df,
            use_container_width=True,
            hide_index=True
        )
        
        # 합계 표시
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
    
    # ========================================================================
    # 4. 총 구매 금액 요약
    # ========================================================================
    st.subheader("💰 총 구매 금액 요약")
    
    if totals['selected_count'] == 0:
        st.info("선택된 상품이 없으므로 총액을 계산할 수 없습니다.")
    else:
        # 큰 글씨로 강조 표시
        st.markdown(f"### 💵 총 구매 예상금액: **{format_currency(totals['total_amount'])}원**")
        
        summary_text = f"""
        - 선택 상품 종류: **{totals['selected_count']}종**
        - 전체 구매 수량: **{totals['total_quantity']}개**
        - 총액: **{format_currency(totals['total_amount'])}원**
        """
        st.markdown(summary_text)


# ============================================================================
# 앱 실행
# ============================================================================

if __name__ == "__main__":
    main()
