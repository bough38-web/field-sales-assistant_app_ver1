import streamlit as st

def show_terms_of_service():
    st.markdown("""
    ### [서비스 이용약관]
    
    **제 1조 (목적)**
    본 약관은 '영업기회 관리 시스템'이 제공하는 제반 서비스의 이용과 관련하여 회사와 회원과의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.
    
    **제 2조 (서비스 이용)**
    1. 회원은 본 약관에 동의함으로서 서비스를 이용할 수 있습니다.
    2. 프리미엄 서비스(Pro 티어)는 유료 결제 후 이용 가능합니다.
    
    **제 3조 (데이터의 사용)**
    본 서비스에서 제공하는 공공데이터 및 분석 결과는 참고용이며, 회사는 실제 결과에 대한 법적 책임을 지지 않습니다.
    """)

def show_privacy_policy():
    st.markdown("""
    ### [개인정보 처리방침]
    
    **1. 수집하는 개인정보 항목**
    - 이메일, 성명, 아이디, 결제 정보
    
    **2. 수집 목적**
    - 서비스 제공, 본인 확인, 결제 처리 및 고객 지원
    
    **3. 보유 및 이용기간**
    - 회원 탈퇴 시 혹은 법정 보유 기간 종료 시까지
    """)

def consent_form():
    st.info("💡 회원가입을 위해 아래 약관에 동의해 주세요.")
    agree_tos = st.checkbox("서비스 이용약관에 동의합니다. (필수)")
    agree_privacy = st.checkbox("개인정보 처리방침에 동의합니다. (필수)")
    
    with st.expander("약관 내용 보기"):
        show_terms_of_service()
        st.divider()
        show_privacy_policy()
        
    return agree_tos and agree_privacy
