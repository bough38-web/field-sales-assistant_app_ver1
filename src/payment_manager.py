import streamlit as st
import stripe
import os

# Stripe keys - stored in Streamlit Secrets normally
# For local dev, we provide a placeholder
STRIPE_API_KEY = st.secrets.get("stripe", {}).get("api_key", "sk_test_4eC39HqLyjWDarjtT1zdp7dc")
stripe.api_key = STRIPE_API_KEY

def create_checkout_session(plan_name, amount, success_url, cancel_url):
    """
    Creates a Stripe Checkout session for subscription or one-time payment.
    """
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'krw',
                    'product_data': {
                        'name': plan_name,
                    },
                    'unit_amount': amount,
                },
                'quantity': 1,
            }],
            mode='payment', # Use 'subscription' for recurring
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url
    except Exception as e:
        st.error(f"결제 세션 생성 오류: {e}")
        return None

def show_pricing_table():
    st.markdown("## 💎 요금제 선택")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="dashboard-card" style="border-top: 5px solid #9E9E9E;">
            <h3>Standard</h3>
            <p style="font-size: 1.5rem; font-weight: bold;">월 9,900원</p>
            <ul style="text-align: left; list-style: none; padding-left: 0;">
                <li>✅ 기본 영업 기회 조회</li>
                <li>✅ 동적 지도 시각화</li>
                <li>✅ 기본 필터링</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Standard 선택", use_container_width=True):
            st.info("실제 운영 시 결제 페이지로 이동합니다 (Stripe 연결 필요)")

    with col2:
        st.markdown("""
        <div class="dashboard-card" style="border: 2px solid #3F51B5; border-top: 5px solid #3F51B5;">
            <div style="background: #3F51B5; color: white; padding: 2px 10px; border-radius: 10px; font-size: 0.8rem; margin-bottom: 5px; display: inline-block;">Best Value</div>
            <h3>Professional</h3>
            <p style="font-size: 1.5rem; font-weight: bold; color: #3F51B5;">월 29,900원</p>
            <ul style="text-align: left; list-style: none; padding-left: 0;">
                <li>🔥 <b>AI 상세 스코어링 분석</b></li>
                <li>📊 데이터 엑셀/CSV 다운로드</li>
                <li>📱 방문 보고서 무제한 저장</li>
                <li>🚀 고령화/인구 통계 레이어</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Professional 업그레이드", type="primary", use_container_width=True):
            # Example Success URL
            url = create_checkout_session(
                "영업 마스터 (Pro)", 
                29900, 
                "http://localhost:8501/?payment=success", 
                "http://localhost:8501/?payment=cancel"
            )
            if url:
                st.link_button("💳 안전하게 결제하기", url, use_container_width=True)
                st.caption("🔒 시연용 테스트 키로 연동되어 있습니다.")

def check_payment_status():
    """Check query params for payment success"""
    if st.query_params.get("payment") == "success":
        st.balloons()
        st.success("결제가 성공적으로 완료되었습니다! 이제 Pro 기능을 사용할 수 있습니다.")
        # Logic to update user tier in DB
        from src import auth_manager
        if st.session_state.get('username'):
            auth_manager.update_user_tier(st.session_state['username'], 'pro')
        st.query_params.clear()
        st.rerun()
