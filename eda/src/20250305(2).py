from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from tqdm import tqdm
import os
import threading
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from glob import glob
import shutil
# 쓰레드 함수 정의
def scrape_data(thread_id, sigungu_list_chunk):
    # 각 쓰레드별 저장 디렉토리 생성
    save_dir = f'/home/koo4802/dev_ws/eda/data/Thread{thread_id}'
    os.makedirs(save_dir, exist_ok=True)
    
    options = webdriver.ChromeOptions()
    prefs = {'download.default_directory': save_dir,
             'download.prompt_for_download': False,
             'download.directory_upgrade': True,
             'safebrowsing.enabled': False}
    
    options.add_experimental_option('prefs', prefs)
    
    url = "https://www.opinet.co.kr/searRgSelect.do"
    driver = webdriver.Chrome(service=Service("/home/koo4802/dev_ws/eda/driver/chromedriver"),
                              options=options)
    
    for _ in range(2):  # 페이지 로딩 재시도
        driver.get(url)
        time.sleep(1)
    
    # 서울시 선택 (서울시 value는 "01"입니다)
    sido_btn = driver.find_element(By.ID, "SIDO_NM0")
    sido_option = sido_btn.find_elements(By.TAG_NAME, "option")
    sido_list = [value for option in sido_option if len(value := option.get_attribute("value"))>0]
    sido_btn.send_keys(sido_list[0])  # 서울시 선택
    time.sleep(1)
    
    # 각 시군구별로 처리 (입력받은 시군구 리스트 청크만 처리)
    for option in tqdm(sigungu_list_chunk, desc=f"Thread {thread_id}"):
        sigungu_btn = driver.find_element(By.ID, "SIGUNGU_NM0")
        sigungu_btn.send_keys(option)
        driver.implicitly_wait(3)
        driver.refresh()
        
        # 저장 버튼 클릭
        save = WebDriverWait(driver, timeout=40).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "btn_type6_ex_save")))
        save.click()
        
        # 파일이 다운로드될 때까지 대기
        path = f"{save_dir}/지역_*"
        current_count = len(glob(path))
        while len(glob(path)) <= current_count:
            time.sleep(0.1)
        # 파일 이름 변경
        time.sleep(1)  # 파일이 완전히 다운로드될 때까지 추가 대기
        downloaded_files = glob(f"{save_dir}/지역_*")
        if downloaded_files:
            latest_file = max(downloaded_files, key=os.path.getctime)
            new_filename = f"{save_dir}/{option}.xls"
            try:
                os.rename(latest_file, new_filename)
            except FileExistsError:
                os.remove(new_filename)  # 기존 파일이 있다면 삭제
                os.rename(latest_file, new_filename)
    # 모든 파일을 부모 디렉토리로 이동
    parent_dir = os.path.dirname(save_dir)
    for file in os.listdir(save_dir):
        src_path = os.path.join(save_dir, file)
        dst_path = os.path.join(parent_dir, file)
        try:
            shutil.move(src_path, dst_path)
        except FileExistsError:
            os.remove(dst_path)  # 기존 파일이 있다면 삭제
            shutil.move(src_path, dst_path)
    
    # 빈 디렉토리 삭제
    os.rmdir(save_dir)
    driver.quit()

# 메인 코드
def main():
    # 먼저 시도 목록 가져오기
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service("/home/koo4802/dev_ws/eda/driver/chromedriver"),
                              options=options)
    url = "https://www.opinet.co.kr/searRgSelect.do"
    for _ in range(2):
        driver.get(url)
        time.sleep(1)
        
    sido_btn = driver.find_element(By.ID, "SIDO_NM0")
    sido_option = sido_btn.find_elements(By.TAG_NAME, "option")
    sido_list = [value for option in sido_option if len(value := option.get_attribute("value"))>0]

    sigungu_btn = driver.find_element(By.ID, "SIGUNGU_NM0")
    sigungu_option = sigungu_btn.find_elements(By.TAG_NAME, "option")
    sigungu_list = [value for option in sigungu_option if len(value := option.get_attribute("value"))>0]

    driver.quit()
    
    # 시도 목록을 5개 쓰레드로 나누기
    num_threads = 5
    chunk_size = len(sigungu_list) // num_threads
    if len(sigungu_list) % num_threads != 0:
        chunk_size += 1
    
    sigungu_chunks = [sigungu_list[i:i+chunk_size] for i in range(0, len(sigungu_list), chunk_size)]
    # 필요한 경우 빈 청크 추가 (쓰레드 수보다 시도 수가 적을 경우)
    while len(sigungu_chunks) < num_threads:
        sigungu_chunks.append([])
    
    # 쓰레드 생성 및 실행
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=scrape_data, args=(i+1, sigungu_chunks[i]))
        threads.append(thread)
        thread.start()
    
    # 모든 쓰레드가 완료될 때까지 대기
    for thread in threads:
        thread.join()
    

# 메인 함수 실행
if __name__ == "__main__":
    main()