🤖 Eduino 구매 체크 확인

학교 수업용 아두이노 프로젝트 부품 구매 확인 및 주문 관리 웹 애플리케이션

📋 프로젝트 개요

Eduino 구매 체크 확인은 학생 또는 프로젝트 팀이 아두이노 프로젝트에 필요한 부품을 선택하고, 옵션과 수량을 지정한 뒤 예상 구매 금액을 자동으로 계산할 수 있도록 만든 Streamlit 기반 웹 애플리케이션입니다.

학생은 장바구니 방식으로 필요한 부품을 구성하고 CSV / Excel 구매 명세서를 다운로드하거나 최종 주문 내역을 제출할 수 있습니다.

제출된 주문 데이터는 Google Apps Script Web App을 통해 Google Sheets에 저장되며, 교사는 Google 계정 인증 후 별도의 주문관리 페이지에서 학생별 제출 현황과 전체 통합 주문 내역을 확인할 수 있습니다.

Eduino 공식 사이트:
https://eduino.kr/

✨ 주요 기능

👨‍🎓 학생 기능

1. 학생 기본정보 입력

학생 주문을 구분하기 위해 다음 정보를 입력합니다.

학년

반

번호

학생명 / 팀원명

예:

1학년
3반
15번
홍길동

2. 카테고리별 상품 선택

상품은 data/products.csv를 기반으로 표시됩니다.

주요 분류:

보드

센서 & 모듈

전자부품

센서 & 모듈은 다시 다음과 같은 세부 분류로 구분됩니다.

환경

거리/위치

수질/토양

압력/접촉

조도/적외선/컬러

LCD/디스플레이

릴레이/스위치

모터/제어

통신

LED/네오픽셀

소리/영상

가속도/자이로

전자부품은 다음 분류를 사용합니다.

IC/기본소자

주변부품

브레드보드

케이블

배터리/전원

3. 상품 옵션 선택

상품에 옵션이 있는 경우 옵션을 선택할 수 있습니다.

예:

5mm LED
→ 빨강색
→ 노랑색
→ 파랑색
→ 초록색
→ 백색

또는:

N20 DC 모터
→ 50RPM
→ 100RPM
→ 300RPM

옵션에 따라 추가금액이 있는 상품은 선택 즉시 실제 단가가 변경됩니다.

4. 옵션별 가격 자동 계산

상품 가격은 다음 방식으로 계산됩니다.

최종 단가
=
기본 가격
+
옵션 추가금액

예:

N20 모터 기본가격: 4,400원

50RPM
→ +0원
→ 4,400원

100RPM
→ +1,100원
→ 5,500원

300RPM
→ +2,200원
→ 6,600원

5. 장바구니

상품을 바로 주문 목록에 넣는 방식이 아니라 다음 과정을 사용합니다.

옵션 선택
→ 수량 입력
→ 담기
→ 장바구니

장바구니 특징:

동일 상품 + 동일 옵션 재추가 시 수량 누적

동일 상품 + 다른 옵션은 별도 품목으로 처리

장바구니에서 직접 수량 수정 가능

품목별 개별 삭제

전체 장바구니 삭제

상품 추가 시 화면 상단 팝업 알림

예:

E-14 / 빨강색 × 2
E-14 / 파랑색 × 3

두 품목은 서로 별도로 관리됩니다.

6. 주문 요약

현재 장바구니를 기반으로 다음 정보를 한 번에 확인할 수 있습니다.

선택 상품 목록

선택 품목 수

전체 구매 수량

총 구매 예상금액

예:

선택 품목
6종

총 수량
8개

총 구매 예상금액
21,310원

7. CSV 구매 명세서 다운로드

학생별 주문 내역을 CSV 파일로 다운로드할 수 있습니다.

CSV는 학교 기안문 품목내역 형태를 기준으로 구성됩니다.

예:

<품목내역>

학년,1학년
반,3반
번호,15번
학생명/팀원명,홍길동

순번,내용,규격,수량,단위,예상단가,예상금액
1-1,아두이노 우노 R3,A-1,1,개,2900,2900
1-2,아두이노 5파이 LED,빨강색,3,개,110,330

