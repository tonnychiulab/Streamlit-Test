import streamlit as st
import ssl_checker
import time

st.set_page_config(
    page_title="HTTPS Site Inspector",
    page_icon="🔒",
    layout="centered"
)

# Custom CSS for better aesthetics
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .status-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .valid {
        background-color: #d1fae5;
        color: #065f46;
        border: 1px solid #34d399;
    }
    .invalid {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #f87171;
    }
    .warning {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fbbf24;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🔒 HTTPS Site Inspector")
st.markdown("Check the SSL/TLS security status of any website instantly.")

url = st.text_input("Enter Website URL", placeholder="example.com")

if st.button("Check Security", type="primary"):
    if not url:
        st.warning("Please enter a URL first.")
    else:
        with st.spinner(f"Inspecting {url}..."):
            # Simulate a brief delay for UX (optional)
            time.sleep(0.5)
            
            fullname = ssl_checker.get_hostname_from_url(url)
            cert_info = ssl_checker.get_certificate_details(fullname)
            headers_info = ssl_checker.check_security_headers(fullname)
            
        # Display Results
        st.subheader("Inspection Results")
        
        # 1. Main Status
        status = cert_info.get("status")
        if status == "valid":
            st.markdown(f"""
                <div class="status-card valid">
                    <h3>✅ Secure Connection</h3>
                    <p>The certificate for <strong>{fullname}</strong> is valid and trusted.</p>
                </div>
            """, unsafe_allow_html=True)
            
            # 2. Key Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Days Remaining", f"{cert_info['days_left']} days")
            with col2:
                org = cert_info['issuer'].get('organizationName', 'Unknown')
                st.metric("Issuer", org) # truncated if too long
            with col3:
                st.metric("TLS Version", f"TLS {cert_info['version']}")
                
            # 3. Security Headers
            st.markdown("### Security Headers")
            hsts = headers_info.get('hsts')
            if hsts:
                 st.success(f"✅ HSTS Enabled: `{hsts}`")
            else:
                 st.warning("⚠️ HSTS Not Detected (Recommended for production)")
                 
            # 4. Detailed Certificate Info
            with st.expander("Checking Certificate Details"):
                st.json(cert_info)
                
        elif status == "invalid":
            st.markdown(f"""
                <div class="status-card invalid">
                    <h3>❌ Insecure Connection</h3>
                    <p>{cert_info.get('error')}</p>
                </div>
            """, unsafe_allow_html=True)
        else:
             st.markdown(f"""
                <div class="status-card warning">
                    <h3>⚠️ Connection Error</h3>
                    <p>{cert_info.get('error')}</p>
                </div>
            """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("Built with Streamlit & Python 🐍")
