"""
Eduino 구매 계산 로직
"""


def calculate_product_amount(selected, quantity, price):
    """
    상품별 금액을 계산한다.
    
    Args:
        selected (bool): 상품 선택 여부
        quantity (int): 구매 수량
        price (float): 단가
    
    Returns:
        float: 상품별 금액 (선택되지 않으면 0)
    """
    if not selected:
        return 0
    return quantity * price


def calculate_totals(products_df, selections, quantities):
    """
    총 구매 정보를 계산한다.
    
    Args:
        products_df (pd.DataFrame): 상품 정보 데이터프레임
        selections (dict): {row_index: bool} 상품별 선택 여부
        quantities (dict): {row_index: int} 상품별 수량
    
    Returns:
        dict: {
            'total_amount': float (총 금액),
            'total_quantity': int (총 수량),
            'selected_count': int (선택 상품 종류 수),
            'selected_items': list (선택된 상품 정보)
        }
    """
    total_amount = 0
    total_quantity = 0
    selected_count = 0
    selected_items = []
    
    for idx, row in products_df.iterrows():
        is_selected = selections.get(idx, False)
        qty = quantities.get(idx, 0) if is_selected else 0
        
        if is_selected:
            selected_count += 1
            total_quantity += qty
            amount = qty * row['price']
            total_amount += amount
            
            selected_items.append({
                '카테고리': row['category'],
                '상품코드': row['code'],
                '상품명': row['name'],
                '단가': int(row['price']),
                '수량': qty,
                '금액': int(amount)
            })
    
    return {
        'total_amount': total_amount,
        'total_quantity': total_quantity,
        'selected_count': selected_count,
        'selected_items': selected_items
    }


def format_currency(amount):
    """
    금액을 천 단위 쉼표가 있는 문자열로 변환한다.
    
    Args:
        amount (float): 금액
    
    Returns:
        str: 포맷된 금액 (예: "32,500")
    """
    return f"{int(amount):,}"
