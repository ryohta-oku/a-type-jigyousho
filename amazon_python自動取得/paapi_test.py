import requests
import datetime
import hashlib
import hmac
import json

# ===== 🔧 あなたのアクセス情報 =====
access_key = "AKIAxxxxxxxxxxxxxxxx"
secret_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
partner_tag = "yourtag-22"  # アソシエイトID

# ===== 📦 テストASIN =====
payload = json.dumps({
    "ItemIds": ["B07X1KT6LD"],
    "Resources": [
        "ItemInfo.Title",
        "Offers.Listings.Price",
        "DetailPageURL"
    ],
    "PartnerTag": partner_tag,
    "PartnerType": "Associates",
    "Marketplace": "www.amazon.co.jp"
})

# ===== 🔐 署名関連 =====
def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def get_signature_key(key, date_stamp, region_name, service_name):
    k_date = sign(('AWS4' + key).encode('utf-8'), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, 'aws4_request')
    return k_signing

# ===== 🌐 エンドポイント情報 =====
host = 'webservices.amazon.com'
region = 'us-east-1'
service = 'ProductAdvertisingAPI'
endpoint = f'https://{host}/paapi5/getitems'

# ===== 🕒 タイムスタンプなど =====
t = datetime.datetime.utcnow()
amz_date = t.strftime('%Y%m%dT%H%M%SZ')
date_stamp = t.strftime('%Y%m%d')

# ===== 📄 canonical request =====
canonical_uri = '/paapi5/getitems'
canonical_querystring = ''
canonical_headers = f'host:{host}\n'
signed_headers = 'host'
payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
canonical_request = f'POST\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'

# ===== 🔏 署名の作成 =====
algorithm = 'AWS4-HMAC-SHA256'
credential_scope = f'{date_stamp}/{region}/{service}/aws4_request'
string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
signing_key = get_signature_key(secret_key, date_stamp, region, service)
signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

authorization_header = (
    f'{algorithm} Credential={access_key}/{credential_scope}, '
    f'SignedHeaders={signed_headers}, Signature={signature}'
)

headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'X-Amz-Date': amz_date,
    'Authorization': authorization_header
}

# ===== 🚀 リクエスト送信 =====
response = requests.post(endpoint, headers=headers, data=payload)

print(f"Status Code: {response.status_code}")
print("Response Body:")
print(response.text)
