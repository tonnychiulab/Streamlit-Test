import socket
import ipaddress
import ssl
import datetime
from urllib.parse import urlparse
import requests

def get_hostname_from_url(url):
    """Extracts hostname from a given URL."""
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    return parsed.netloc

def get_certificate_details(hostname):
    """
    Connects to the hostname via SSL and retrieves certificate details.
    Returns a dictionary with status and data.
    """
    context = ssl.create_default_context()
    conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=hostname)
    
    # Timeout set to 5 seconds
    conn.settimeout(5.0)

    try:
        conn.connect((hostname, 443))
        cert = conn.getpeercert()
        
        # Extract relevant details
        subject = dict(x[0] for x in cert['subject'])
        issuer = dict(x[0] for x in cert['issuer'])
        not_before = cert['notBefore']
        not_after = cert['notAfter']
        version = cert['version']
        serial_number = cert['serialNumber']
        
        # Convert date strings to datetime objects
        # Format usually: 'May 26 00:00:00 2026 GMT'
        date_fmt = r'%b %d %H:%M:%S %Y %Z'
        valid_from_dt = datetime.datetime.strptime(not_before, date_fmt)
        valid_to_dt = datetime.datetime.strptime(not_after, date_fmt)
        
        days_left = (valid_to_dt - datetime.datetime.utcnow()).days
        
        conn.close()
        
        return {
            "status": "valid",
            "hostname": hostname,
            "subject": subject,
            "issuer": issuer,
            "valid_from": valid_from_dt.strftime('%Y-%m-%d'),
            "valid_to": valid_to_dt.strftime('%Y-%m-%d'),
            "days_left": days_left,
            "version": version,
            "serial_number": serial_number,
            "raw": cert
        }

    except ssl.SSLCertVerificationError as e:
        return {
            "status": "invalid",
            "error": f"SSL Verification Error: {e.verify_message}",
            "hostname": hostname
        }
    except socket.timeout:
        return {
            "status": "error",
            "error": "Connection timed out",
            "hostname": hostname
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "hostname": hostname
        }

def check_security_headers(url):
    """
    Checks for security headers like HSTS.
    """
    if not url.startswith("http"):
        url = "https://" + url
        
    try:
        response = requests.get(url, timeout=5)
        headers = response.headers
        
        hsts = headers.get('Strict-Transport-Security', None)
        x_frame = headers.get('X-Frame-Options', None)
        x_content_type = headers.get('X-Content-Type-Options', None)
        
        return {
            "hsts": hsts,
            "x_frame_options": x_frame,
            "x_content_type_options": x_content_type,
            "status_code": response.status_code
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def is_valid_ip(ip_address: str) -> bool:
    """
    驗證輸入的字串是否為合法的 IP 位址 (IPv4 或 IPv6)

    * 為什麼需要這個函式：確認輸入的目標是否為直接的 IP 位址，這對於某些不支援網域名稱解析的情境很有用。
    * 技巧：使用標準函式庫 `ipaddress` 來處理，避免自己寫複雜且容易出錯的 Regex。

    Args:
        ip_address (str): 要驗證的 IP 位址字串

    Returns:
        bool: 如果是合法的 IP 位址則回傳 True，否則回傳 False
    """
    try:
        # 使用 Python 內建的 ipaddress 工廠函式
        # 它會自動判斷是 IPv4 或 IPv6，如果格式錯誤會拋出 ValueError
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        # TODO: 如果未來需要區分 IPv4 或 IPv6，可以在這裡做更細緻的錯誤處理或回傳不同代碼
        return False

