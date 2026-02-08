import requests
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .env 파일 로드 (로컬 테스트용)
load_dotenv()

def fetch_koreaexim_rates():
    # Github Secrets에 등록된 키 이름: EXCHANGE_KEY
    auth_key = os.getenv('EXCHANGE_KEY')
    if not auth_key:
        print("❌ Error: 환경변수 EXCHANGE_KEY를 찾을 수 없습니다.")
        return None, None

    # 오늘 날짜부터 과거로 조회
    target_date = datetime.now()
    max_retries = 10 
    
    url = "https://www.koreaexim.go.kr/site/program/financial/exchangeJSON"

    for i in range(max_retries):
        search_date_str = target_date.strftime("%Y%m%d")
        print(f"🔄 시도 {i+1}: {search_date_str} 데이터 조회 중...")

        params = {
            'authkey': auth_key,
            'searchdate': search_date_str,
            'data': 'AP01'
        }

        try:
            # verify=False: SSL 인증서 오류 방지
            response = requests.get(url, params=params, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                # 데이터가 유효한 리스트인지 확인
                if isinstance(data, list) and data:
                    print(f"✅ 성공! {search_date_str} 기준 데이터를 가져왔습니다.")
                    return data, search_date_str 
                else:
                    print(f"⚠️ {search_date_str} 데이터 없음 (휴일 등)")
            else:
                print(f"❌ 요청 실패 (Status: {response.status_code})")

        except Exception as e:
            print(f"❌ 에러 발생: {e}")

        # 하루 전으로 이동
        target_date -= timedelta(days=1)

    print("❌ 최근 10일간의 데이터를 찾을 수 없습니다.")
    return None, None

def process_and_save(data, date_str):
    if not data:
        return

    # 1. 데이터 폴더 생성 (없으면 생성)
    save_dir = "data"
    os.makedirs(save_dir, exist_ok=True)

    # 2. DataFrame 생성 및 컬럼명 매핑
    df = pd.DataFrame(data)
    df.columns = [c.lower() for c in df.columns] # 키값을 소문자로 통일

    column_mapping = {
        'cur_unit': '통화코드',
        'cur_nm': '국가/통화명',
        'ttb': '전신환_받으실때',
        'tts': '전신환_보내실때',
        'deal_bas_r': '매매기준율',
        'bkpr': '장부가격',
        'yy_efee_r': '년환가료율',
        'ten_dd_efee_r': '10일환가료율',
        'kftc_deal_bas_r': '서울외국환중개_매매기준율',
        'kftc_bkpr': '서울외국환중개_장부가격'
    }

    # 존재하는 컬럼만 이름 변경
    rename_map = {k: v for k, v in column_mapping.items() if k in df.columns}
    df.rename(columns=rename_map, inplace=True)
    
    # 3. 기준일자 컬럼 추가
    df['기준일자'] = date_str
    
    # 4. 숫자 데이터 전처리 (콤마 제거)
    exclude_cols = ['통화코드', '국가/통화명', '기준일자']
    for col in df.columns:
        if col not in exclude_cols and df[col].dtype == 'object':
            df[col] = df[col].str.replace(",", "").str.strip()
            # 빈 값 처리 후 float 변환
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 5. 저장할 컬럼 순서 정리
    final_columns = ['기준일자'] + list(rename_map.values())
    df = df[final_columns]

    # 6. CSV 파일로 저장 (/data/exchange_rates.csv)
    filename = os.path.join(save_dir, "exchange_rates.csv")
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print(f"💾 저장 완료: {filename}")
    print(df.head().to_string())

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    rates_data, rates_date = fetch_koreaexim_rates()
    
    if rates_data:
        process_and_save(rates_data, rates_date)