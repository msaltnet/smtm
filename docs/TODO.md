# 문서 TODO (이월 과제)

이 문서는 **다음 릴리스에서 처리하기로 미룬 문서 작업**을 기록합니다.

`docs/public/*`, `README.md`, `README-ko-kr.md`, `docs/wiki/architecture.md`는
텔레그램 전용 제어 + 가상거래 기본값 변경에 맞춰 갱신 완료했습니다.
아래 항목은 **이번 변경 이전부터 이미 낡아 있던 문서**들이라 인라인으로 고치지 않고
별도 과제로 분리했습니다.

---

## 1. `docs/wiki/` 전면 재작성 (다음 릴리스)

`docs/wiki/` 문서 대부분은 2.0 이전 시뮬레이터 시대의 내용입니다.
지금 코드에는 존재하지 않는 실행 모드와 플래그를 설명하고 있어
부분 수정보다 재작성이 맞습니다.

**중요**: 이 문서 부패(rot)는 텔레그램 전용 변경 **이전부터** 존재했습니다.
즉 `--mode 0` / `--mode 1`을 없앤 것 때문에 틀려진 게 아니라, 원래부터 틀려 있었습니다.
그래서 이번 작업 범위에서 제외하고 이월했습니다.

### 1.1 완전히 폐기된 문서 (재작성 또는 삭제)

| 파일 | 문제 | 처리 방향 |
|------|------|-----------|
| `docs/wiki/how-to-setup-and-run.md` | `--mode 0` ~ `--mode 5`와 2.0 이전 시뮬레이터 플래그(`--from_dash_to`, `--offset`, `--title`, `--file`, `--config`)를 설명. **전부 존재하지 않음.** | 전면 재작성 - 현재 유일한 실행 방법인 `python -m smtm --token <telegram-bot-token> --chatid <chat-id>` 기준으로 다시 씀 |
| `docs/wiki/tips.md` | `nohup python -m smtm --mode 3 --demo 1` 예시. `--mode`도 `--demo`도 없음. | 폐기 - 백그라운드 실행 팁은 `docs/public/user-guide.md`의 운영 팁 섹션으로 통합 검토 |
| `docs/wiki/how-to-run-demo-mode.md` | demo 모드 자체가 더 이상 존재하지 않음. | 코드 확인 후 재작성 또는 삭제 |

### 1.2 현재 아키텍처와 대조 검증 필요

| 파일 | 확인할 것 |
|------|-----------|
| `docs/wiki/introduce.md` | 프로젝트 소개가 현재 AI Agent 구조(SystemOperator / SessionManager / TradingOperator)를 반영하는지 |
| `docs/wiki/SMTM_프로젝트_소개.md` | 위와 동일 |
| `docs/wiki/how-to-test.md` | 테스트 분류(unit / e2e / integration)와 실행 명령이 현재와 맞는지 |

`docs/wiki/architecture.md`의 레이어 표는 이번에 `TelegramController, JptController`로 갱신했지만,
같은 문서의 컴포넌트/클래스/시퀀스 다이어그램 이미지는 여전히 구버전입니다. 함께 재생성해야 합니다.

---

## 2. 손대지 않기로 한 문서

- `docs/claw-branch-review.md` - 특정 시점의 리뷰를 기록한 **역사적 문서**입니다. 당시 상태를 그대로 남겨두는 것이 목적이므로 갱신하지 않습니다.
- `RELEASE_NOTES.md`, `docs/public/release-notes.md` - 릴리스 기록이므로 과거 항목은 수정하지 않습니다.
- `docs/superpowers/**` - 스펙/계획 문서로 역사적 기록입니다.
