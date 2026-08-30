# 08 · SaaS 랜딩 페이지 (완성 코드)

실버케어 플랫폼의 서비스 소개 랜딩 페이지. **바로 실행 가능한 Next.js 앱**입니다.

## 실행 방법

```bash
cd apps/08-saas-landing
npm install       # 처음 한 번
npm run dev       # 개발 서버 → http://localhost:3000
```

빌드/배포:
```bash
npm run build     # 프로덕션 빌드 (통과 확인용)
npm run start     # 빌드된 앱 실행
```

## 구성

- `app/page.tsx` — 메인 랜딩 (히어로 · 데모 · 기능 · 타겟 · 고지)
- `app/layout.tsx` — 레이아웃, 폰트(Pretendard)
- `app/globals.css` — 전역 스타일 · 접근성(포커스, 모션 최소화)
- `components/DrugDemo.tsx` — 시그니처: 약 조합을 눌러보는 인터랙티브 데모
- `tailwind.config.ts` — 색·타이포 토큰 (딥 틸 + 크림 + 앰버)

## 디자인 의도

- **고령자 배려**가 곧 시그니처: 기본 폰트를 크게(18px+), 큰 버튼, 높은 대비
- 색은 신뢰의 청록(teal) + 따뜻한 크림 배경 + 경고용 앰버/코럴
- 히어로 다음에 바로 "약 조합 눌러보기" 데모 → 서비스 가치를 즉시 체감
- 하단에 "의료기기 아님, 참고용" 고지 필수 포함

## Claude Code로 다듬기 (선택)

이미 동작하지만 더 손보고 싶으면 Claude Code에서:
```
이 랜딩페이지의 [히어로 카피 / 색감 / 데모]를 이렇게 바꿔줘: ...
```

## Vercel 배포

```bash
# Vercel CLI 또는 GitHub 연동으로 배포
# 이 폴더를 루트로 지정하면 됩니다.
```
배포 후 이 README 맨 위에 URL을 적어두세요.

## 참고

- 데모(DrugDemo)의 판정은 **미리보기용**입니다. 실제 판정은 10번 챗봇 +
  식약처 DUR이 담당합니다.
- 외부 연동·키가 필요 없는 순수 프런트라 바로 배포됩니다.
