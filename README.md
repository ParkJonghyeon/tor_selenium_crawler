# tor_selenium_crawler

Docker Image로 제작되어 컨테이너 환경에서 돌아가는 것을 전제로 작성 된 코드  
필요한 Tor 브라우저 및 gecko driver의 경로 등은 Docker Image의 세팅을 따라감  

Docker hub 링크 - https://hub.docker.com/r/larkjh/tbselcrawler

* MS Azure나 AWS 환경에서 실행시키므로 Virtual Display 활성화 되어있음  
* 최대 사용 탭 개수는 5개로 고정되어있음(MAX_TAB_NUM)  
* 해당 변수는 input args로 조절 가능하게 고쳐야함

---

tor_pageCrawler_tab.py를 실행시키는데 필요한 input args로 사용할 주소 세트의 번호, 페이지의 타임 아웃 판단 기준 시간(초)를 받음  
* ex) 1번 주소 세트를 사용해 수집을 시도하고, 120초간 페이지 로딩이 지속 되는 경우 타임아웃으로 판단  
  python3 tor_pageCrawler_tab 1 120  
  
---

* 사용하는 주소 세트는 /home/tordocker/shared_dir/onion_link_set에 위치해야하고, 주소 세트명은 onion_link_set_<주소 세트의 번호>.tsv로 구성되어있음  
* 수집 된 결과는 /home/tordocker/shared_dir에 각각 디렉토리를 생성하여 저장
  * <수집 날짜>는 년월일시로 구성(24시간 표기법) - ex) 2019021211
  * output_dir에는 접속 시도한 onion 주소와 접속 결과 여부가 기록 된 tsv 파일이 저장  
    파일명은 output_<주소 세트의 번호>_<수집 날짜>.tsv의 형태로 저장  
  * output_dir에는 접속 시도한 onion 주소의 http response 헤더도 저장  
    파일명은 hidden_service_header_<주소 세트의 번호>.json 형태로 저장  
    현재 버전에서는 중복 된 주소에 대해서 데이터 갱신이나 날짜별 데이터 생성이 아닌 append로 계속해서 한 파일에 추가 작성해나가도록 구현되어 있음
  * html_source_dir_<수집 날짜>에는 해당 날짜에 수집한 모든 다크 웹의 HTML 파일이 저장
  * log_dir에는 tor_visit_log_<주소 세트의 번호>.txt의 형태로 수집 시작 시간, 수집 종료 시간, 에러 로그 정보를 기록한 텍스트 파일 저장

---

# Dockerfile

Dockerfile은 이미지에서 사용할 크롤러와 Tor 브라우저, Geckodriver를 로컬에서 COPY 명령어로 가져와서 사용 중  
(Tor 브라우저의 경우 네트워크에서 wget 등으로 다운로드 시 크래시 나는 경우가 있음)  

각각 Dockerfile과 동일한 경로상에 TBB, TBSEL, GECKO 디렉토리가 위치하고 각각 Tor 브라우저, tor_selenium_crawler, gecko driver의 압축 파일들이 위치하고 있어야함.
