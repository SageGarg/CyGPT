from __future__ import annotations
import streamlit as st
from src.auth import login, register, validate_password, validate_username


def show() -> None:
    st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">🌪️</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">CyGPT</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Iowa State University Academic Assistant</div>', unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        if st.session_state.get("_login_err"):
            st.markdown(
                f'<div class="auth-msg-error">{st.session_state["_login_err"]}</div>',
                unsafe_allow_html=True,
            )
        lu = st.text_input("Username", key="_lu", placeholder="your username")
        lp = st.text_input("Password", key="_lp", placeholder="your password", type="password")

        if st.button("Sign In", type="primary", width="stretch", key="_login_btn"):
            result = login(lu.strip(), lp)
            if result:
                st.session_state.update({
                    "logged_in": True,
                    "username": result[0],
                    "display_name": result[1],
                    "_login_err": None,
                })
                st.rerun()
            else:
                st.session_state["_login_err"] = "Incorrect username or password."
                st.rerun()

    with tab_signup:
        if st.session_state.get("_signup_err"):
            st.markdown(
                f'<div class="auth-msg-error">{st.session_state["_signup_err"]}</div>',
                unsafe_allow_html=True,
            )
        if st.session_state.get("_signup_ok"):
            st.markdown('<div class="auth-msg-ok">Account created! Sign in above.</div>', unsafe_allow_html=True)

        su  = st.text_input("Username", key="_su", placeholder="letters, numbers, underscores")
        sn  = st.text_input("Display name", key="_sn", placeholder="e.g. Jane Doe  (optional)")
        sp  = st.text_input("Password", key="_sp", placeholder="min 8 chars, one number", type="password")
        sp2 = st.text_input("Confirm password", key="_sp2", placeholder="repeat password", type="password")
        st.markdown('<div class="auth-hint">Requirements: at least 8 characters · at least one number</div>', unsafe_allow_html=True)

        if st.button("Create Account", type="primary", width="stretch", key="_signup_btn"):
            err = validate_username(su.strip()) or validate_password(sp)
            if err:
                st.session_state.update({"_signup_err": err, "_signup_ok": False})
            elif sp != sp2:
                st.session_state.update({"_signup_err": "Passwords do not match.", "_signup_ok": False})
            else:
                err = register(su.strip(), sn.strip(), sp)
                st.session_state.update({"_signup_err": err, "_signup_ok": not err})
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()
