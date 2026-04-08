import streamlit as st
import streamlit_authenticator as stauth
import json
import os
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token

# User data storage
# In a real app, this should be a DB like Supabase or PostgreSQL.
USER_DB_DIR = Path(os.path.expanduser("~")) / ".sales_assistant_data"
USER_DB_FILE = USER_DB_DIR / "users_auth.json"

def init_user_db():
    USER_DB_DIR.mkdir(parents=True, exist_ok=True)
    if not USER_DB_FILE.exists():
        # Default admin and tiers
        default_data = {
            "usernames": {}
        }
        with open(USER_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4)

def load_user_db():
    init_user_db()
    with open(USER_DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_user_db(data):
    with open(USER_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_auth_config():
    db = load_user_db()
    config = {
        "credentials": db,
        "cookie": {
            "expiry_days": 30,
            "key": "sales_assistant_signature",
            "name": "sales_assistant_cookie"
        },
        "preauthorized": {
            "emails": []
        }
    }
    return config

def register_user(username, email, name, password, tier="basic"):
    db = load_user_db()
    if username in db["usernames"]:
        return False, "이미 존재하는 사용자 아이디입니다."
    
    # Simple hashing (Authenticator does this usually, but we store it)
    hashed_password = stauth.Hasher([password]).generate()[0]
    
    db["usernames"][username] = {
        "email": email,
        "name": name,
        "password": hashed_password,
        "tier": tier,
        "created_at": str(st.session_state.get('now_kst', '2026-04-08'))
    }
    save_user_db(db)
    return True, "회원가입이 완료되었습니다."

def update_user_tier(username, new_tier):
    db = load_user_db()
    if username in db["usernames"]:
        db["usernames"][username]["tier"] = new_tier
        save_user_db(db)
        return True
    return False

def get_user_tier(username):
    db = load_user_db()
    return db["usernames"].get(username, {}).get("tier", "basic")

def is_pro_user():
    """Helper to check if current logged in user is Pro"""
    if 'authentication_status' in st.session_state and st.session_state['authentication_status']:
        username = st.session_state['username']
        return get_user_tier(username) == "pro"
    return False

def show_login_registration():
    config = get_auth_config()
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )

    # --- [EXPERT UI] Premium Landing Hero Section ---
    st.markdown("""
        <div style="text-align: center; padding: 1.5rem 0 2rem 0;">
            <h1 style="font-size: 2.8rem; font-weight: 800; background: linear-gradient(135deg, #1a237e 0%, #228be6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;">
                💼 영업기회 Pro
            </h1>
            <p style="font-size: 1.15rem; color: #444; font-weight: 600; margin-bottom: 0.2rem;">
                전국 <span style="color: #228be6; font-weight: 800;">1,300+명</span>의 영업 전문가가 선택한 AI 분석 툴
            </p>
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: 10px;">
                <span class="pro-badge" style="font-size: 0.8rem; padding: 4px 12px;">🛡️ SSL 보안</span>
                <span class="pro-badge" style="font-size: 0.8rem; padding: 4px 12px; background: #e7f5ff; color: #228be6;">⚡ 실시간 분석</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Wrap the login form in a premium card container
    with st.container():
        st.markdown('<div class="dashboard-card" style="max-width: 500px; margin: 0 auto; padding: 30px !important;">', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔒 로그인", "📝 회원가입"])
        
        with tab1:
            name, authentication_status, username = authenticator.login('main')
            if authentication_status:
                st.session_state['user_role'] = 'admin' if username == 'admin' else 'user'
                st.rerun()
            elif authentication_status == False:
                st.error('아이디/비밀번호가 일치하지 않습니다.')
            elif authentication_status == None:
                st.info('본인 확인을 위해 로그인해 주세요.')

        with tab2:
            st.markdown("""
                <div style="background-color: #f1f3f5; padding: 15px; border-radius: 10px; border-left: 5px solid #228be6; margin-bottom: 20px;">
                    <h4 style="margin-top: 0; font-size: 1rem; color: #1a237e;">📝 회원가입 가이드 (Registration Guide)</h4>
                    <ul style="font-size: 0.85rem; color: #444; padding-left: 1.2rem; margin-bottom: 0;">
                        <li><b>사용자명 (Username):</b> <u>영문 및 숫자</u>만 가능합니다. (English/Numbers only)</li>
                        <li><b>성함 (Full Name):</b> 한글 또는 영문 실명을 입력하세요. (Real name in KR/EN)</li>
                        <li><b>이메일 (Email):</b> 형식에 맞는 정확한 주소를 입력하세요.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            try:
                # v0.3.x style: positional title removed, use help/captions if supported or just guide above
                if authenticator.register_user(preauthorization=False):
                    save_user_db(config['credentials'])
                    st.success('가입을 축하드립니다! 이제 로그인 탭에서 접속하세요.')
            except Exception as e:
                if "Username" in str(e):
                    st.error("오류: 사용자명(Username)에 한글이 포함되어 있습니다. 영문/숫자로 다시 입력해 주세요.")
                else:
                    st.error(f"오류: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --- [EXPERT UI] Trust & Social Proof Footer ---
    st.markdown("""
        <div style="text-align: center; margin-top: 2rem; border-top: 1px solid #eee; padding-top: 1.5rem;">
            <p style="font-size: 0.85rem; color: #888; margin-bottom: 1rem;">
                "이 앱을 쓰고 나서 가망 고객 발굴 시간이 50% 단축되었습니다" <br>
                <b>- 서부본부 홍길동 메니저 -</b>
            </p>
            <div style="opacity: 0.6; grayscale: 1;">
                <img src="https://cdn-icons-png.flaticon.com/512/1087/1087815.png" width="24" style="margin-right: 10px;">
                <span style="font-size: 0.75rem; vertical-align: middle;">엔터프라이즈급 기보안 및 암호화 솔루션 탑재</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- Google OAuth Implementation ---

GOOGLE_CLIENT_ID = st.secrets.get("google", {}).get("client_id", "")
GOOGLE_CLIENT_SECRET = st.secrets.get("google", {}).get("client_secret", "")
# Re-direct URI must match what you set in Google Console
REDIRECT_URI = st.secrets.get("google", {}).get("redirect_uri", "http://localhost:8501")

def get_google_login_url():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None
    
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": "field-sales-assistant",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI]
        }
    }
    
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config,
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
    )
    flow.redirect_uri = REDIRECT_URI
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    st.session_state['oauth_state'] = state
    return authorization_url

def handle_google_callback():
    """Handles the redirect back from Google with 'code' in URL"""
    if "code" in st.query_params:
        code = st.query_params["code"]
        
        client_config = {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "project_id": "field-sales-assistant",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI]
            }
        }
        
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
        )
        flow.redirect_uri = REDIRECT_URI
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Verify ID Token
            info = id_token.verify_oauth2_token(
                credentials.id_token, Request(), GOOGLE_CLIENT_ID
            )
            
            email = info.get('email')
            name = info.get('name')
            google_id = info.get('sub')
            
            if email:
                # 1. Login or Auto-Register
                db = load_user_db()
                username = email.split('@')[0] # Simple username from email
                
                if username not in db["usernames"]:
                    # Auto Register
                    register_user(username, email, name, google_id) # Use google_id as placeholder PW
                
                # 2. Set Session State
                st.session_state['authentication_status'] = True
                st.session_state['username'] = username
                st.session_state['name'] = name
                st.session_state['logout'] = False
                
                st.query_params.clear()
                st.rerun()
                
        except Exception as e:
            st.error(f"Google 로그인 처리 중 오류 발생: {e}")