,합계,,,,,3230

파일명 예:

Eduino_품목내역_1학년_3반_15번_홍길동.csv

CSV는 Excel 한글 호환성을 위해 UTF-8 BOM 형식으로 생성됩니다.

8. Excel 구매 명세서 다운로드

학생별 주문 내역을 .xlsx 형식으로 다운로드할 수 있습니다.

Excel 문서는 다음 항목을 포함합니다.

학생 기본정보

품목내역

규격

수량

단가

예상금액

전체 합계

학교 행정문서 형태로 사용할 수 있도록 다음 스타일을 적용합니다.

제목 병합

Header Bold

중앙 정렬

테두리

열 너비 조정

상품명 자동 줄바꿈

천 단위 금액 표시

9. 최종 제출

학생은 현재 장바구니 내용을 최종 제출할 수 있습니다.

Streamlit
↓
Google Apps Script Web App
↓
Google Sheets

학생이 제출하면 주문 상품 1개당 Google Sheet에 1행씩 저장됩니다.

👩‍🏫 교사용 기능

1. Google 계정 로그인

학생은 로그인 없이 앱을 사용할 수 있습니다.

교사용 주문관리 페이지는 Google 로그인 후 접근할 수 있습니다.

인증 흐름:

Google 로그인
↓
OIDC 인증
↓
로그인 이메일 확인
↓
교사 allowlist 확인
↓
교사용 페이지 접근

교사 이메일은 코드에 직접 작성하지 않고 Streamlit Secrets에서 관리합니다.

2. 교사용 페이지 접근 제한

다음 사용자는 교사용 주문관리 메뉴를 볼 수 없습니다.

비로그인 사용자

허용 목록에 등록되지 않은 Google 계정

허용된 교사 계정만 다음 메뉴를 사용할 수 있습니다.

🛒 Eduino 구매
👩‍🏫 교사용 주문관리

교사용 페이지는 메뉴 노출 여부뿐만 아니라 페이지 내부에서도 다시 권한을 검사합니다.

3. 학생 제출 현황

학생별 최신 제출 상태를 확인할 수 있습니다.

표시 항목:

학년

반

번호

학생명

제출일시

품목수

총수량

총액

정렬 기준:

1순위: 학년
2순위: 반
3순위: 번호

4. 최신 제출 우선 처리

Google Sheets에는 학생이 제출할 때마다 기록이 계속 누적됩니다.

예:

1학년 1반 1번
22:55 제출
→ 이전 주문

1학년 1반 1번
23:08 제출
→ 최신 주문

교사용 주문관리에서는 같은 학생이 여러 번 제출한 경우 가장 최근 제출만 현재 주문으로 인정합니다.

중요하게, 최신 행 하나만 선택하는 것이 아니라:

submission_id
+
가장 최근 submitted_at

이 동일한 모든 상품 행을 하나의 제출 묶음으로 처리합니다.

5. 학생별 주문 상세

학생을 선택하면 해당 학생의 최신 주문 상품 전체를 확인할 수 있습니다.

표시 항목:

상품코드

상품명

옵션

단가

수량

금액

학생별 총 구매 예상금액도 함께 표시됩니다.

6. 전체 주문 통합

전체 학생의 최신 제출 데이터를 기준으로 동일 상품을 자동 집계합니다.

집계 기준:

상품코드 + 옵션

예:

E-14 / 빨강색
E-14 / 파랑색

은 서로 다른 주문 품목으로 처리합니다.

교사용 화면에서는 다음 항목을 확인할 수 있습니다.

제출 학생 수

주문 품목 수

총 주문 수량

전체 예상금액

전체 주문 통합 테이블:

상품코드
상품명
옵션
예상단가
총수량
예상금액

7. 교사용 전체 주문 Excel 다운로드

교사는 최신 제출 기준 전체 주문 데이터를 Excel 파일로 다운로드할 수 있습니다.

파일 예:

Eduino_전체주문내역_2026-08-14.xlsx

Excel에는 다음 시트가 포함됩니다.

