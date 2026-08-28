import { useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { SearchSuggestion } from "../types";

const DEBOUNCE_MS = 200;
const MIN_CHARS = 2;

function normalizeInput(value: string) {
  return value.trim().replace(/\s+/g, " ");
}

export function SearchCombobox({
  value,
  onChange,
  onSubmitQuery,
}: {
  value: string;
  onChange: (next: string) => void;
  onSubmitQuery?: (query: string) => void;
}) {
  const inputId = useId();
  const listId = useId();
  const navigate = useNavigate();
  const [results, setResults] = useState<SearchSuggestion[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const requestId = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const blurTimer = useRef<number | null>(null);

  useEffect(
    () => () => {
      abortRef.current?.abort();
      if (blurTimer.current) window.clearTimeout(blurTimer.current);
    },
    [],
  );

  useEffect(() => {
    const normalized = normalizeInput(value);
    if (normalized.length < MIN_CHARS) {
      abortRef.current?.abort();
      setResults([]);
      setStatus("idle");
      setOpen(false);
      setActiveIndex(-1);
      return;
    }

    const timer = window.setTimeout(() => {
      const currentRequest = ++requestId.current;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setStatus("loading");
      api
        .searchSuggestions(normalized, controller.signal)
        .then((payload) => {
          if (currentRequest !== requestId.current) return;
          setResults(payload.results);
          setStatus("ready");
          setOpen(true);
          setActiveIndex(payload.results.length ? 0 : -1);
        })
        .catch((error) => {
          if (currentRequest !== requestId.current) return;
          if (error instanceof DOMException && error.name === "AbortError") return;
          setStatus(error instanceof ApiError ? "error" : "idle");
          setResults([]);
          setOpen(true);
          setActiveIndex(-1);
        });
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [value]);

  function choose(item: SearchSuggestion) {
    setOpen(false);
    onChange("");
    navigate(item.href);
  }

  function submitFallback() {
    const query = normalizeInput(value);
    if (activeIndex >= 0 && results[activeIndex]) {
      choose(results[activeIndex]);
      return;
    }
    setOpen(false);
    onSubmitQuery?.(query);
  }

  return (
    <div className={`search-combobox ${open ? "is-open" : ""}`}>
      <label className="sr-only" htmlFor={inputId}>
        جست‌وجوی مقصد یا نقطهٔ مسیر
      </label>
      <input
        id={inputId}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
        aria-label="جست‌وجوی مقصد یا نقطهٔ مسیر"
        placeholder="مثلاً توچال، پس‌قلعه یا شیرپلا"
        autoComplete="off"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => {
          if (results.length || status === "loading" || status === "error") setOpen(true);
        }}
        onBlur={() => {
          blurTimer.current = window.setTimeout(() => setOpen(false), 120);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            if (!results.length) return;
            setOpen(true);
            setActiveIndex((index) => (index + 1) % results.length);
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            if (!results.length) return;
            setOpen(true);
            setActiveIndex((index) => (index <= 0 ? results.length - 1 : index - 1));
          } else if (event.key === "Escape") {
            setOpen(false);
            setActiveIndex(-1);
          } else if (event.key === "Enter") {
            event.preventDefault();
            submitFallback();
          }
        }}
      />
      {open ? (
        <div className="search-combobox-panel" role="presentation">
          {status === "loading" ? <p className="search-combobox-status">در حال جست‌وجو…</p> : null}
          {status === "error" ? <p className="search-combobox-status">جست‌وجو ناموفق بود.</p> : null}
          {status === "ready" && !results.length ? (
            <p className="search-combobox-status">نتیجه‌ای پیدا نشد.</p>
          ) : null}
          {results.length ? (
            <ul id={listId} role="listbox" aria-label="پیشنهادهای جست‌وجو">
              {results.map((item, index) => (
                <li
                  key={`${item.type}-${item.slug}`}
                  id={`${listId}-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                  className={index === activeIndex ? "is-active" : ""}
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => choose(item)}
                >
                  <span className="search-result-label">{item.label}</span>
                  <span className="search-result-hint">— {item.hint}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
