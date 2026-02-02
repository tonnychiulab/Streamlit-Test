import ssl_checker
import json

hostname = "google.com"
print(f"Checking {hostname}...")

# Check SSL
cert = ssl_checker.get_certificate_details(hostname)
print("Certificate Status:", cert.get("status"))
if cert.get("status") == "valid":
    print("Issuer:", cert.get("issuer"))
    print("Days Left:", cert.get("days_left"))

# Check Headers
headers = ssl_checker.check_security_headers(hostname)
print("HSTS:", headers.get("hsts"))
