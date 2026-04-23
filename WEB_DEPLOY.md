# 웹 배포 가이드

앱을 여러 사람이 웹으로 접속해서 쓸 수 있게 만드는 세 가지 방법을 안내합니다. 상황에 맞춰 하나를 고르거나, 필요에 따라 여러 개를 조합해서 쓰셔도 됩니다.

---

## 📊 방법 비교

| 방법 | 세팅 시간 | 접속 범위 | 보안 | 추천 상황 |
|------|----------|----------|------|----------|
| **A. LAN 공유** | 5분 | 같은 Wi-Fi 사람만 | 🟢 안전 | 같은 사무실·회의실 내 5명 이내 |
| **B. Cloudflare Tunnel** | 10분 | 누구나 (URL 알면) | 🟡 URL 공유 주의 | 원격 동료·강박사님께 임시 시연 |
| **C. Streamlit Cloud** | 20분 | 누구나 (영구) | 🟡 공개됨 | 학회·논문 링크·상시 데모 |

---

## 🅰️ 방법 A — LAN 공유 (같은 Wi-Fi 내)

내 PC에서 Streamlit을 실행하면서, **같은 Wi-Fi / 같은 사무실 네트워크**에 있는 다른 사람들이 접속할 수 있게 합니다.

### 실행 (Windows)
```
start_server.bat 더블클릭
```

### 실행 (macOS / Linux)
```bash
./start_server.sh
```

### 실행하면 이런 메시지가 뜹니다
```
============================================================
  Ozone Hotspot Dashboard — starting...
============================================================

  On THIS PC:          http://localhost:8501
  On other PCs (LAN):  http://192.168.0.15:8501

  Tell others to connect to the "LAN" URL above.
```

### 다른 사람들은 이렇게 접속
1. 본인 PC와 **같은 Wi-Fi**에 연결
2. 브라우저 주소창에 `http://192.168.0.15:8501` 입력 (실제 IP는 스크립트가 알려줌)

### 방화벽 설정 (Windows)
처음 실행 시 Windows 방화벽이 차단할 수 있습니다. 팝업이 뜨면 **"개인 네트워크"에서 허용** 체크.

### 장점
- ✅ 가장 간단, 5분 만에 가능
- ✅ 내 PC에서만 돌아가므로 **데이터가 외부로 나가지 않음**
- ✅ 무료

### 단점
- ⚠️ 같은 Wi-Fi 안에 있는 사람만 접속 가능
- ⚠️ 내 PC가 꺼져있으면 접속 불가
- ⚠️ 내 PC의 IP가 바뀌면 URL도 바뀜 (DHCP 환경)

---

## 🅱️ 방법 B — Cloudflare Tunnel (외부 접속 가능)

내 PC에서 돌아가는 Streamlit에 **임시 공개 URL**을 붙여서, 인터넷 어디서든 접속 가능하게 합니다. 원격에 있는 강박사님도 접속할 수 있어요.

### 최초 1회 설치

**Windows**:
1. https://github.com/cloudflare/cloudflared/releases/latest 접속
2. `cloudflared-windows-amd64.exe` 다운로드
3. `cloudflared.exe`로 이름 변경
4. `ozone_pkg` 폴더에 넣기

**macOS**:
```bash
brew install cloudflare/cloudflare/cloudflared
```

**Linux**:
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
```

### 실행

**Windows**: `start_public_tunnel.bat` 더블클릭

**macOS / Linux**:
```bash
./start_public_tunnel.sh
```

### 실행하면
두 개의 창이 열립니다:
- 하나는 Streamlit (작게 켜져있음)
- 하나는 Cloudflare Tunnel 로그 — 여기에 **공개 URL**이 뜸

예시:
```
Your quick Tunnel has been created! Visit it at:
https://soft-dream-1234.trycloudflare.com
```

### 이 URL을 강박사님께 전달
- 📱 카카오톡 · 이메일 · 문자로 URL 전송
- 클릭만 하면 어디서든 접속

### 장점
- ✅ **어디서든** 접속 가능 (집·출장·학회장 등)
- ✅ HTTPS 자동 (암호화)
- ✅ 내 PC의 IP 공개 안 됨 (Cloudflare 서버 경유)
- ✅ 무료, 회원가입 불필요

### 단점
- ⚠️ URL을 아는 사람은 누구나 접속 가능 → URL 공유에 주의
- ⚠️ 내 PC를 꺼놓으면 접속 불가
- ⚠️ URL이 매번 바뀜 (세션마다 새 URL) — **고정 URL**은 Cloudflare 계정 필요 (추가 설정)

### 🔒 비밀번호 걸고 싶으면?
Streamlit 자체는 기본 인증이 없지만, 간단히 다음 방법이 있습니다:
- `streamlit_authenticator` 패키지 사용 (간단한 로그인 추가)
- 또는 Cloudflare Access (계정 필요, 무료)

이 중 필요한 거 있으면 말씀해주세요.

---

## 🅲 방법 C — Streamlit Community Cloud (영구 URL)

내 PC와 무관하게, **Streamlit 회사의 클라우드**에서 앱이 24/7 돌아갑니다. `https://ozone-hotspot.streamlit.app` 같은 영구 URL을 받아요.

