import socket
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
