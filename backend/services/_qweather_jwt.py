"""
和风天气 JWT 认证令牌生成器 — 纯 Python 实现
零外部依赖，仅需 hashlib + 内置 base64 + 内置 asn1 解析

用法:
    token = qweather_jwt(project_id, credential_id, private_key_pem)
    # 返回 JWT 字符串，用于 Authorization: Bearer <token>
"""

import base64
import hashlib
import json
import time
import re


def _b64url(data: bytes) -> str:
    """Base64URL 编码（无填充）"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Base64URL 解码"""
    s += "=" * (4 - len(s) % 4) if len(s) % 4 else ""
    return base64.urlsafe_b64decode(s)


def _parse_pkcs8_ed25519_key(pem_text: str) -> bytes:
    """从 PEM 格式的 Ed25519 私钥中提取 32-byte 原始密钥

    支持两种格式:
      1. PKCS#8 PEM (-----BEGIN PRIVATE KEY-----)
      2. 原始 32-byte hex 字符串
    """
    pem_text = pem_text.strip()

    # 格式 1: 原始 hex (64 字符 = 32 字节)
    if re.match(r"^[0-9a-fA-F]{64}$", pem_text):
        return bytes.fromhex(pem_text)

    # 格式 1b: 原始 hex 带 0x 前缀
    if pem_text.startswith("0x") and re.match(r"^0x[0-9a-fA-F]{64}$", pem_text):
        return bytes.fromhex(pem_text[2:])

    # 格式 2: 已经是原始 base64 (44 字符, 无 PEM 头)
    if not pem_text.startswith("-----"):
        try:
            raw = base64.b64decode(pem_text)
            if len(raw) >= 32:
                return _extract_ed25519_seed(raw)
        except Exception:
            pass

    # 格式 3: PEM → DER → extract key
    b64_body = re.sub(r"-----(BEGIN|END) PRIVATE KEY-----", "", pem_text)
    b64_body = re.sub(r"\s+", "", b64_body)
    der = base64.b64decode(b64_body)
    return _extract_ed25519_seed(der)


def _extract_ed25519_seed(der: bytes) -> bytes:
    """从 PKCS#8 DER 编码中提取 Ed25519 32-byte 种子

    PKCS#8 Ed25519 结构 (RFC 8410):
      SEQUENCE {
        INTEGER 0
        SEQUENCE { OID 1.3.101.112 }
        OCTET STRING {        ← 外层包装
          OCTET STRING {      ← 内层 (tag 04, len 0x20)
            32-byte seed
          }
        }
      }
    """
    # 方法 1: 寻找内层 OCTET STRING 标记 (04 20)
    # 注意要跳过外层的 04 xx (外层通常长 34 = 0x22)
    for i in range(len(der) - 34):
        # 寻找 "04 20" 标记（OCTET STRING, 长度 32）
        if der[i] == 0x04 and der[i + 1] == 0x20:
            # 确保后续有 32 字节
            if i + 2 + 32 <= len(der):
                candidate = der[i + 2 : i + 2 + 32]
                # 验证: 这不是外层的包装（外层前面应该还有 structure）
                # 外层 04 22 位于更早位置
                return candidate

    # 方法 2: 直接取最后 32 字节（在很多 Ed25519 PKCS#8 编码中有效）
    if len(der) >= 32:
        return der[-32:]

    raise ValueError(
        "无法从私钥数据中提取 Ed25519 32-byte 种子。\n"
        "请确认私钥格式正确: PEM (-----BEGIN PRIVATE KEY-----) 或 64 字符 hex。\n"
        "生成方法: openssl genpkey -algorithm ED25519 -out ed25519-private.pem"
    )


def _ed25519_sign(msg: bytes, seed: bytes) -> bytes:
    """Ed25519 签名 — 使用纯 Python 参考实现"""
    from services._ed25519 import signature_unsafe, publickey_unsafe

    if len(seed) != 32:
        raise ValueError(f"Ed25519 seed must be 32 bytes, got {len(seed)}")

    pk = publickey_unsafe(seed)
    return signature_unsafe(msg, seed, pk)


def qweather_jwt(
    project_id: str,
    credential_id: str,
    private_key_pem: str,
    ttl: int = 900,
) -> str:
    """生成和风天气 JWT 认证令牌

    Args:
        project_id:    项目 ID (JWT sub)
        credential_id: 凭据 ID (JWT kid)
        private_key_pem: Ed25519 私钥 PEM 字符串 (或 64 字符 hex)
        ttl:           Token 有效期 (秒, 默认 15 分钟, 最大 24 小时)

    Returns:
        JWT 令牌字符串 (可直接用于 Authorization: Bearer <token>)
    """
    # 提取原始 Ed25519 种子
    seed = _parse_pkcs8_ed25519_key(private_key_pem)

    # 构建 JWT header & payload
    now = int(time.time())
    header = {
        "alg": "EdDSA",
        "kid": credential_id,
    }
    payload = {
        "sub": project_id,
        "iat": now - 30,       # 提前 30 秒防时钟偏差
        "exp": now + min(ttl, 86400),
    }

    # 编码 header & payload
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())

    # 签名
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = _ed25519_sign(signing_input, seed)
    sig_b64 = _b64url(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


# 便捷函数：生成后直接可用于 HTTP 头
def qweather_auth_header(
    project_id: str,
    credential_id: str,
    private_key_pem: str,
) -> str:
    """返回 Authorization 头的值: Bearer <jwt_token>"""
    return f"Bearer {qweather_jwt(project_id, credential_id, private_key_pem)}"