전체주문

순번
상품코드
상품명
옵션
총수량
단위
예상단가
예상금액

학생별제출

학년
반
번호
학생명
제출일시
상품코드
상품명
옵션
수량
단가
금액

학생별제출 시트의 정렬 우선순위:

1순위: 학년
2순위: 반
3순위: 번호

🗂 Google Sheets 데이터 구조

Google Drive:

Drive
└─ Streamlit
   └─ Eduino 학생제출

Google Sheet 탭:

학생제출

컬럼:

제출ID
제출일시
학년
반
번호
학생명
상품코드
상품명
옵션
단가
수량
금액
총액

예:

1-3-15
2026-08-14 22:20:00
1학년
3반
15
홍길동
E-14
아두이노 5파이 LED
빨강색
110
3
330
11220

한 학생이 여러 상품을 제출하면 동일한 제출ID와 제출일시로 여러 행이 저장됩니다.

🔗 Google Apps Script 연동

Streamlit에서 Google Sheets에 직접 접근하지 않습니다.

다음 구조를 사용합니다.

Streamlit
↓
HTTP requests
↓
Google Apps Script Web App
↓
Google Sheets

Apps Script 주요 기능:

doPost(e)
→ 학생 주문 제출

doGet(e)
→ 교사용 데이터 조회

getSubmissions()
→ 학생 제출 원본 조회

getSummary()
→ 상품별 집계

학생 주문 저장과 교사용 조회 API를 하나의 Apps Script Web App에서 처리합니다.

🔐 Google 로그인

교사용 로그인에는 Streamlit 내장 OIDC 기능을 사용합니다.

사용 기능:

st.login()
st.user
st.logout()

Google OAuth Client는 Google Cloud Console에서 Web Application 형태로 생성합니다.

Redirect URI 예:

https://eduino-buy.streamlit.app/oauth2callback

🔒 Streamlit Secrets

민감정보는 GitHub에 저장하지 않습니다.

Streamlit Community Cloud의 Secrets 기능을 사용합니다.

예:

[google_sheet]
web_app_url = "YOUR_GOOGLE_APPS_SCRIPT_WEB_APP_URL"

[auth]
redirect_uri = "https://YOUR_APP.streamlit.app/oauth2callback"
cookie_secret = "YOUR_RANDOM_COOKIE_SECRET"
client_id = "YOUR_GOOGLE_CLIENT_ID"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

teacher_emails = [
    "YOUR_TEACHER_EMAIL"
]

다음 정보는 GitHub에 절대 커밋하지 않습니다.

Google OAuth Client Secret

cookie_secret

Apps Script Web App URL

교사 이메일 목록

.streamlit/secrets.toml

🛠 기술 스택

Frontend / Application

Python 3.11+

Streamlit

Pandas

Document Export

OpenPyXL

Python csv

Backend / Storage

Google Apps Script

Google Sheets

Authentication

Google OAuth 2.0 / OpenID Connect

Streamlit OIDC

st.login()

st.user

st.logout()

HTTP Communication

Requests

Deployment

Streamlit Community Cloud

GitHub

📂 프로젝트 구조

eduino-buy/
│
├── streamlit_app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── pages/
│   └── 1_교사용_주문관리.py
│
├── views/
│   ├── __init__.py
│   └── student_page.py
│
├── data/
│   └── products.csv
│
├── services/
│   ├── __init__.py
│   ├── auth_service.py
│   ├── google_sheet_service.py
│   └── excel_service.py
│
└── utils/
    ├── __init__.py
    ├── calculator.py
    └── export.py

📁 주요 파일 설명

streamlit_app.py

애플리케이션의 핵심 Entry Point입니다.

주요 역할:

Streamlit page configuration

Session State 관리

상품 데이터 로딩

상품 UI

장바구니

주문 요약

CSV / Excel 다운로드

Google Sheets 최종 제출

인증 Sidebar

st.Page

st.navigation

views/student_page.py

학생용 구매 페이지를 Streamlit navigation에 연결합니다.

학생은 로그인 없이 해당 페이지를 사용할 수 있습니다.

