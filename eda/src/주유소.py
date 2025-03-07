from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import json
import threading
import os
from tqdm import tqdm

# 쓰레드 함수 정의
def process_gas_info(thread_id, sigungu_list_chunk):
    # 각 쓰레드별 결과 저장 리스트
    thread_gas_info_list = []
    
    # 각 쓰레드별 웹드라이버 초기화
    url = "https://www.opinet.co.kr/searRgSelect.do"
    driver = webdriver.Chrome(service=Service("/home/koo4802/dev_ws/eda/driver/chromedriver"))
    driver.set_window_size(1400, 1080)
    
    for _ in range(2):
        driver.get(url)
        time.sleep(1)
    
    # 서울시 선택 (서울시 value는 "01"입니다)
    sido_btn = driver.find_element(By.ID, "SIDO_NM0")
    sido_option = sido_btn.find_elements(By.TAG_NAME, "option")
    sido_list = [value for option in sido_option if len(value := option.get_attribute("value"))>0]
    sido_btn.send_keys(sido_list[0])  # 서울시 선택
    time.sleep(1)
    
    # 각 시군구별로 처리
    for sigungu in tqdm(sigungu_list_chunk, desc=f"Thread {thread_id}"):
        # 시군구 선택
        sigungu_btn = driver.find_element(By.ID, "SIGUNGU_NM0")
        sigungu_btn.send_keys(sigungu)
        driver.implicitly_wait(3)
        driver.refresh()
        time.sleep(1)
        
        # 레이어와 바디 ID 정의
        layer_ids = ["os_layer1", "os_layer2", "os_layer3", "os_layer4"]
        body_ids = ["body2", "body1", "body3", "body4"]
        
        # 각 레이어 처리
        for layer_id, body_id in zip(layer_ids, body_ids):
            tab_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, layer_id))
            )
            tab_btn.find_element(By.TAG_NAME, "a").click()
            
            # 가스 정보 수집
            try:
                body_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, body_id))
                )
                a_list = body_element.find_elements(By.TAG_NAME, "a")
                for a in a_list:
                    a.click()
                    mini_window = WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.ID, "os_dtail_info"))
                            )
                    firm_title = mini_window.find_element(By.ID, "poll_div_nm").text
                    gas_title = mini_window.find_element(By.ID, "os_nm").text
                    address = mini_window.find_element(By.ID, "rd_addr").text
                    cost_info = mini_window.find_element(By.ID, "infoTbody").text
                    gas_info = {
                        "상표": firm_title,
                        "주유소명": gas_title,
                        "주소": address,
                        "시군구": sigungu,
                        "유종별 가격": {},
                        "부가정보": {}
                    }
                    lines = cost_info.split("\n")
                    gas_price = {}
                    for line in lines:
                        gas_price[line.split(" ")[0]] = line.split(" ")[1]
                    gas_info["유종별 가격"] = gas_price
                    time.sleep(1)
                    detail_ids = ["cwsh_yn", "lpg_yn", "maint_yn", "cvs_yn", "sel24_yn"]
                    detail_keys = ["세차장 여부", "충전소 여부", "경정비 여부", "편의점 여부", "24시 영업 여부"]
                    detail_info = {}
                    for idx, id in enumerate(detail_ids):
                        src_value = driver.find_element(By.ID, id).get_attribute("src")
                        if "off" in src_value:
                            detail_info[detail_keys[idx]] = "N"
                        else:
                            detail_info[detail_keys[idx]] = "Y"
                    gas_info["부가정보"] = detail_info
                    thread_gas_info_list.append(gas_info)
            except Exception as e:
                print(f"Error in Thread {thread_id} - {sigungu} - {layer_id} {e}")
                continue
    
    driver.quit()
    return thread_gas_info_list

def main():
    # 먼저 시도/시군구 목록 가져오기
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service("/home/koo4802/dev_ws/eda/driver/chromedriver"),
                              options=options)
    url = "https://www.opinet.co.kr/searRgSelect.do"
    for _ in range(2):
        driver.get(url)
        time.sleep(1)
        
    # 서울시 선택 (서울시 value는 "01"입니다)
    sido_btn = driver.find_element(By.ID, "SIDO_NM0")
    sido_option = sido_btn.find_elements(By.TAG_NAME, "option")
    sido_list = [value for option in sido_option if len(value := option.get_attribute("value"))>0]
    sido_btn.send_keys(sido_list[0])  # 서울시 선택
    time.sleep(1)
    
    # 시군구 목록 가져오기
    sigungu_btn = driver.find_element(By.ID, "SIGUNGU_NM0")
    sigungu_option = sigungu_btn.find_elements(By.TAG_NAME, "option")
    sigungu_list = [value for option in sigungu_option if len(value := option.get_attribute("value"))>0]
    
    driver.quit()
    
    # 5개 쓰레드로 작업 분배
    num_threads = 5
    chunk_size = len(sigungu_list) // num_threads
    if len(sigungu_list) % num_threads != 0:
        chunk_size += 1
    
    sigungu_chunks = [sigungu_list[i:i+chunk_size] for i in range(0, len(sigungu_list), chunk_size)]
    # 필요한 경우 빈 청크 추가 (쓰레드 수보다 시군구 수가 적을 경우)
    while len(sigungu_chunks) < num_threads:
        sigungu_chunks.append([])
    
    # 쓰레드 생성 및 실행
    threads = []
    results = [None] * num_threads
    
    for i in range(num_threads):
        if sigungu_chunks[i]:  # 작업이 있는 쓰레드만 실행
            thread = threading.Thread(
                target=lambda idx, chunk: results.__setitem__(idx, process_gas_info(idx+1, chunk)),
                args=(i, sigungu_chunks[i])
            )
            threads.append(thread)
            thread.start()
    
    # 모든 쓰레드가 완료될 때까지 대기
    for thread in threads:
        thread.join()
    
    # 결과 합치기
    all_gas_info = []
    for result in results:
        if result:
            all_gas_info.extend(result)
    
    # 데이터프레임 생성 및 처리
    df = pd.DataFrame(all_gas_info)
    
    # 딕셔너리 타입의 열 처리하기
    for col in df.columns:
        # 해당 열에 딕셔너리 타입의 값이 있는지 확인
        if df[col].apply(lambda x: isinstance(x, dict)).any():
            # 딕셔너리를 JSON 문자열로 변환
            df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
    
    # 중복 제거
    df = df.drop_duplicates()
    df = df.reset_index(drop=True)
    
    # JSON 문자열을 다시 딕셔너리로 변환
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, str) and x.startswith('{')).any():
            df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, str) and x.startswith('{') else x)
    
    # 결과 저장 또는 반환
    print(f"총 {len(df)}개의 주유소 정보를 수집했습니다.")
    return df

if __name__ == "__main__":
    df = main()
    # 필요하다면 CSV 파일로 저장
    df.to_csv("/home/koo4802/dev_ws/eda/data/gas_stations.csv", index=False)