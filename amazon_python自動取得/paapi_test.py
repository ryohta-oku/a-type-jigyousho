import requests
import datetime
import hashlib
import hmac
import json

# ===== 🔧 あなたのアクセス情報 =====
access_key = "AKPAEEKWJP1752396396"
secret_key = "zfDbpUflco4lP6PNdmxvCHbHGqSenn3fqQUrUyAF"
partner_tag = "choshucrypter-22"

# ===== 📦 テストASIN（日本Amazon用）=====
payload = json.dumps({
    "ItemIds": ["B0BSFQBCBJ"],  # 日本で確実に存在するASIN (Nintendo Switch本体など)
    "Resources": [
        "ItemInfo.Title",
        "Offers.Listings.Price",
        "Images.Primary.Medium",
        "ItemInfo.DetailPageURL"
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

# ===== 🌐 エンドポイント情報（日本用）=====
host = 'webservices.amazon.co.jp'
region = 'us-west-2'  # 日本のPA-APIでもus-west-2を使用
service = 'ProductAdvertisingAPI'
endpoint = f'https://{host}/paapi5/getitems'

# ===== 🕒 タイムスタンプ =====
t = datetime.datetime.now(datetime.UTC)
amz_date = t.strftime('%Y%m%dT%H%M%SZ')
date_stamp = t.strftime('%Y%m%d')

# ===== 📄 canonical request =====
canonical_uri = '/paapi5/getitems'
canonical_querystring = ''
canonical_headers = f'host:{host}\nx-amz-date:{amz_date}\n'
signed_headers = 'host;x-amz-date'
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
    'Authorization': authorization_header,
    'X-Amz-Target': 'com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems'
}

# ===== 🔍 診断機能追加 =====
def diagnose_credentials():
    """認証情報の基本チェック"""
    issues = []
    
    if not access_key or len(access_key) != 20:
        issues.append("❌ Access Keyが無効です（20文字である必要があります）")
    else:
        issues.append("✅ Access Key形式OK")
    
    if not secret_key or len(secret_key) != 40:
        issues.append("❌ Secret Keyが無効です（40文字である必要があります）")
    else:
        issues.append("✅ Secret Key形式OK")
        
    if not partner_tag:
        issues.append("❌ Partner Tagが設定されていません")
    else:
        issues.append("✅ Partner Tag設定済み")
    
    return issues

def test_different_asins():
    """複数のASINでテスト"""
    test_asins = [
        "B0BSFQBCBJ",  # Nintendo Switch (新しめ)
        "B07HCSQ48C",  # Echo Dot 3rd Gen
        "B08N5WRWNW",  # 元のASIN
    ]
    
    for asin in test_asins:
        print(f"\n--- {asin} をテスト中 ---")
        
        test_payload = json.dumps({
            "ItemIds": [asin],
            "Resources": ["ItemInfo.Title"],
            "PartnerTag": partner_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.co.jp"
        })
        
        # 新しい署名を生成
        payload_hash = hashlib.sha256(test_payload.encode('utf-8')).hexdigest()
        canonical_request = f'POST\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
        string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        test_headers = headers.copy()
        test_headers['Authorization'] = f'{algorithm} Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
        
        try:
            response = requests.post(endpoint, headers=test_headers, data=test_payload, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ 成功!")
                return True
            else:
                print("❌ 失敗")
                
        except Exception as e:
            print(f"エラー: {e}")
    
    return False

# ===== 🔍 事前診断 =====
print("=== 🔍 事前診断 ===")
diagnosis = diagnose_credentials()
for issue in diagnosis:
    print(issue)

print("\n=== 📝 重要な確認事項 ===")
print("1. Amazon Associates アカウントが承認済みか")
print("2. PA-API 5.0 のアクセス権限があるか")
print("3. 過去3日以内にAmazonで売上があるか（新規アカウントの場合）")
print("4. 正しいリージョンのエンドポイントを使用しているか")

print(f"\n=== リクエスト情報 ===")
print(f"エンドポイント: {endpoint}")
print(f"日時: {amz_date}")
print(f"パートナータグ: {partner_tag}")
print(f"リージョン: {region}")

# ===== 🚀 メインテスト =====
print("\n=== 🚀 メインテスト実行 ===")
try:
    response = requests.post(endpoint, headers=headers, data=payload, timeout=30)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功!")
        response_json = response.json()
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
    else:
        print("❌ エラー:")
        print("Response Body:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2, ensure_ascii=False))
        except:
            print(response.text)
        
        # エラー別対応
        error_solutions = {
            400: "🔧 リクエスト形式エラー - JSONペイロードやヘッダーを確認",
            403: "🔐 認証エラー - Access Key, Secret Key, Partner Tagを確認",
            404: "🔍 リソース未発見 - ASIN存在確認 or エンドポイント確認",
            429: "⏰ レート制限 - しばらく待ってから再実行",
            500: "🏥 サーバーエラー - Amazon側の問題、時間をおいて再試行"
        }
        
        if response.status_code in error_solutions:
            print(f"\n💡 {error_solutions[response.status_code]}")
        
        # 追加テスト実行
        print("\n=== 🔄 追加診断テスト ===")
        if not test_different_asins():
            print("\n❗ 全てのASINでエラー - 認証情報またはアカウント設定に問題がある可能性")
            
except requests.exceptions.RequestException as e:
    print(f"ネットワークエラー: {e}")
except Exception as e:
    print(f"予期しないエラー: {e}")

print("\n=== 🛠️ トラブルシューティング ===")
print("1. Amazon Associates Central で PA-API アクセスを申請済みか確認")
print("2. 新規アカウントの場合、最低3件の適格売上が必要")
print("3. アクセスキーとシークレットキーが最新か確認")
print("4. Partner Tag (Tracking ID) が正確か確認")
print("5. Marketplace設定が適切か確認 (www.amazon.co.jp)")
import requests
import datetime
import hashlib
import hmac
import json

# ===== 🔧 あなたのアクセス情報 =====
access_key = "AKPAEEKWJP1752396396"
secret_key = "zfDbpUflco4lP6PNdmxvCHbHGqSenn3fqQUrUyAF"
partner_tag = "choshucrypter-22"

# ===== 📦 テストASIN（日本Amazon用）=====
payload = json.dumps({
    "ItemIds": ["B0BSFQBCBJ"],  # 日本で確実に存在するASIN (Nintendo Switch本体など)
    "Resources": [
        "ItemInfo.Title",
        "Offers.Listings.Price",
        "Images.Primary.Medium",
        "ItemInfo.DetailPageURL"
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

# ===== 🌐 エンドポイント情報（日本用）=====
host = 'webservices.amazon.co.jp'
region = 'us-west-2'  # 日本のPA-APIでもus-west-2を使用
service = 'ProductAdvertisingAPI'
endpoint = f'https://{host}/paapi5/getitems'

# ===== 🕒 タイムスタンプ =====
t = datetime.datetime.now(datetime.UTC)
amz_date = t.strftime('%Y%m%dT%H%M%SZ')
date_stamp = t.strftime('%Y%m%d')

# ===== 📄 canonical request =====
canonical_uri = '/paapi5/getitems'
canonical_querystring = ''
canonical_headers = f'host:{host}\nx-amz-date:{amz_date}\n'
signed_headers = 'host;x-amz-date'
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
    'Authorization': authorization_header,
    'X-Amz-Target': 'com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems'
}

# ===== 🔍 診断機能追加 =====
def diagnose_credentials():
    """認証情報の基本チェック"""
    issues = []
    
    if not access_key or len(access_key) != 20:
        issues.append("❌ Access Keyが無効です（20文字である必要があります）")
    else:
        issues.append("✅ Access Key形式OK")
    
    if not secret_key or len(secret_key) != 40:
        issues.append("❌ Secret Keyが無効です（40文字である必要があります）")
    else:
        issues.append("✅ Secret Key形式OK")
        
    if not partner_tag:
        issues.append("❌ Partner Tagが設定されていません")
    else:
        issues.append("✅ Partner Tag設定済み")
    
    return issues

def test_different_asins():
    """複数のASINでテスト"""
    test_asins = [
        "B0BSFQBCBJ",  # Nintendo Switch (新しめ)
        "B07HCSQ48C",  # Echo Dot 3rd Gen
        "B08N5WRWNW",  # 元のASIN
    ]
    
    for asin in test_asins:
        print(f"\n--- {asin} をテスト中 ---")
        
        test_payload = json.dumps({
            "ItemIds": [asin],
            "Resources": ["ItemInfo.Title"],
            "PartnerTag": partner_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.co.jp"
        })
        
        # 新しい署名を生成
        payload_hash = hashlib.sha256(test_payload.encode('utf-8')).hexdigest()
        canonical_request = f'POST\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
        string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        test_headers = headers.copy()
        test_headers['Authorization'] = f'{algorithm} Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
        
        try:
            response = requests.post(endpoint, headers=test_headers, data=test_payload, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ 成功!")
                return True
            else:
                print("❌ 失敗")
                
        except Exception as e:
            print(f"エラー: {e}")
    
    return False

# ===== 🔍 事前診断 =====
print("=== 🔍 事前診断 ===")
diagnosis = diagnose_credentials()
for issue in diagnosis:
    print(issue)

print("\n=== 📝 重要な確認事項 ===")
print("1. Amazon Associates アカウントが承認済みか")
print("2. PA-API 5.0 のアクセス権限があるか")
print("3. 過去3日以内にAmazonで売上があるか（新規アカウントの場合）")
print("4. 正しいリージョンのエンドポイントを使用しているか")

print(f"\n=== リクエスト情報 ===")
print(f"エンドポイント: {endpoint}")
print(f"日時: {amz_date}")
print(f"パートナータグ: {partner_tag}")
print(f"リージョン: {region}")

# ===== 🚀 メインテスト =====
print("\n=== 🚀 メインテスト実行 ===")
try:
    response = requests.post(endpoint, headers=headers, data=payload, timeout=30)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功!")
        response_json = response.json()
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
    else:
        print("❌ エラー:")
        print("Response Body:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2, ensure_ascii=False))
        except:
            print(response.text)
        
        # エラー別対応
        error_solutions = {
            400: "🔧 リクエスト形式エラー - JSONペイロードやヘッダーを確認",
            403: "🔐 認証エラー - Access Key, Secret Key, Partner Tagを確認",
            404: "🔍 リソース未発見 - ASIN存在確認 or エンドポイント確認",
            429: "⏰ レート制限 - しばらく待ってから再実行",
            500: "🏥 サーバーエラー - Amazon側の問題、時間をおいて再試行"
        }
        
        if response.status_code in error_solutions:
            print(f"\n💡 {error_solutions[response.status_code]}")
        
        # 追加テスト実行
        print("\n=== 🔄 追加診断テスト ===")
        if not test_different_asins():
            print("\n❗ 全てのASINでエラー - 認証情報またはアカウント設定に問題がある可能性")
            
except requests.exceptions.RequestException as e:
    print(f"ネットワークエラー: {e}")
except Exception as e:
    print(f"予期しないエラー: {e}")

print("\n=== 🛠️ トラブルシューティング ===")
print("1. Amazon Associates Central で PA-API アクセスを申請済みか確認")
print("2. 新規アカウントの場合、最低3件の適格売上が必要")
print("3. アクセスキーとシークレットキーが最新か確認")
print("4. Partner Tag (Tracking ID) が正確か確認")
print("5. Marketplace設定が適切か確認 (www.amazon.co.jp)")
