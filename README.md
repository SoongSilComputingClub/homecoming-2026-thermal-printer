# SSCC 홈커밍 티켓 프린터

0~99번 럭키드로우 추첨권을 영수증 프린터로 출력합니다. 기본 설정은 현장에서 길이를 맞춘 버전입니다. 점선을 따라 접으면 반대편에 세로 시간표와 [행사 홈페이지](https://homecoming-2026.sscc-ssu.com/) QR이 보입니다.

## 준비

Linux에서 Python 3.10 이상, ImageMagick의 `convert`, CUPS의 `lp`, 나눔 글꼴과 DejaVu Sans Mono Bold가 필요합니다. 기본 대기열은 `Receipt_Printer`이며, 프린터는 384도트 폭의 ESC/POS 이미지와 자동 절단을 지원해야 합니다.

```bash
lpstat -p
python3 ticket.py --help
```

파이썬 패키지를 설치할 필요는 없습니다. 가상환경을 쓰려면 `uv venv`를 실행한 뒤 아래 명령의 `python3`를 `.venv/bin/python`으로 바꾸면 됩니다. 글꼴 경로는 `ticket.py` 상단에 있습니다.

## 출력

저장소 폴더에서 실행합니다. 번호는 그대로 찍히며 앞에 0을 붙이지 않습니다.

```bash
python3 ticket.py --num=5
python3 ticket.py --range=0-60
python3 ticket.py --num=5 --preview=/tmp/ticket-5.png
python3 ticket.py --num=5 --printer=Receipt_Printer --timetable-bottom=64
```

`--range`는 시작과 끝 번호를 모두 포함합니다. 각 번호를 오름차순으로 한 장씩 출력하고 한 장마다 절단 명령을 보냅니다. `--preview`는 한 번호를 PNG로 저장하며 프린터에 전송하지 않습니다.

| 옵션 | 기본값 | 동작 |
| --- | --- | --- |
| `--num=N` | 필수 선택 | 0~99 중 한 번호 |
| `--range=A-B` | 필수 선택 | A~B를 한 장씩 출력. `--num`과 함께 쓸 수 없음 |
| `--printer=NAME` | `Receipt_Printer` | CUPS 대기열 |
| `--preview=PNG` | 꺼짐 | `--num` 한 장의 미리보기 |
| `--no-timetable` | 꺼짐 | 시간표와 접는 선 생략 |
| `--no-cut` | 꺼짐 | 자동 절단 생략 |
| `--feed=N` | 48 | 절단 전 이송량. 시간표가 있으면 시작에도 같은 양을 추가 |
| `--fold-gap=N` | 24 | 접는 점선이 들어가는 여백 |
| `--timetable-top=N` | 40 | 시간표 위 추가 여백 |
| `--timetable-bottom=N` | 64 | 시간표 아래 추가 여백 |
| `--timetable-speed=N` | 1 | 시간표 인쇄 속도 단계. 0은 프린터 기본값 |
| `--qr-dot=N` | 4 | QR 한 칸의 도트 수. 2~4 |

길이 옵션은 도트 단위입니다. 203 dpi 프린터에서 8도트는 약 1mm입니다. 일정은 `ticket.py`의 `render_timetable()`에 있고, `homepage-qr.txt`에는 공식 홈페이지 URL의 QR 패턴이 들어 있습니다.

## AI에게 시키기

> 이 폴더의 README를 읽고 5번을 한 장 출력해 줘. 시간표 아래 여백은 72도트로 해 줘.

이 요청은 `python3 ticket.py --num=5 --timetable-bottom=72`로 실행하면 됩니다. 여러 장은 요청에 맞게 `--range`를 사용합니다. 미리보기 요청에는 `--preview`를 붙입니다. 실제 출력 요청에서는 번호와 수량을 확인해 한 번만 제출하고, 반환된 작업 ID를 `lpstat -W completed -o Receipt_Printer`에서 확인합니다. 처리 중인 작업을 다시 제출하면 중복 출력될 수 있습니다.
