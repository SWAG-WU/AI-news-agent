import base64
import hashlib
import hmac

from src.sender import FeishuSender


def test_feishu_signature_uses_lark_webhook_algorithm():
    sender = FeishuSender.__new__(FeishuSender)
    sender.secret = "test-secret"

    timestamp = "1700000000"
    expected = base64.b64encode(
        hmac.new(
            f"{timestamp}\n{sender.secret}".encode("utf-8"),
            b"",
            digestmod=hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    assert sender._generate_sign(timestamp) == expected
