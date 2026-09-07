import DrugDemo from "@/components/DrugDemo";

const FEATURES = [
  {
    tag: "상호작용 확인",
    title: "이 약들, 같이 먹어도 될까요?",
    body: "여러 약을 함께 복용할 때 위험한 조합을 식약처 공식 데이터(DUR)로 확인해드려요. 병용금기부터 성분 중복까지.",
    href: "#",
  },
  {
    tag: "약물 정보",
    title: "쉬운 말로 읽는 약 이야기",
    body: "함께 먹으면 안 되는 약, 겹치면 위험한 성분처럼 꼭 필요한 정보를 어려운 용어 없이 전해드려요.",
    href: "#",
  },
  {
    tag: "약국·병원 찾기",
    title: "가까운 곳에서 상담하기",
    body: "주의가 필요한 조합이 나오면, 가장 가까운 약국·병원을 지도에서 찾아 바로 상담하러 갈 수 있어요.",
    href: "#",
  },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16 sm:py-24">
      {/* 헤더 */}
      <header className="mb-20 flex items-center justify-between">
        <span className="text-lg font-semibold tracking-tight text-teal-deep">
          필체크
        </span>
        <a
          href="#start"
          className="rounded-full bg-teal px-5 py-2.5 text-base font-medium text-white hover:bg-teal-deep"
        >
          시작하기
        </a>
      </header>

      {/* 히어로 */}
      <section className="mb-16">
        <p className="rise mb-6 inline-block rounded-full bg-teal-soft px-4 py-2 text-base font-medium text-teal-deep">
          여러 약을 드시는 분을 위한 약물 상호작용 확인
        </p>
        <h1 className="rise-2 max-w-3xl text-4xl font-bold leading-tight tracking-tight text-ink sm:text-6xl">
          여러 약, 같이 먹어도
          <br />
          <span className="text-teal">괜찮을까요?</span>
        </h1>
        <p className="rise-3 mt-6 max-w-2xl text-xl leading-relaxed text-ink/70">
          여러 약을 먹어도 괜찮은지, 뭘 먹으면 좋을지 — 어렵게 찾아보지 마세요.
          식약처 공식 데이터를 바탕으로 쉽게 안내해드립니다.
        </p>
        <div className="rise-3 mt-8 flex flex-wrap gap-4" id="start">
          <a
            href="#"
            className="rounded-full bg-teal px-7 py-4 text-lg font-medium text-white hover:bg-teal-deep"
          >
            약 상담 시작하기
          </a>
          <a
            href="#features"
            className="rounded-full border-2 border-teal/30 px-7 py-4 text-lg font-medium text-teal-deep hover:border-teal"
          >
            무엇을 도와주나요?
          </a>
        </div>
      </section>

      {/* 시그니처: 인터랙티브 데모 */}
      <section className="mb-24">
        <DrugDemo />
      </section>

      {/* 기능 소개 */}
      <section id="features" className="mb-24">
        <h2 className="mb-10 text-3xl font-bold tracking-tight text-ink">
          이런 걸 도와드려요
        </h2>
        <div className="grid gap-6 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <a
              key={f.tag}
              href={f.href}
              className="group rounded-2xl border border-teal/15 bg-white p-7 transition hover:border-teal/40 hover:shadow-md"
            >
              <span className="text-sm font-semibold uppercase tracking-wide text-teal">
                {f.tag}
              </span>
              <h3 className="mt-3 text-xl font-bold leading-snug text-ink">
                {f.title}
              </h3>
              <p className="mt-3 text-base leading-relaxed text-ink/65">
                {f.body}
              </p>
              <span className="mt-4 inline-block text-base font-medium text-teal group-hover:underline">
                자세히 보기 →
              </span>
            </a>
          ))}
        </div>
      </section>

      {/* 타겟 */}
      <section className="mb-24 rounded-3xl bg-teal-deep px-8 py-14 text-white sm:px-14">
        <h2 className="text-3xl font-bold tracking-tight">
          이런 분들께 특히 도움이 됩니다
        </h2>
        <div className="mt-8 grid gap-8 sm:grid-cols-2">
          <div>
            <p className="text-xl font-semibold text-teal-soft">
              여러 약을 드시는 어르신
            </p>
            <p className="mt-2 text-lg leading-relaxed text-white/80">
              혈압약, 당뇨약, 진통제… 함께 먹어도 괜찮은지 큰 글씨와 쉬운 말로
              확인해드려요.
            </p>
          </div>
          <div>
            <p className="text-xl font-semibold text-teal-soft">
              바쁜 직장인
            </p>
            <p className="mt-2 text-lg leading-relaxed text-white/80">
              역류·불면·통풍이 걱정된다면, 회식·야근 속에서 뭘 피하고 뭘 고를지
              알려드려요.
            </p>
          </div>
        </div>
      </section>

      {/* 고지 */}
      <section className="mb-16 rounded-2xl border border-amber/30 bg-amber/5 p-6">
        <p className="text-base leading-relaxed text-ink/70">
          <span className="font-semibold text-amber">참고 안내</span> · 본 서비스는
          의료기기가 아니며 진단·처방을 하지 않습니다. 식약처 공식 데이터를 조회해
          안내하는 참고용 서비스이며, 데이터베이스에 없다고 해서 안전한 것은 아닙니다.
          복용 전 반드시 의사·약사와 상담하세요.
        </p>
      </section>

      {/* 푸터 */}
      <footer className="border-t border-teal/15 pt-8 text-base text-ink/50">
        <p>필체크(PillCheck) · 약물 상호작용 확인 서비스</p>
        <p className="mt-1">상호작용 확인 · 약물 정보 · 약국·병원 찾기 · 음성 안내</p>
      </footer>
    </main>
  );
}
