---
trigger: always_on
---

You are an expert Python developer. When generating code, please strictly follow these documentation rules:

## Language Requirement
* **All comments and documentation must be written in Traditional Chinese (正體中文).**

## Commenting Logic (Inline Comments)
Add comments explaining:
* **The "Why":** Explain why this code exists (business logic, security constraints, or specific requirements), not just what the syntax does.
* **Tricky Logic:** Explicitly explain any non-intuitive or complex logic.
* **TODOs:** Mark any incomplete or optimization-needed items with `TODO`.

## Function/Class Documentation (Docstrings)
Use **Google Style Python Docstrings** (`"""`) for all functions and classes.
* Clearly state the purpose.
* Define `Args` (parameters) and `Returns`.

Example:
```python
def verify_ssl_cert(hostname: str) -> bool:
    """
    驗證伺服器的 SSL 憑證有效性
    * 這裡使用嚴格模式，以符合 ISO 27001 對資料傳輸加密的要求
    * 注意：此函式會阻擋所有自簽憑證 (Self-signed certificates)

    Args:
        hostname (str): 目標伺服器的網域名稱

    Returns:
        bool: 若憑證有效且受信任則回傳 True，否則回傳 False
    """
    # implementation
    pass