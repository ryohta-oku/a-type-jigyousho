import requests
import datetime
import hashlib
import hmac
import json
import urllib.parse
import time

# ===== 🔧 設定情報 =====
access_key = "AKPAEEKWJP1752396396"
secret_key = "zfDbpUflco4lP6PNdmxvCHbHGqSenn3fqQUrUyAF"
partner_tag = "choshucrypter-22"

# ===== 🌐 地域別エンドポイント設定 =====
REGIONS = {
    'japan': {
        'host': 'webservices.amazon.co.jp',
        'region': 'us-west-2',
        'marketplace': 'www.amazon.co.jp'
    },
    'us': {
        'host': 'webservices.amazon.com',
        'region': 'us-east-1',
        'marketplace': 'www.amazon.com'
    }
}

class AmazonPAAPI:
    def __init__(self, access_key, secret_key, partner_tag, region_config):
        self.access_key = access_key
        self.secret_key = secret_key
        self.partner_tag = partner_tag
        self.host = region_config['host']
        self.region = region_config['region']
        self.marketplace = region_config['marketplace']
        self.service = 'ProductAdvertisingAPI'
        self.endpoint = f'https://{self.host}/paapi5/getitems'
        
    def sign(self, key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def get_signature_key(self, key, date_stamp, region_name, service_name):
        k_date = self.sign(('AWS4' + key).encode('utf-8'), date_stamp)
        k_region = self.sign(k_date, region_name)
        k_service = self.sign(k_region, service_name)
        k_signing = self.sign(k_service, 'aws4_request')
        return k_signing

    def create_canonical_request(self, payload, amz_date):
        """正規化リクエストを作成"""
        canonical_uri = '/paapi5/getitems'
        canonical_querystring = ''
        canonical_headers = f'host:{self.host}\nx-amz-date:{amz_date}\n'
        signed_headers = 'host;x-amz-date'
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        canonical_request = (
            f'POST\n'
            f'{canonical_uri}\n'
            f'{canonical_querystring}\n'
            f'{canonical_headers}\n'
            f'{signed_headers}\n'
            f'{payload_hash}'
        )
        
        return canonical_request, signed_headers

    def create_signature(self, canonical_request, amz_date, date_stamp, signed_headers):
        """署名を作成"""
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{self.region}/{self.service}/aws4_request'
        
        string_to_sign = (
            f'{algorithm}\n'
            f'{amz_date}\n'
            f'{credential_scope}\n'
            f'{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        )
        
        signing_key = self.get_signature_key(self.secret_key, date_stamp, self.region, self.service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        authorization_header = (
            f'{algorithm} '
            f'Credential={self.access_key}/{credential_scope}, '
            f'SignedHeaders={signed_headers}, '
            f'Signature={signature}'
        )
        
        return authorization_header

    def get_items(self, item_ids, resources=None, retry_count=3):
        """商品情報を取得"""
        if resources is None:
            resources = [
                "ItemInfo.Title",
                "Offers.Listings.Price",
                "Images.Primary.Medium"
            ]
        
        payload = json.dumps({
            "ItemIds": item_ids,
            "Resources": resources,
            "PartnerTag": self.partner_tag,
            "PartnerType": "Associates",
            "Marketplace": self.marketplace
        }, separators=(',', ':'))  # スペースを削除
        
        for attempt in range(retry_count):
            try:
                # 新しいタイムスタンプを生成
                t = datetime.datetime.now(datetime.UTC)
                amz_date = t.strftime('%Y%m%dT%H%M%SZ')
                date_stamp = t.strftime('%Y%m%d')
                
                # 署名を作成
                canonical_request, signed_headers = self.create_canonical_request(payload, amz_date)
                authorization_header = self.create_signature(canonical_request, amz_date, date_stamp, signed_headers)
                
                # ヘッダーを設定
                headers = {
                    'Content-Type': 'application/json; charset=utf-8',
                    'X-Amz-Date': amz_date,
                    'Authorization': authorization_header,
                    'X-Amz-Target': 'com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems'
                }
                
                print(f"試行 {attempt + 1}: {self.endpoint}")
                print(f"Marketplace: {self.marketplace}")
                
                # リクエスト送信
                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    data=payload,
                    timeout=30
                )
                
                return response
                
            except Exception as e:
                print(f"試行 {attempt + 1} でエラー: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2)  # 2秒待機
                else:
                    raise e

def diagnose_response(response):
    """レスポンスを詳細に診断"""
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("✅ 成功!")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2, ensure_ascii=False))
            return True
        except json.JSONDecodeError:
            print("❌ JSONデコードエラー")
            print("Response text:", response.text)
            return False
    else:
        print("❌ エラー:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2, ensure_ascii=False))
            
            # エラー詳細の分析
            if 'Errors' in response_json:
                for error in response_json['Errors']:
                    error_code = error.get('Code', 'Unknown')
                    error_message = error.get('Message', 'No message')
                    print(f"エラーコード: {error_code}")
                    print(f"エラーメッセージ: {error_message}")
                    
        except json.JSONDecodeError:
            print("Response text:", response.text)
        
        # ステータスコード別の詳細診断
        error_details = {
            400: {
                'title': '🔧 リクエスト形式エラー',
                'solutions': [
                    'JSONペイロードの構文を確認',
                    '必須パラメータが不足していないか確認',
                    'Content-Typeヘッダーが正しいか確認'
                ]
            },
            403: {
                'title': '🔐 認証/認可エラー',
                'solutions': [
                    'Access KeyとSecret Keyが正しいか確認',
                    'Partner Tag (Tracking ID) が正しいか確認',
                    'Amazon Associates アカウントが承認済みか確認',
                    'PA-API 5.0のアクセス権限があるか確認',
                    '新規アカウントの場合、売上実績要件を満たしているか確認'
                ]
            },
            404: {
                'title': '🔍 リソース未発見',
                'solutions': [
                    'エンドポイントURLが正しいか確認',
                    'ASINが存在するか確認',
                    'Marketplaceが正しいか確認',
                    'リージョン設定が適切か確認'
                ]
            },
            429: {
                'title': '⏰ レート制限',
                'solutions': [
                    'リクエスト頻度を下げる',
                    'しばらく時間をおいて再試行'
                ]
            },
            500: {
                'title': '🏥 サーバーエラー',
                'solutions': [
                    'Amazon側の一時的な問題の可能性',
                    '時間をおいて再試行',
                    'リクエストペイロードの内容を確認'
                ]
            }
        }
        
        if response.status_code in error_details:
            error_info = error_details[response.status_code]
            print(f"\n💡 {error_info['title']}")
            for solution in error_info['solutions']:
                print(f"   • {solution}")
        
        return False

def test_different_regions_and_asins():
    """複数のリージョンとASINでテスト"""
    
    # テスト用ASIN（リージョン別）
    test_data = [
        {
            'region': 'japan',
            'asins': ['B0BSFQBCBJ', 'B07HCSQ48C', 'B08N5WRWNW']
        },
        {
            'region': 'us',
            'asins': ['B08N5WRWNW', 'B07HCSQ48C', 'B073H9RQ9Q']
        }
    ]
    
    for test_case in test_data:
        region = test_case['region']
        asins = test_case['asins']
        
        print(f"\n{'='*50}")
        print(f"🌍 {region.upper()}リージョンでテスト")
        print(f"{'='*50}")
        
        api = AmazonPAAPI(access_key, secret_key, partner_tag, REGIONS[region])
        
        for asin in asins:
            print(f"\n--- ASIN: {asin} ---")
            try:
                response = api.get_items([asin], ["ItemInfo.Title"])
                success = diagnose_response(response)
                
                if success:
                    print(f"✅ {region}リージョンで成功!")
                    return True
                    
            except Exception as e:
                print(f"例外エラー: {e}")
    
    return False

def run_comprehensive_test():
    """包括的なテストを実行"""
    print("🔍 Amazon PA-API 5.0 包括的テスト開始")
    print("=" * 60)
    
    # 基本認証情報チェック
    print("\n=== 📋 認証情報チェック ===")
    if len(access_key) == 20:
        print("✅ Access Key形式: OK")
    else:
        print("❌ Access Key形式: NG (20文字である必要があります)")
    
    if len(secret_key) == 40:
        print("✅ Secret Key形式: OK")
    else:
        print("❌ Secret Key形式: NG (40文字である必要があります)")
    
    if partner_tag:
        print("✅ Partner Tag: 設定済み")
    else:
        print("❌ Partner Tag: 未設定")
    
    # 重要な確認事項
    print("\n=== 📝 重要な確認事項 ===")
    important_checks = [
        "Amazon Associates アカウントが承認済みか",
        "PA-API 5.0 のアクセス権限が付与されているか",
        "新規アカウントの場合、適格売上要件を満たしているか",
        "Access KeyとSecret Keyが最新のものか",
        "Partner Tag (Tracking ID) が正確か"
    ]
    
    for i, check in enumerate(important_checks, 1):
        print(f"{i}. {check}")
    
    # 複数リージョンでのテスト実行
    print("\n=== 🚀 テスト実行 ===")
    success = test_different_regions_and_asins()
    
    if not success:
        print("\n" + "="*60)
        print("❗ 全てのテストが失敗しました")
        print("="*60)
        print("\n🛠️ 主要なトラブルシューティング手順:")
        print("1. Amazon Associates Central にログインして以下を確認:")
        print("   • アカウントステータスが「承認済み」か")
        print("   • PA-API利用申請が承認されているか")
        print("   • 最近3日以内に適格売上があるか（新規の場合）")
        print("\n2. 認証情報の確認:")
        print("   • Amazon Associates Central の「ツール」→「Product Advertising API」から")
        print("   • 最新のAccess KeyとSecret Keyを取得")
        print("   • Partner Tag (Tracking ID) が正しいか確認")
        print("\n3. アカウント要件:")
        print("   • 新規アカウント: 登録後120日以内に3件以上の適格売上が必要")
        print("   • 既存アカウント: 過去30日以内に売上実績が必要")
        
    return success

if __name__ == "__main__":
    run_comprehensive_test()