### 최초 1회 설정 (20분)

**1단계 — GitHub 저장소 만들기** (GitHub 계정 필요)

1. https://github.com 가입 (무료)
2. 새 저장소 생성: `ozone_hotspot` (public으로)
3. `ozone_pkg` 폴더 안의 파일을 GitHub에 업로드
   - ⚠️ **데이터 CSV는 올리지 말 것** (`.gitignore`에 이미 포함됨)

업로드 방법 (터미널):
```bash
cd ozone_pkg
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<본인계정>/ozone_hotspot.git
git push -u origin main
```

또는 GitHub Desktop 앱 사용 (GUI로 편함).

**2단계 — Streamlit Cloud 연결**

1. https://share.streamlit.io 접속
2. GitHub 계정으로 로그인
3. `New app` 클릭
4. 설정:
   - Repository: `<본인계정>/ozone_hotspot`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: `ozone-hotspot` (원하는 이름)
5. `Deploy!` 클릭

**3단계 — 완료**

2~3분 후 `https://ozone-hotspot.streamlit.app` 같은 URL로 접속 가능.

### 업데이트하는 법
GitHub에 새 코드를 push하면 자동으로 Streamlit Cloud에도 반영됩니다.

```bash
git add .
git commit -m "Updated dashboard"
git push
```

### 장점
- ✅ **영구 URL** (24/7 접속 가능)
- ✅ 내 PC 꺼도 됨
- ✅ 여러 사람이 동시에 사용 가능
- ✅ 무료 (public 저장소 기준)

### 단점
- ⚠️ **GitHub에 코드 공개됨** (public) — 비공개 원하면 Streamlit Cloud 유료 플랜
- ⚠️ 세팅에 20분 걸림
- ⚠️ 자원 제한: 1GB RAM, 1 CPU — 대량 파일 처리엔 부족할 수 있음

### 🔒 비공개로 하려면?
- Streamlit Cloud Teams: 월 $20~ (유료)
- 또는 GitHub private + Streamlit Cloud 유료 플랜

### 📝 데모 모드 설정 팁
Streamlit Cloud는 누구나 접속 가능하므로, 실제 측정 데이터는 업로드 안 하는 게 좋습니다. 데모용 샘플 CSV를 미리 저장소에 넣고 "샘플로 먼저 테스트해보세요" 안내 문구를 추가하는 것을 권장합니다.

---

## 🎯 추천 — 본 시나리오 (강박사님·실무자 5명 이내)

**첫 2주**: 방법 **A (LAN 공유)** — 같은 사무실에서 바로 시연
**학회·원격 공유 필요 시**: 방법 **B (Cloudflare Tunnel)** — 그때그때 URL 생성
**공식 도구로 굳어지면**: 방법 **C (Streamlit Cloud)** — 영구 URL

---

## 📋 자주 묻는 질문

**Q: 세 방법을 동시에 쓸 수 있나요?**
A: 네. 예를 들어 평소엔 A로 쓰다가 급한 원격 시연만 B로, 학회 발표 전엔 C도 올려두는 식으로 조합 가능합니다.

**Q: 내 PC 꺼도 되는 건 C만?**
A: 맞습니다. A와 B는 내 PC가 켜져있어야 합니다.

**Q: 방화벽·보안 프로그램이 Streamlit을 차단해요.**
A:
- A (LAN): Windows 방화벽에서 `8501` 포트 허용
- B (Tunnel): cloudflared가 알아서 하므로 보통 괜찮음
- 기관 보안 정책상 외부 접속 차단된 경우: IT팀 문의 필요

**Q: Cloudflare Tunnel이 끊기면?**
A: 터미널에서 Ctrl+C로 중지 후 다시 스크립트 실행. URL은 매번 새로 발급됩니다 (고정 URL은 Cloudflare 계정 필요).

**Q: Streamlit Cloud에서 Korean font가 깨져요.**
A: 이 문제는 패키지 내부에서 이미 해결되어 있습니다 (제목 등을 영문으로 자동 변환). 그래도 문제 있으면 말씀해주세요.

**Q: 누가 내 URL에 접속하는지 알 수 있나요?**
A:
- A (LAN): Streamlit 터미널에 IP가 찍힙니다
- B (Tunnel): cloudflared 로그에 찍힙니다
- C (Streamlit Cloud): Streamlit Cloud 대시보드에서 통계 확인

---

## 🚀 지금 바로 시작

**가장 쉬운 방법 (방법 A)**:

Windows:
```
ozone_pkg 폴더 열기 → start_server.bat 더블클릭
```

macOS/Linux:
```bash
cd ozone_pkg
./start_server.sh
```

브라우저가 자동으로 열리면 성공. 터미널에 뜬 "LAN" URL을 동료에게 전달하세요.