pages/1_교사용_주문관리.py

교사용 관리 페이지입니다.

주요 기능:

교사 권한 검사

학생 제출 데이터 조회

최신 제출 판별

학년 / 반 / 학생명 필터

학생 제출 현황

학생별 상세 주문

전체 주문 통합

교사용 Excel 다운로드

services/auth_service.py

Google 로그인 및 교사 권한 판별을 담당합니다.

주요 기능:

교사 이메일 allowlist
로그인 상태 확인
로그인 이메일 확인
교사 권한 확인
인증 Sidebar
로그아웃

services/google_sheet_service.py

Streamlit과 Apps Script Web App 간 HTTP 통신을 담당합니다.

주요 기능:

submit_order_to_sheet()
fetch_submissions()
fetch_order_summary()

services/excel_service.py

학생용 및 교사용 Excel 파일 생성을 담당합니다.

주요 기능:

학생별 구매 명세서

전체 주문 통합 Excel

학생별 제출 시트

금액 Formatting

행정문서 스타일

utils/calculator.py

금액 표시와 계산 보조 기능을 담당합니다.

예:

format_currency()

utils/export.py

내보내기 관련 공통 기능을 관리하기 위한 모듈입니다.

data/products.csv

Eduino 상품 정보를 저장합니다.

📊 products.csv 구조

현재 CSV 필드:

필드

설명

category

상위 상품 카테고리

subcategories

세부 카테고리

code

Eduino 상품 코드

name

상품명

price

기본 판매가격

url

Eduino 상품 URL

option_name

옵션 이름

options

선택 가능한 옵션

option_prices

옵션별 추가금액

예:

category,subcategories,code,name,price,url,option_name,options,option_prices
전자부품,IC/기본소자,E-14,아두이노 5파이(5mm) LED,110,https://eduino.kr/...,색상,빨강색|노랑색|파랑색|초록색|백색,
센서,모터/제어,D-75,아두이노 N20 6V 소형 기어드 DC모터,4400,https://eduino.kr/...,기어비,50RPM|100RPM|300RPM,50RPM:0|100RPM:1100|300RPM:2200

⚙️ 옵션 데이터 규칙

options

옵션은 | 문자로 구분합니다.

빨강색|노랑색|파랑색

option_prices

형식:

옵션:추가금액|옵션:추가금액

예:

50RPM:0|100RPM:1100|300RPM:2200

🚀 로컬 설치 및 실행

1. 저장소 Clone

git clone YOUR_REPOSITORY_URL
cd eduino-buy

2. 의존성 설치

pip install -r requirements.txt

3. Streamlit Secrets 설정

로컬 개발 시:

.streamlit/secrets.toml

파일을 생성합니다.

예:

[google_sheet]
web_app_url = "YOUR_GOOGLE_APPS_SCRIPT_WEB_APP_URL"

