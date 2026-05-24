from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import httpx

try:
    import fitz
except Exception:  # pragma: no cover
    fitz = None

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from parsers.excel_parser import BALANCE_SHEET_MAP, CASH_FLOW_MAP, INCOME_STATEMENT_MAP


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_MAX_LOG_LINES = 800


class _BoundedLinesHandler(logging.FileHandler):
    """FileHandler that keeps only the last N lines by trimming from the start."""

    def __init__(self, filename, max_lines: int = _MAX_LOG_LINES, **kwargs):
        super().__init__(filename, **kwargs)
        self.max_lines = max_lines
        self._write_count = 0

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self._write_count += 1
        if self._write_count != 1 and self._write_count % 50 != 0:
            return
        try:
            with open(self.baseFilename, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > self.max_lines:
                with open(self.baseFilename, "w", encoding="utf-8") as f:
                    f.writelines(lines[-self.max_lines:])
        except OSError:
            pass


logger = logging.getLogger("pdf_parser")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = _BoundedLinesHandler(LOG_DIR / "pdf_parser.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    # Trim existing file on startup if it already exceeds the limit.
    log_path = LOG_DIR / "pdf_parser.log"
    try:
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > _MAX_LOG_LINES:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.writelines(lines[-_MAX_LOG_LINES:])
    except OSError:
        pass


NUM_TOKEN_RE = re.compile(r"\(?-?\d[\d,，]*(?:\.\d+)?\)?\s*(?:万元|千元|万股|万|元)?")
FIELD_CHUNK_SIZE = 18
MAX_CANDIDATE_PAGES_PER_STATEMENT = 12
MAX_LEGACY_SCAN_PAGES_PER_BATCH = 10


STATEMENT_RULES = {
    "balance_sheet": {
        "titles": ["资产负债表", "合并资产负债表"],
        "anchors": ["资产总计", "负债合计", "所有者权益"],
    },
    "income_statement": {
        "titles": ["利润表", "合并利润表"],
        "anchors": ["营业收入", "营业利润", "净利润"],
    },
    "cash_flow": {
        "titles": ["现金流量表", "合并现金流量表"],
        "anchors": ["经营活动", "投资活动", "筹资活动"],
    },
}


def _page_text(page: Any, max_chars: int = 8000) -> str:
    text = page.get_text("text") or ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _extract_json_block(text: str) -> Dict:
    if not text:
        return {}

    # Prefer fenced JSON blocks when model wraps output in markdown.
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # Try JSON decoder from each '{' position to avoid greedy regex failures.
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return {}


def _numeric_token_count(text: str) -> int:
    return len(re.findall(r"(?<!\d)-?\d[\d,，]*(?:\.\d+)?", text))


def _money_like_count(text: str) -> int:
    # Financial tables usually have comma-grouped or decimal amounts; TOC pages usually do not.
    return len(re.findall(r"\d{1,3}(?:[,，]\d{3})+(?:\.\d+)?|\d+\.\d{2}", text))


def _normalize_item_name(text: str) -> str:
    return re.sub(r"[\s\u3000:：·•\-—\(\)（）\[\]]+", "", text or "")


def _is_toc_like(text: str) -> bool:
    head = text[:500]
    dot_leader_count = len(re.findall(r"[.．·]{4,}", head))
    return "目录" in head and (dot_leader_count >= 1 or _money_like_count(head) < 3)


def _detect_unit_multiplier(text: str) -> float:
    sample = text[:900]
    if re.search(r"单位[：:：]?\s*(人民币)?\s*千元", sample):
        return 1000.0
    if re.search(r"单位[：:：]?\s*(人民币)?\s*万元", sample):
        return 10000.0
    if re.search(r"金额单位[：:：]?\s*(人民币)?\s*万元", sample):
        return 10000.0
    return 1.0


def _chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _extract_first_number_after_name(line: str, item_name: str, default_multiplier: float = 1.0) -> float | None:
    idx = line.find(item_name)
    tail = line[idx + len(item_name):] if idx >= 0 else line
    candidates = NUM_TOKEN_RE.findall(tail)
    if not candidates:
        return None
    parsed: List[Tuple[str, float]] = [(token, _normalize_number(token, default_multiplier=default_multiplier)) for token in candidates]

    # When multi-column PDF tables show 本期 vs 上期 side by side, prefer the
    # number closest to the "本期" marker (i.e. the current period column).
    if "本期" in tail:
        benqi_idx = tail.index("本期")
        best, best_dist = None, float("inf")
        for token, value in parsed:
            compact = token.strip()
            if not compact:
                continue
            token_idx = tail.index(compact) if compact in tail else -1
            if token_idx >= 0 and token_idx < benqi_idx:
                dist = benqi_idx - token_idx
                if dist < best_dist:
                    best, best_dist = value, dist
        if best is not None and best != 0.0:
            return best

    # Prefer tokens that look like real money amounts over tiny note indexes.
    for token, value in parsed:
        compact = token.strip()
        amount_like = any(mark in compact for mark in [",", "，", ".", "万元", "千元", "万", "元"])
        raw_magnitude = abs(_normalize_number(token, default_multiplier=1.0))
        if value != 0.0 and (amount_like or raw_magnitude >= 1000):
            return value

    return None


def _normalize_number(value, default_multiplier: float = 1.0):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) * default_multiplier
    text = str(value).strip()
    if not text:
        return 0.0
    negative = text.startswith("(") and text.endswith(")")
    original = text
    text = text.replace(",", "").replace("，", "")
    text = text.replace("(", "").replace(")", "")
    if "万元" in original or ("万" in original and "万股" not in original):
        multiplier = 10000.0
    elif "千元" in original:
        multiplier = 1000.0
    elif "元" in original or "万股" in original:
        multiplier = 1.0
    else:
        multiplier = default_multiplier
    text = text.replace("万元", "").replace("千元", "").replace("万股", "").replace("万", "").replace("元", "")
    try:
        num = float(text) * multiplier
    except ValueError:
        return 0.0
    return -num if negative else num


class PDFParser:
    def __init__(self) -> None:
        self.enabled = bool(DEEPSEEK_API_KEY)
        logger.info("PDFParser initialized: deepseek_enabled=%s base_url=%s model=%s", self.enabled, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL)

    def _chat_completion(self, prompt: str, max_tokens: int) -> str:
        endpoint = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
        start = time.time()
        try:
            response = httpx.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = e.response.text[:1200] if e.response is not None else ""
            logger.error("DeepSeek HTTP error: status=%s body=%s", e.response.status_code if e.response is not None else "unknown", body)
            raise
        logger.info("DeepSeek request ok: endpoint=%s max_tokens=%s elapsed=%.2fs", endpoint, max_tokens, time.time() - start)
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _find_statement_pages(self, doc: Any) -> Dict[str, List[int]]:
        started = time.time()
        local_candidates = self._candidate_statement_pages(doc)
        logger.info("Local statement candidates: %s", local_candidates)

        if not self.enabled:
            logger.warning("DeepSeek disabled, using local candidate page detection")
            result = self._expand_adjacent_pages(doc, self._refine_statement_pages(doc, local_candidates))
            logger.info("Detected statement pages without DeepSeek: %s elapsed=%.2fs", result, time.time() - started)
            return result

        if any(local_candidates.values()):
            result = {key: [] for key in STATEMENT_RULES.keys()}
            for key, candidates in local_candidates.items():
                if not candidates:
                    continue
                selected = self._ai_select_pages_for_statement(doc, key, candidates)
                result[key] = selected or candidates[:5]
            result = self._refine_statement_pages(doc, result)
            result = self._expand_adjacent_pages(doc, result)
            missing = [key for key, page_list in result.items() if not page_list]
            if missing:
                logger.warning("Candidate detection missed statements=%s, supplementing with legacy scan", missing)
                legacy = self._legacy_ai_find_statement_pages(doc)
                for key in missing:
                    if legacy.get(key):
                        result[key] = legacy[key]
            logger.info("Detected statement pages from candidates: %s elapsed=%.2fs", result, time.time() - started)
            return result

        logger.warning("No local statement candidates found, falling back to legacy DeepSeek page scan")
        result = self._legacy_ai_find_statement_pages(doc)
        logger.info("Detected statement pages from legacy scan: %s elapsed=%.2fs", result, time.time() - started)
        return result

    def _legacy_ai_find_statement_pages(self, doc: Any) -> Dict[str, List[int]]:
        result = {"balance_sheet": [], "income_statement": [], "cash_flow": []}
        for start in range(0, len(doc), MAX_LEGACY_SCAN_PAGES_PER_BATCH):
            page_snippets = []
            for i in range(start, min(start + MAX_LEGACY_SCAN_PAGES_PER_BATCH, len(doc))):
                page_snippets.append(f"[页码:{i + 1}]\n{_page_text(doc[i], max_chars=5000)}")
            prompt = (
                "识别本批页面中合并资产负债表、合并利润表、合并现金流量表所在页码。"
                "页码按整个文档从1开始计数，返回JSON:"
                '{"balance_sheet":[...],"income_statement":[...],"cash_flow":[...]}'
                "\n\n以下是页面文本：\n"
                + "\n\n".join(page_snippets)
            )
            try:
                text = self._chat_completion(prompt, max_tokens=800)
            except Exception as e:
                logger.exception("Find statement pages failed for chunk_start=%s: %s", start + 1, e)
                continue
            data = _extract_json_block(text)
            logger.info("Page detection chunk=%s json_keys=%s", start // 10 + 1, list(data.keys()))
            for key in result.keys():
                result[key].extend([int(x) for x in data.get(key, []) if isinstance(x, (int, float))])
        for key in result.keys():
            result[key] = sorted(set(result[key]))
        if not any(result.values()):
            logger.warning("No pages detected by DeepSeek, fallback to heuristic page detection")
            return self._heuristic_find_pages(doc)
        result = self._refine_statement_pages(doc, result)
        result = self._expand_adjacent_pages(doc, result)
        return result

    def _candidate_statement_pages(self, doc: Any) -> Dict[str, List[int]]:
        scored: Dict[str, List[Tuple[float, int]]] = {key: [] for key in STATEMENT_RULES.keys()}
        for i in range(len(doc)):
            raw_text = doc[i].get_text("text") or ""
            text = re.sub(r"\s+", " ", raw_text).strip()
            if not text or _is_toc_like(text):
                continue
            for key in STATEMENT_RULES.keys():
                score = self._score_statement_page(key, text)
                if score >= 7.0:
                    scored[key].append((score, i + 1))

        candidates: Dict[str, List[int]] = {}
        for key, rows in scored.items():
            rows.sort(key=lambda x: (-x[0], x[1]))
            candidates[key] = sorted({page for _score, page in rows[:MAX_CANDIDATE_PAGES_PER_STATEMENT]})
        return candidates

    def _score_statement_page(self, key: str, text: str) -> float:
        rules = STATEMENT_RULES.get(key, {})
        titles = rules.get("titles", [])
        anchors = rules.get("anchors", [])
        head = text[:500]
        score = 0.0

        exact_title = titles[-1] if titles else ""
        if exact_title and exact_title in head:
            score += 10.0
        elif any(t in head for t in titles):
            score += 7.0
        elif any(t in text for t in titles):
            score += 6.0

        score += sum(1 for anchor in anchors if anchor in text) * 2.2
        if "单位" in head or "金额单位" in head:
            score += 1.2
        score += min(_numeric_token_count(text) / 30.0, 4.0)
        score += min(_money_like_count(text) / 10.0, 4.0)

        if "母公司" in head:
            score -= 6.0
        if "附注" in head and not any(t in head for t in titles):
            score -= 2.0
        return score

    def _ai_select_pages_for_statement(self, doc: Any, key: str, candidates: List[int]) -> List[int]:
        rules = STATEMENT_RULES.get(key, {})
        label = rules.get("titles", [key])[-1]
        page_snippets = []
        for page_no in candidates:
            if page_no < 1 or page_no > len(doc):
                continue
            page_snippets.append(f"[页码:{page_no}]\n{_page_text(doc[page_no - 1], max_chars=4200)}")
        if not page_snippets:
            return []

        prompt = (
            f"下面是本地规则从年报中筛出的候选页。请只判断哪些页是真正的{label}。"
            "优先选择合并报表，排除目录、附注索引页、母公司报表。"
            "如果该表跨页，可以返回多个页码；只能返回候选页中的页码。"
            '返回JSON: {"pages":[...]}\n\n'
            + "\n\n".join(page_snippets)
        )
        try:
            text = self._chat_completion(prompt, max_tokens=500)
        except Exception as e:
            logger.exception("AI candidate page selection failed statement=%s candidates=%s error=%s", key, candidates, e)
            return []

        data = _extract_json_block(text)
        raw_pages = data.get("pages") or data.get(key) or []
        selected = sorted({
            int(x)
            for x in raw_pages
            if isinstance(x, (int, float)) and int(x) in candidates
        })
        logger.info("AI selected pages statement=%s candidates=%s selected=%s", key, candidates, selected)
        return selected

    def _refine_statement_pages(self, doc: Any, pages: Dict[str, List[int]]) -> Dict[str, List[int]]:
        refined: Dict[str, List[int]] = {"balance_sheet": [], "income_statement": [], "cash_flow": []}
        for key, candidates in pages.items():
            rules = STATEMENT_RULES.get(key, {})
            titles = rules.get("titles", [])
            anchors = rules.get("anchors", [])
            scored: List[tuple[float, int]] = []

            for p in candidates:
                if p < 1 or p > len(doc):
                    continue
                raw_text = doc[p - 1].get_text("text") or ""
                text = re.sub(r"\s+", " ", raw_text)
                text_head = text[:180]
                num_count = _numeric_token_count(text)
                money_count = _money_like_count(text)
                dot_leader_count = len(re.findall(r"[.．·]{4,}", text))

                # Table of contents pages often contain the title words but little numeric table content.
                if "目录" in text_head and (money_count < 3 or dot_leader_count >= 2):
                    continue

                score = 0.0
                exact_title = titles[-1] if titles else ""
                if exact_title and exact_title in text:
                    score += 10.0
                elif any(t in text for t in titles):
                    score += 6.0
                score += sum(1 for a in anchors if a in text) * 2.0
                if "单位" in text:
                    score += 1.0
                score += min(num_count / 25.0, 4.0)
                score += min(money_count / 8.0, 4.0)

                if "母公司" in text_head:
                    score -= 6.0
                if dot_leader_count >= 2:
                    score -= 4.0

                # Guardrail: very likely non-table pages.
                if money_count < 2 and "单位" not in text:
                    continue

                if score >= 5.0:
                    scored.append((score, p))

            scored.sort(key=lambda x: (-x[0], x[1]))
            refined[key] = sorted(p for _, p in scored[:5])

            if not refined[key] and candidates:
                # Keep one original candidate as a last resort to avoid empty extraction.
                refined[key] = [min(candidates)]

        logger.info("Refined statement pages: before=%s after=%s", pages, refined)
        return refined

    def _expand_adjacent_pages(self, doc: Any, pages: Dict[str, List[int]]) -> Dict[str, List[int]]:
        """Include pages immediately after each statement's last page when they
        contain spillover rows (financial numbers) and don't start another statement.

        A page assigned to another statement may still be included if that other
        statement's title does not appear in the page head (first 200 chars),
        meaning the current statement's content spills over into that page."""
        original_pages: Dict[int, str] = {}
        for key, page_list in pages.items():
            for p in page_list:
                original_pages[p] = key

        other_titles: Dict[str, List[str]] = {}
        for stmt_key, rules in STATEMENT_RULES.items():
            other_titles[stmt_key] = []
            for other_key, other_rules in STATEMENT_RULES.items():
                if other_key != stmt_key:
                    other_titles[stmt_key].extend(other_rules.get("titles", []))

        expanded: Dict[str, List[int]] = {}
        for key, page_list in pages.items():
            if not page_list:
                expanded[key] = []
                continue
            page_set = set(page_list)
            last_page = max(page_list)

            for p in range(last_page + 1, min(last_page + 3, len(doc) + 1)):
                text = doc[p - 1].get_text("text") or ""
                text_head = text[:200]
                money_count = _money_like_count(text)

                # Hard stop: page head starts with another statement's title.
                if any(t in text_head for t in other_titles.get(key, [])):
                    break

                # If this page belongs to another statement, only add it when
                # the other statement's title is NOT in the page head (spillover).
                if p in original_pages and original_pages[p] != key:
                    other_rules = STATEMENT_RULES.get(original_pages[p], {})
                    other_titles_list = other_rules.get("titles", [])
                    if not any(t in text_head for t in other_titles_list):
                        if money_count >= 2:
                            page_set.add(p)
                    break

                if money_count >= 2:
                    page_set.add(p)
                else:
                    break

            expanded[key] = sorted(page_set)

        if expanded != pages:
            logger.info("Expanded statement pages: before=%s after=%s", pages, expanded)
        return expanded

    def _heuristic_find_pages(self, doc: Any) -> Dict[str, List[int]]:
        mapping = {
            "balance_sheet": ["资产负债表", "合并资产负债表"],
            "income_statement": ["利润表", "合并利润表"],
            "cash_flow": ["现金流量表", "合并现金流量表"],
        }
        out = {"balance_sheet": [], "income_statement": [], "cash_flow": []}
        for i in range(len(doc)):
            text = doc[i].get_text("text")
            for key, kws in mapping.items():
                if any(k in text for k in kws):
                    out[key].append(i + 1)
        return out

    def _extract_statement_data(self, doc: Any, pages: List[int], statement_map: Dict[str, str]) -> Dict[str, float]:
        if not pages:
            logger.info("No pages passed for statement extraction, skip")
            return {}

        started = time.time()
        heuristic = self._heuristic_extract(doc, pages, statement_map)
        if not self.enabled:
            logger.warning("DeepSeek disabled, using heuristic data extraction")
            logger.info(
                "Extracted statement fields without DeepSeek: requested=%s heuristic=%s non_zero=%s elapsed=%.2fs",
                len(statement_map),
                len(heuristic),
                sum(1 for v in heuristic.values() if v != 0.0),
                time.time() - started,
            )
            return heuristic

        parsed: Dict[str, float] = {}
        chinese_items = list(statement_map.keys())
        page_texts: List[str] = []
        for p in pages:
            page_texts.append(f"[页码:{p}]\n{_page_text(doc[p - 1], max_chars=5200)}")

        for chunk_index, item_chunk in enumerate(_chunked(chinese_items, FIELD_CHUNK_SIZE), start=1):
            prompt = (
                "你正在从中国上市公司财报表格中提取本期金额。"
                "只提取下面列出的科目，返回严格JSON，key必须是中文科目名，value为元金额或null。"
                "请处理括号负数、千分位，并把万元/千元转换为元，即value必须是元口径；不要输出解释。\n"
                + "\n".join(item_chunk)
                + "\n\n以下是候选页面文本：\n"
                + "\n\n".join(page_texts)
            )
            try:
                text = self._chat_completion(prompt, max_tokens=1400)
            except Exception as e:
                logger.exception("Statement extraction chunk failed chunk=%s pages=%s error=%s", chunk_index, pages, e)
                continue

            raw = _extract_json_block(text)
            if not raw:
                logger.warning("LLM extraction chunk no-json chunk=%s preview=%s", chunk_index, (text or "")[:500].replace("\n", " "))
                continue

            raw_by_normalized_key = {_normalize_item_name(str(k)): v for k, v in raw.items()}
            for cn in item_chunk:
                field = statement_map[cn]
                raw_val = raw.get(cn)
                if raw_val is None:
                    raw_val = raw_by_normalized_key.get(_normalize_item_name(cn))
                if raw_val in (None, "", "null", "None", "-", "--"):
                    continue
                parsed[field] = _normalize_number(raw_val)

        llm_non_zero = sum(1 for v in parsed.values() if v != 0.0)
        if llm_non_zero == 0:
            logger.warning("LLM parsed zero/empty fields for pages=%s", pages)

        merged = dict(parsed)
        replaced_zero = 0
        filled_missing = 0
        conflict_count = 0
        for field, hv in heuristic.items():
            if field not in merged:
                merged[field] = hv
                filled_missing += 1
                continue
            if merged[field] == 0.0 and hv != 0.0:
                merged[field] = hv
                replaced_zero += 1
            elif hv != 0.0 and merged[field] != 0.0:
                diff_ratio = abs(merged[field] - hv) / max(abs(hv), 1.0)
                if diff_ratio > 0.2:
                    conflict_count += 1
                    logger.warning("LLM/heuristic value conflict field=%s llm=%s heuristic=%s diff_ratio=%.2f", field, merged[field], hv, diff_ratio)

        non_zero = sum(1 for v in merged.values() if v != 0.0)
        logger.info(
            "Extracted statement fields: requested=%s llm_parsed=%s heuristic=%s filled_missing=%s replaced_zero=%s conflicts=%s merged_non_zero=%s elapsed=%.2fs",
            len(statement_map),
            len(parsed),
            len(heuristic),
            filled_missing,
            replaced_zero,
            conflict_count,
            non_zero,
            time.time() - started,
        )
        return merged

    def _heuristic_extract(self, doc: Any, pages: List[int], statement_map: Dict[str, str]) -> Dict[str, float]:
        result: Dict[str, float] = {}
        normalized_map = {_normalize_item_name(name): (name, field) for name, field in statement_map.items()}
        for p in pages:
            text = doc[p - 1].get_text("text")
            unit_multiplier = _detect_unit_multiplier(text)
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                line_norm = _normalize_item_name(line)
                for norm_name, (cn, field) in normalized_map.items():
                    if field in result:
                        continue
                    if norm_name not in line_norm:
                        continue
                    value = _extract_first_number_after_name(line, cn, default_multiplier=unit_multiplier)
                    if value is not None:
                        result[field] = value
            # Fallback: cross-line global match on full page text for still-missing items.
            for cn, field in statement_map.items():
                if field in result:
                    continue
                compact_text = re.sub(r"\s+", " ", text)
                idx = compact_text.find(cn)
                if idx >= 0:
                    value = _extract_first_number_after_name(compact_text[idx:idx + 350], cn, default_multiplier=unit_multiplier)
                    if value is not None:
                        result[field] = value
                        continue
                # Second fallback: whitespace-insensitive search (handles line-breaks
                # inside item names, e.g. "扣除\n非经常性损益的净利润").
                ws_pattern = r"\s*".join(re.escape(c) for c in cn)
                m = re.search(ws_pattern, compact_text)
                if m:
                    synthetic = cn + compact_text[m.end():]
                    value = _extract_first_number_after_name(synthetic, cn, default_multiplier=unit_multiplier)
                    if value is not None:
                        result[field] = value
        return result


def _log_parse_quality(data: Dict[str, float], pages: Dict[str, List[int]], elapsed: float) -> List[str]:
    total_non_zero = sum(1 for key, value in data.items() if key not in {"company_id", "year", "quarter", "report_type"} and value != 0.0)
    logger.info("PDF parse quality: non_zero_fields=%s pages=%s elapsed=%.2fs", total_non_zero, pages, elapsed)
    warnings: List[str] = []

    total_assets = float(data.get("total_assets", 0.0) or 0.0)
    total_liabilities = float(data.get("total_liabilities", 0.0) or 0.0)
    total_equity = float(data.get("total_equity", 0.0) or 0.0)
    if total_assets and total_liabilities and total_equity:
        diff = abs(total_assets - total_liabilities - total_equity)
        ratio = diff / max(abs(total_assets), 1.0)
        if ratio > 0.03:
            msg = f"资产负债表不平: 资产={total_assets:.2f}, 负债={total_liabilities:.2f}, 权益={total_equity:.2f}, 差异={diff:.2f}, 偏差率={ratio*100:.2f}%"
            logger.warning("Balance equation mismatch: %s", msg)
            warnings.append(msg)

    if total_non_zero < 30:
        msg = f"PDF解析字段过少: 仅解析出 {total_non_zero} 个非零字段，可能部分页面未识别"
        logger.warning(msg)
        warnings.append(msg)

    return warnings


parser = PDFParser()


def parse_pdf(file_path: str | Path, company_id: int, year: int, quarter: int = 0) -> tuple[Dict[str, float], List[str]]:
    if fitz is None:
        raise RuntimeError("PyMuPDF 未安装，无法解析 PDF")

    file_path = Path(file_path)
    started = time.time()
    file_size = file_path.stat().st_size if file_path.exists() else 0
    logger.info("Start parse_pdf file=%s size=%s company_id=%s year=%s quarter=%s", file_path, file_size, company_id, year, quarter)
    doc = fitz.open(str(file_path))
    try:
        logger.info("Opened PDF file=%s page_count=%s", file_path, len(doc))
        pages = parser._find_statement_pages(doc)

        data: Dict[str, float] = {}
        data.update(parser._extract_statement_data(doc, pages.get("balance_sheet", []), BALANCE_SHEET_MAP))
        data.update(parser._extract_statement_data(doc, pages.get("income_statement", []), INCOME_STATEMENT_MAP))
        data.update(parser._extract_statement_data(doc, pages.get("cash_flow", []), CASH_FLOW_MAP))

        # Second pass: scan all pages heuristically for still-missing fields.
        # Some fields (e.g. 扣非净利润, total_shares) only appear on summary or
        # notes pages that are not included in statement page detection.
        all_maps = {**BALANCE_SHEET_MAP, **INCOME_STATEMENT_MAP, **CASH_FLOW_MAP}
        missing = {cn: field for cn, field in all_maps.items() if data.get(field, 0.0) == 0.0}
        if missing:
            all_pages = list(range(1, len(doc) + 1))
            filled = parser._heuristic_extract(doc, all_pages, missing)
            filled_count = 0
            for field, value in filled.items():
                if value != 0.0 and not data.get(field):
                    data[field] = value
                    filled_count += 1
            if filled_count:
                logger.info("Post-scan filled %s fields from non-statement pages: %s", filled_count, list(filled.keys()))

        data["company_id"] = company_id
        data["year"] = year
        data["quarter"] = quarter
        data["report_type"] = "annual" if quarter == 0 else "quarterly"
        warnings = _log_parse_quality(data, pages, time.time() - started)
        logger.info("Finish parse_pdf file=%s detected_pages=%s output_fields=%s warnings=%s", file_path, pages, len(data), len(warnings))
        return data, warnings
    finally:
        doc.close()
