import {
  forwardRef,
  useEffect,
  useId,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { searchCatalogIndex } from "../lib/catalogSearch";
import { normalizeSearchText, searchMatchRange } from "../lib/searchText";
import type { SearchSuggestion } from "../types";
import { CategoryIcon, DesignIcon } from "./DesignIcon";
export type SearchComboboxHandle = { submit: () => void };
function Highlight({ text, query }: { text: string; query: string }) {
  const range = searchMatchRange(text, query);
  return range ? (
    <>
      {text.slice(0, range[0])}
      <mark>{text.slice(range[0], range[1])}</mark>
      {text.slice(range[1])}
    </>
  ) : (
    <>{text}</>
  );
}
export const SearchCombobox = forwardRef<
  SearchComboboxHandle,
  {
    value: string;
    onChange: (next: string) => void;
    onUnifiedSearch?: (query: string, results: SearchSuggestion[]) => void;
    onUnifiedSearchStart?: (query: string) => void;
    onUnifiedSearchError?: (query: string) => void;
    onClearSubmitted?: () => void;
  }
>(function SearchCombobox({ value, onChange }, ref) {
  const id = useId();
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  const wrapper = useRef<HTMLDivElement>(null);
  const [results, setResults] = useState<SearchSuggestion[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [retry, setRetry] = useState(0);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const sequence = useRef(0);
  const query = normalizeSearchText(value);
  useEffect(() => {
    const version = ++sequence.current;
    const controller = new AbortController();
    if (query.length < 2) {
      setResults([]);
      setOpen(false);
      setStatus("idle");
      setActive(-1);
      return;
    }
    setResults([]);
    setStatus("loading");
    setOpen(true);
    const timer = window.setTimeout(() => {
      void api
        .searchIndex()
        .then((payload) => {
          if (version !== sequence.current) return;
          setResults(searchCatalogIndex(payload, query));
          setStatus("ready");
          setActive(-1);
        })
        .catch(async (error) => {
          if (version !== sequence.current) return;
          if (error.name === "AbortError") return;
          // Keep search available during an index or CDN outage.
          try {
            const payload = await api.searchSuggestions(query, controller.signal);
            if (version !== sequence.current) return;
            setResults([
              ...payload.results.filter((item) => item.type === "point"),
              ...payload.results.filter((item) => item.type === "route"),
            ]);
            setStatus("ready");
          } catch (fallbackError) {
            if (version !== sequence.current || (fallbackError as { name?: string }).name === "AbortError") return;
            setStatus("error");
          }
        });
    }, 120);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, retry]);
  useEffect(() => {
    const outside = (e: PointerEvent) => {
      if (!wrapper.current?.closest("form")?.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, []);
  function submit() {
    if (query.length >= 2) {
      setOpen(true);
      input.current?.focus({ preventScroll: true });
    }
  }
  useImperativeHandle(ref, () => ({ submit }), [query]);
  return (
    <div className="search-combobox" ref={wrapper}>
      <label className="sr-only" htmlFor={id}>
        جست‌وجوی مقصد و مسیر
      </label>
      <input
        ref={input}
        id={id}
        role="combobox"
        type="search"
        aria-label="جست‌وجوی مقصد و مسیر"
        aria-expanded={open}
        aria-controls={`${id}-results`}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${id}-${active}` : undefined}
        autoComplete="off"
        placeholder="مقصد یا مسیرت را پیدا کن"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => {
          if (query.length >= 2) setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.preventDefault();
            setOpen(false);
            setActive(-1);
          }
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            setOpen(true);
            if (!results.length) return;
            setActive((i) =>
              e.key === "ArrowDown"
                ? (i + 1) % results.length
                : i <= 0
                  ? results.length - 1
                  : i - 1,
            );
          }
          if (e.key === "Enter") {
            e.preventDefault();
            if (open && active >= 0 && results[active]) {
              navigate(results[active].href);
              setOpen(false);
            } else submit();
          }
        }}
      />
      {open ? (
        <div className="home-search-panel">
          <div className="search-result-header">
            <span>نتایج جست‌وجو</span>
            <span role="status">
              {results.length.toLocaleString("fa-IR")} نتیجه
            </span>
          </div>
          {status === "loading" ? (
            <p className="search-combobox-status" role="status">
              در حال جست‌وجو…
            </p>
          ) : null}
          {status === "error" ? (
            <p className="search-combobox-status" role="alert">
              جست‌وجو ناموفق بود.{" "}
              <button
                type="button"
                className="outline-button"
                onClick={() => setRetry((value) => value + 1)}
              >
                تلاش دوباره
              </button>
            </p>
          ) : null}
          {status === "ready" && !results.length ? (
            <div className="search-no-match">
              <strong>نتیجه‌ای پیدا نشد</strong>
              <p>نام مقصد یا مسیر دیگری را امتحان کن.</p>
              <button
                type="button"
                className="outline-button"
                onClick={() => onChange("")}
              >
                پاک کردن جست‌وجو
              </button>
            </div>
          ) : null}
          <div
            className="search-result-list"
            id={`${id}-results`}
            role="listbox"
            aria-label="نتایج مقصد و مسیر"
          >
            {(["point", "route"] as const).map((type) => {
              const group = results.filter((r) => r.type === type);
              if (!group.length) return null;
              return (
                <section
                  key={type}
                  role="group"
                  aria-label={type === "point" ? "مقصدها" : "مسیرها"}
                >
                  <h2 className="search-group-title">
                    {type === "point" ? "مقصدها" : "مسیرها"} ·{" "}
                    {group.length.toLocaleString("fa-IR")}
                  </h2>
                  {group.map((item) => {
                    const index = results.indexOf(item);
                    return (
                      <Link
                        key={item.href}
                        to={item.href}
                        id={`${id}-${index}`}
                        className={`search-result ${index === active ? "is-active" : ""}`}
                        role="option"
                        aria-selected={index === active}
                        onMouseEnter={() => setActive(index)}
                        onClick={() => setOpen(false)}
                      >
                        {type === "route" ? (
                          <DesignIcon
                            name="category-route"
                            className="category-icon"
                          />
                        ) : (
                          <CategoryIcon
                            category={item.category_key}
                            placeType={item.place_type}
                          />
                        )}
                        <span className="search-result-copy">
                          <strong>
                            <Highlight text={item.label} query={value} />
                          </strong>
                          <small>{item.hint}</small>
                        </span>
                        <DesignIcon name="chevron-left" />
                      </Link>
                    );
                  })}
                </section>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
});
