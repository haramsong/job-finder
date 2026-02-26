"use client";

import { useState, useEffect, useRef, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const PAGE_SIZE = 20;

const LOCATIONS = [
  "서울", "경기", "인천", "부산", "대구", "대전", "광주", "울산",
  "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
];

const SOURCE_COLORS: Record<string, string> = {
  saramin: "bg-blue-100 text-blue-800",
  jobkorea: "bg-green-100 text-green-800",
  wanted: "bg-purple-100 text-purple-800",
  incruit: "bg-orange-100 text-orange-800",
  linkedin: "bg-sky-100 text-sky-800",
  remember: "bg-pink-100 text-pink-800",
  rallit: "bg-yellow-100 text-yellow-800",
  jumpit: "bg-teal-100 text-teal-800",
};

interface Category { id: string; name: string; core_keywords: string[]; auxiliary_keywords: string[] }

interface Job {
  source: string; company: string; title: string; link: string;
  conditions: string[]; keywords: string[];
  matched_keywords: string[]; excluded_keywords: string[];
}

interface SearchResult { matched: Job[]; excluded: Job[] }

// 모바일 감지 훅
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);
  return isMobile;
}

export default function Home() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedLocations, setSelectedLocations] = useState<string[]>([]);
  const [selectedCore, setSelectedCore] = useState<string[]>([]);
  const [selectedAux, setSelectedAux] = useState<string[]>([]);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [showExcluded, setShowExcluded] = useState(false);
  const [matchedPage, setMatchedPage] = useState(1);
  const [excludedPage, setExcludedPage] = useState(1);
  // 모바일 infinite scroll용
  const [matchedVisible, setMatchedVisible] = useState(PAGE_SIZE);
  const [excludedVisible, setExcludedVisible] = useState(PAGE_SIZE);
  const isMobile = useIsMobile();

  useEffect(() => {
    fetch(`${API_BASE}/api/categories`)
      .then((res) => res.json())
      .then((data: Category[]) => {
        setCategories(data);
        if (data.length > 0) {
          setSelectedCategory(data[0].id);
          setSelectedCore(data[0].core_keywords);
          setSelectedAux(data[0].auxiliary_keywords);
        }
      })
      .catch(() => {});
  }, []);

  const handleCategoryChange = (id: string) => {
    setSelectedCategory(id);
    const cat = categories.find((c) => c.id === id);
    if (cat) { setSelectedCore(cat.core_keywords); setSelectedAux(cat.auxiliary_keywords); }
  };

  const currentCategory = categories.find((c) => c.id === selectedCategory);

  const toggleItem = (list: string[], item: string, setter: (v: string[]) => void) => {
    setter(list.includes(item) ? list.filter((x) => x !== item) : [...list, item]);
  };

  const toggleAll = (all: string[], selected: string[], setter: (v: string[]) => void) => {
    setter(selected.length === all.length ? [] : [...all]);
  };

  const isAllSelected = currentCategory &&
    selectedCore.length === currentCategory.core_keywords.length &&
    selectedAux.length === currentCategory.auxiliary_keywords.length;

  const handleSearch = async () => {
    if (!selectedCategory) return;
    setLoading(true);
    setResult(null);
    setMatchedPage(1);
    setExcludedPage(1);
    setMatchedVisible(PAGE_SIZE);
    setExcludedVisible(PAGE_SIZE);
    const location = selectedLocations.length === 1 ? selectedLocations[0] : undefined;
    const allowedKeywords = isAllSelected ? undefined : [...selectedCore, ...selectedAux];
    try {
      const params = new URLSearchParams({ category: selectedCategory, page_size: "200", crawl_pages: "2" });
      if (location) params.set("location", location);
      if (allowedKeywords) { for (const kw of allowedKeywords) params.append("allowed_keywords", kw); }
      const res = await fetch(`${API_BASE}/api/jobs?${params}`);
      setResult(await res.json());
    } catch {
      alert("검색 실패: 백엔드 서버가 실행 중인지 확인해주세요");
    } finally {
      setLoading(false);
    }
  };

  const paginate = (items: Job[], page: number) => items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const totalPages = (count: number) => Math.max(1, Math.ceil(count / PAGE_SIZE));

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">🔍 Job Finder</h1>

      {/* 검색 영역 */}
      <div className="mb-6 rounded-lg bg-white p-5 shadow-sm">
        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">직군</label>
          <select value={selectedCategory} onChange={(e) => handleCategoryChange(e.target.value)} className="w-full appearance-auto rounded border border-gray-300 px-3 py-2 text-sm">
            {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        {currentCategory && (
          <div className="mb-4">
            <div className="mb-1 flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">핵심 키워드</label>
              <button onClick={() => toggleAll(currentCategory.core_keywords, selectedCore, setSelectedCore)} className="text-xs text-blue-500 hover:underline">
                {selectedCore.length === currentCategory.core_keywords.length ? "전체 해제" : "전체 선택"}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {currentCategory.core_keywords.map((kw) => <Chip key={kw} label={kw} selected={selectedCore.includes(kw)} onClick={() => toggleItem(selectedCore, kw, setSelectedCore)} />)}
            </div>
          </div>
        )}

        {currentCategory && (
          <div className="mb-4">
            <div className="mb-1 flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">보조 키워드</label>
              <button onClick={() => toggleAll(currentCategory.auxiliary_keywords, selectedAux, setSelectedAux)} className="text-xs text-blue-500 hover:underline">
                {selectedAux.length === currentCategory.auxiliary_keywords.length ? "전체 해제" : "전체 선택"}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {currentCategory.auxiliary_keywords.map((kw) => <Chip key={kw} label={kw} selected={selectedAux.includes(kw)} onClick={() => toggleItem(selectedAux, kw, setSelectedAux)} />)}
            </div>
          </div>
        )}

        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">지역</label>
          <div className="flex flex-wrap gap-2">
            {LOCATIONS.map((loc) => <Chip key={loc} label={loc} selected={selectedLocations.includes(loc)} onClick={() => toggleItem(selectedLocations, loc, setSelectedLocations)} />)}
          </div>
        </div>

        <button onClick={handleSearch} disabled={loading || !selectedCategory} className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {loading ? "검색 중..." : "검색"}
        </button>
      </div>

      {/* 결과 */}
      {result && result.matched && (
        <>
          <div className="mb-4 text-sm text-gray-600">
            ✅ 매칭 {result.matched.length}개 | ❌ 제외 {result.excluded.length}개
          </div>

          <h2 className="mb-3 text-lg font-semibold">✅ 매칭 공고</h2>
          <div className="mb-2 grid gap-3">
            {(isMobile ? result.matched.slice(0, matchedVisible) : paginate(result.matched, matchedPage)).map((job, i) => (
              <JobCard key={`m-${i}`} job={job} />
            ))}
            {result.matched.length === 0 && <p className="text-sm text-gray-500">매칭된 공고가 없습니다</p>}
          </div>
          {isMobile ? (
            matchedVisible < result.matched.length && (
              <InfiniteScrollTrigger onVisible={() => setMatchedVisible((v) => v + PAGE_SIZE)} />
            )
          ) : (
            totalPages(result.matched.length) > 1 && (
              <Pagination current={matchedPage} total={totalPages(result.matched.length)} onChange={setMatchedPage} />
            )
          )}

          <button onClick={() => setShowExcluded(!showExcluded)} className="mb-3 mt-6 text-sm font-medium text-gray-500 hover:text-gray-700">
            {showExcluded ? "▼" : "▶"} 제외된 공고 보기 ({result.excluded.length}개)
          </button>

          {showExcluded && (
            <>
              <div className="mb-2 grid gap-3">
                {(isMobile ? result.excluded.slice(0, excludedVisible) : paginate(result.excluded, excludedPage)).map((job, i) => (
                  <JobCard key={`e-${i}`} job={job} excluded />
                ))}
              </div>
              {isMobile ? (
                excludedVisible < result.excluded.length && (
                  <InfiniteScrollTrigger onVisible={() => setExcludedVisible((v) => v + PAGE_SIZE)} />
                )
              ) : (
                totalPages(result.excluded.length) > 1 && (
                  <Pagination current={excludedPage} total={totalPages(result.excluded.length)} onChange={setExcludedPage} />
                )
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

// Infinite scroll 감지 컴포넌트
function InfiniteScrollTrigger({ onVisible }: { onVisible: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const onVisibleRef = useRef(onVisible);
  onVisibleRef.current = onVisible;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) onVisibleRef.current(); },
      { rootMargin: "200px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return <div ref={ref} className="flex justify-center py-4"><span className="text-xs text-gray-400">불러오는 중...</span></div>;
}

function Pagination({ current, total, onChange }: { current: number; total: number; onChange: (p: number) => void }) {
  const start = Math.max(1, current - 2);
  const end = Math.min(total, current + 2);
  const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i);

  return (
    <div className="mb-6 flex items-center justify-center gap-1">
      <button onClick={() => onChange(current - 1)} disabled={current <= 1} className="rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100 disabled:opacity-30">‹</button>
      {start > 1 && (
        <>
          <button onClick={() => onChange(1)} className="rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100">1</button>
          {start > 2 && <span className="px-1 text-xs text-gray-400">…</span>}
        </>
      )}
      {pages.map((p) => (
        <button key={p} onClick={() => onChange(p)} className={`rounded px-2 py-1 text-sm ${p === current ? "bg-blue-600 text-white" : "text-gray-500 hover:bg-gray-100"}`}>{p}</button>
      ))}
      {end < total && (
        <>
          {end < total - 1 && <span className="px-1 text-xs text-gray-400">…</span>}
          <button onClick={() => onChange(total)} className="rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100">{total}</button>
        </>
      )}
      <button onClick={() => onChange(current + 1)} disabled={current >= total} className="rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100 disabled:opacity-30">›</button>
    </div>
  );
}

function Chip({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button type="button" role="checkbox" aria-checked={selected} aria-label={`${label} ${selected ? "선택됨" : "선택 안 됨"}`} onClick={onClick}
      className={`inline-flex cursor-pointer items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition ${selected ? "bg-blue-100 text-blue-700 hover:bg-blue-200" : "bg-gray-100 text-gray-500 hover:bg-gray-200"} focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500`}>
      {label}
      <span className="inline-block w-3 text-center text-[10px]">{selected ? "✓" : "✕"}</span>
    </button>
  );
}

function JobCard({ job, excluded }: { job: Job; excluded?: boolean }) {
  return (
    <a href={job.link} target="_blank" rel="noopener noreferrer" className="block rounded-lg bg-white p-4 shadow-sm transition hover:shadow-md">
      <div className="mb-2 flex items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${SOURCE_COLORS[job.source] || "bg-gray-100 text-gray-800"}`}>{job.source}</span>
        <span className="text-sm text-gray-500">{job.company}</span>
      </div>
      <h3 className="mb-2 text-sm font-semibold leading-snug">{job.title}</h3>
      <div className="flex flex-wrap gap-1">
        {job.matched_keywords.map((kw, i) => <span key={`mk-${i}`} className="rounded bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">{kw}</span>)}
        {excluded && job.excluded_keywords.map((kw, i) => <span key={`ek-${i}`} className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">{kw}</span>)}
      </div>
      {job.conditions.length > 0 && <p className="mt-2 text-xs text-gray-400">{job.conditions.join(" · ")}</p>}
    </a>
  );
}
