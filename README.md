# 시장 지표 대시보드 배포

이 폴더는 Streamlit Community Cloud에 올릴 수 있도록 분리한 배포용 앱입니다.
부모 프로젝트의 자동매매 소스, 설정, 자격 증명 파일은 포함하지 않습니다.

## 포함된 파일

- `dashboard_100.py`: 기술지표 100개와 FRED 거시지표 대시보드
- `requirements.txt`: 로컬에서 확인한 Python 패키지 버전
- `.gitignore`: 인증정보, 로컬 분석 기록, 캐시 파일 제외

## GitHub에 올리기

GitHub에서 **새 저장소를 만든 뒤**, 이 폴더 안에서 다음 명령을 실행합니다.
`<YOUR_NAME>`과 `<REPOSITORY>`는 본인의 GitHub 사용자명과 저장소 이름으로 바꿉니다.

```powershell
Set-Location 'F:\소프트웨어\자동매매4\streamlit-deploy'
git init -b main
git add dashboard_100.py requirements.txt README.md .gitignore
git commit -m "Prepare market indicator dashboard"
git remote add origin https://github.com/<YOUR_NAME>/<REPOSITORY>.git
git push -u origin main
```

GitHub 웹사이트에서 저장소에 파일을 업로드해도 됩니다. 이 경우에도 **부모
프로젝트 폴더 전체가 아니라 이 배포 폴더의 파일만** 올리세요. 자격 증명,
다른 자동매매 코드, 거래 기록은 업로드하지 않습니다.

## Streamlit Community Cloud에 배포하기

1. [Streamlit Community Cloud](https://share.streamlit.io/)에 GitHub로 로그인합니다.
2. **Create app**을 누르고 위 저장소와 `main` 브랜치를 선택합니다.
3. 메인 파일 경로를 `dashboard_100.py`로 지정한 뒤 **Deploy**합니다.
4. 배포가 완료되면 발급된 `*.streamlit.app` 주소를 공유합니다.
5. 누구나 링크로 보게 하려면 앱의 Sharing 설정에서 공개 여부를 확인합니다.

이 앱은 Yahoo Finance와 FRED 공개 데이터에 접속하므로 배포 환경의 인터넷 연결이
필요합니다. API 키나 Streamlit Secrets는 필요하지 않습니다. Yahoo Finance 데이터는
실시간 시세/SLA가 보장되지 않습니다.

## 기록과 공개 범위

배포판의 최근 분석 기록은 **현재 방문자의 Streamlit 세션 안에서만** 유지됩니다.
브라우저 세션이 끝나거나 앱이 다시 시작되면 사라질 수 있습니다. 서버 파일에
공용 기록을 저장하지 않으므로 방문자 간 기록이 섞이지 않습니다. 영구 기록이
필요하다면 인증과 사용자별 데이터베이스를 별도로 구성해야 합니다.

공개 앱은 인터넷에 공개되며 로그인이나 사용자별 접근 제어가 설정되어 있지
않습니다. 투자 판단에 쓰기 전에 데이터와 점수 규칙을 직접 검증하세요.