[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "YOUR_RANDOM_COOKIE_SECRET"
client_id = "YOUR_GOOGLE_CLIENT_ID"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

teacher_emails = [
    "YOUR_TEACHER_EMAIL"
]

로컬 인증을 사용할 경우 Google OAuth Client에도 동일한 Redirect URI 등록이 필요합니다.

4. 애플리케이션 실행

streamlit run streamlit_app.py

기본 주소:

http://localhost:8501

☁️ Streamlit Community Cloud 배포

GitHub Repository를 Streamlit Community Cloud와 연결합니다.

Main file:

streamlit_app.py

배포 후 앱 URL 예:

https://eduino-buy.streamlit.app

Google OAuth Authorized Redirect URI:

https://eduino-buy.streamlit.app/oauth2callback

Streamlit Community Cloud Secrets에는 실제 운영용 Secret 값을 등록해야 합니다.

🔄 상품 데이터 캐시

상품 데이터는 @st.cache_data를 사용합니다.

CSV 파일 수정 시 파일의 mtime 값을 캐시 키에 포함하여 변경사항이 자동으로 반영되도록 구현되어 있습니다.

따라서 단순 브라우저 캐시가 아니라 실제 products.csv 변경 여부를 기준으로 Streamlit 데이터 캐시가 갱신됩니다.

✅ 주요 검증 항목

현재 다음 기능을 테스트했습니다.

학생 기능

✅ 학생 기본정보 입력

✅ 상품 카테고리 표시

✅ 상품 URL 연결

✅ 옵션 선택

✅ 옵션별 추가금액

✅ 수량 선택

✅ 상품 담기

✅ 동일 상품 수량 누적

✅ 옵션별 장바구니 분리

✅ 장바구니 수량 직접 수정

✅ 개별 상품 삭제

✅ 장바구니 전체 삭제

✅ 주문 요약

✅ 총 구매 금액 계산

✅ CSV 다운로드

✅ Excel 다운로드

✅ Google Sheets 최종 제출

Google Sheets

✅ Apps Script POST 요청

✅ 학생 제출 저장

✅ 상품 1개당 1행 저장

✅ 제출일시 기록

✅ 주문 총액 저장

✅ Apps Script GET 조회

교사용 기능

✅ Google 로그인

✅ 교사 이메일 allowlist

✅ 교사용 메뉴 동적 표시

✅ URL 직접 접근 제한

✅ 학생 제출 현황

✅ 최신 제출 우선 처리

✅ 학생별 주문 상세

✅ 전체 주문 통합

✅ 상품 + 옵션별 집계

✅ 교사용 전체 주문 Excel 다운로드

✅ 로그아웃

🔐 보안 원칙

이 프로젝트에서는 다음 원칙을 사용합니다.

학생은 Google 로그인 없이 구매 및 제출 가능

교사용 주문관리만 Google 로그인 필요

교사 이메일은 allowlist 방식으로 관리

OAuth Secret은 Streamlit Secrets에 저장

.streamlit/secrets.toml은 GitHub에 업로드하지 않음

Google Sheets는 Streamlit에서 직접 접근하지 않고 Apps Script를 통해 접근

⚠️ 현재 보안 구조 참고

현재 Apps Script Web App은 학생 제출과 교사용 조회 API를 제공합니다.

교사용 Streamlit 페이지는 인증된 교사만 조회 API를 호출하도록 제한되어 있습니다.

다만 Apps Script Web App URL 자체에 대한 추가적인 서버 간 인증은 현재 구현되어 있지 않습니다.

실제 대규모 서비스 또는 민감정보를 다루는 환경에서는 API 인증 강화가 추가로 필요할 수 있습니다.

🎯 향후 개선 계획

교사용 제출 이력 조회

학생별 이전 제출 비교

제출 취소 / 수정 정책

교사용 상품 관리 기능

상품 가격 일괄 업데이트

주문 마감 기능

학급별 제출률 표시

미제출 학생 확인

프로젝트별 주문 구분

학년도 / 학기 구분

모바일 UI 추가 개선

Apps Script 조회 API 인증 강화

💡 사용 팁

상품 추가 또는 수정

data/products.csv를 수정합니다.

옵션 추가

options 컬럼:

옵션1|옵션2|옵션3

옵션별 가격 추가

option_prices 컬럼:

옵션1:0|옵션2:1000|옵션3:2000

학생 재제출

학생이 같은 학년 / 반 / 번호로 다시 제출하더라도 Google Sheets에는 이전 제출이 삭제되지 않습니다.

교사용 화면에서는 자동으로 최신 제출만 현재 주문으로 처리합니다.

Apps Script 수정

Apps Script 코드를 수정한 경우 기존 Web App 배포를 새 버전으로 업데이트해야 합니다.

Apps Script
→ 배포
→ 배포 관리
→ 기존 웹 앱 편집
→ 새 버전
→ 배포

기존 /exec URL을 유지하면 Streamlit Secrets를 다시 변경할 필요가 없습니다.

📞 문의 및 피드백

본 애플리케이션은 학교 수업에서 아두이노 프로젝트 부품 구매 및 주문 관리를 지원하기 위해 개발되었습니다.

개선 사항이나 버그가 발견되면 프로젝트 담당자에게 문의해주세요.