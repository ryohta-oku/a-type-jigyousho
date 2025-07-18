import hashlib
import hmac
import time
import requests
import urllib.parse
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook

# 認証情報
access_key = "AKPAEEKWJP1752396396"
secret_key = "zfDbpUflco4lP6PNdmxvCHbHGqSenn3fqQUrUyAF"
associate_tag = "choshucrypter-22"
region = "us-west-2"
host = "webservices.amazon.co.jp"
uri = "/paapi5/searchitems"

# JANコード一覧の読み込み
df = pd.read_excel("【AI用】総合カタログ2024-2025掲載継続アイテムリスト.xlsx")
df['JANコード'] = df['JANコード'].astype(str).str.replace('.0', '', regex=False)
jan_list = df['JANコード'].dropna().unique()[:10]  # 最初の10件だけ

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def get_signature_key(key, date_stamp, region_name, service_name):
    k_date = sign(('AWS4' + key).encode('utf-8'), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, 'aws4_request')
    return k_signing

def make_signed_request(payload):
    method = 'POST'
    service = 'ProductAdvertisingAPI'
    content_type = 'application/json; charset=utf-8'

    t = datetime.utcnow()
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')

    canonical_uri = uri
    canonical_querystring = ''

    canonical_headers = f'content-type:{content_type}\nhost:{host}\nx-amz-date:{amz_date}\n'
    signed_headers = 'content-type;host;x-amz-date'
    payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

    canonical_request = f'{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'

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
        'Content-Type': content_type,
        'X-Amz-Date': amz_date,
        'Authorization': authorization_header
    }

    url = f'https://{host}{uri}'
    response = requests.post(url, headers=headers, data=payload)
    return response

# 取得＆Excel追記
for i, jan in enumerate(jan_list):
    print(f"[{i+1}] Searching JAN: {jan}")
    payload = f'''
    {{
      "Keywords": "{jan}",
      "SearchIndex": "All",
      "PartnerTag": "{associate_tag}",
      "PartnerType": "Associates",
      "Marketplace": "www.amazon.co.jp",
      "Resources": [
        "ItemInfo.Title",
        "Offers.Listings.Price",
        "Images.Primary.Small",
        "ItemInfo.ByLineInfo"
      ]
    }}
    '''

    res = make_signed_request(payload)
    if res.status_code != 200:
        print("Error:", res.status_code, res.text)
        continue

    data = res.json()
    items = data.get("SearchResult", {}).get("Items", [])
    if not items:
        print("No item found.")
        continue

    asin = items[0]["ASIN"]
    title = items[0]["ItemInfo"]["Title"]["DisplayValue"]
    url = f"https://www.amazon.co.jp/dp/{asin}"
    price = items[0].get("Offers", {}).get("Listings", [{}])[0].get("Price", {}).get("DisplayAmount", "N/A")

    # 該当行にASINとURLを追記
    idx = df[df['JANコード'] == jan].index[0]
    df.at[idx, 'ASIN'] = asin
    df.at[idx, 'Amazon URL'] = url
    df.at[idx, '商品名'] = title
    df.at[idx, '価格'] = price

# 保存
df.to_excel("ASIN付き商品一覧_取得済.xlsx", index=False)
print("✅ 完了！→ ASIN付き商品一覧_取得済.xlsx に保存しました")