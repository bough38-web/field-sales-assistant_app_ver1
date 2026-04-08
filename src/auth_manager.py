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

    tab1, tab2 = st.tabs(["🔒 로그인", "📝 회원가입"])
    
    with tab1:
        name, authentication_status, username = authenticator.login('main')
        if authentication_status:
            st.session_state['user_role'] = 'admin' if username == 'admin' else 'user'
            st.rerun()
        elif authentication_status == False:
            st.error('아이디/비밀번호가 일치하지 않습니다.')
        elif authentication_status == None:
            st.warning('아이디와 비밀번호를 입력해주세요.')

    with tab2:
        try:
            if authenticator.register_user('회원가입', pre_authorization=False):
                # Update our local DB with the new user from the authenticator's update
                save_user_db(config['credentials'])
                st.success('가입을 축하드립니다! 이제 로그인 탭에서 접속하세요.')
        except Exception as e:
            st.error(f"오류: {e}")

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
