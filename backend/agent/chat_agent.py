"""LangGraph ReAct chat agent for the Vinyl Assistant.

Architecture:
    START → agent ──(tool_use)──→ tools → agent (loop, max 3 tool calls)
                 └──(text)──────→ END

Memory:
    PostgresSaver checkpointer — one thread per record (record_<id>) or
    per general-chat session (general_<session_id>).
    Thread history capped at MAX_STORED_MESSAGES to keep Postgres rows small.
    Token budget enforced before every LLM call via trim_messages.

Tools:
    web_search            — Tavily/DuckDuckGo web search
    search_vinyl_prices   — comprehensive pricing + market info
    query_collection      — query the vinyl_records DB table; filters: artist,
                            title, genre, label, catalog_number, barcode,
                            condition, notes (user_notes text search),
                            needs_review, year/value range, user_tag;
                            sort_by/sort_order; count_only for stats;
                            hard-capped at 50 results
                            (db session injected per-request via RunnableConfig)

Config keys (passed per invocation, never stored in checkpoint):
    thread_id       — scopes the checkpoint
    db              — SQLAlchemy Session for query_collection
    record_metadata — current record fields (fresh from DB each request)
"""

import logging
import os
from datetime import datetime, timezone
from typing import Annotated, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

# ── Limits ────────────────────────────────────────────────────────────────
MAX_STORED_MESSAGES = 40  # messages kept in Postgres per thread
TOKEN_BUDGET = 24_000     # max tokens sent to LLM per turn (leaves room for output)


# ── State ─────────────────────────────────────────────────────────────────
def _capped_add_messages(left: list, right: list) -> list:
    """add_messages with a hard cap so Postgres rows stay small."""
    merged = add_messages(left, right)
    if len(merged) <= MAX_STORED_MESSAGES:
        return merged
    return merged[-MAX_STORED_MESSAGES:]


class ChatAgentState(TypedDict):
    messages: Annotated[list, _capped_add_messages]


# ── Shared tool instances (lazy singleton) ────────────────────────────────
_chat_tools = None


def _get_chat_tools():
    global _chat_tools
    if _chat_tools is None:
        from backend.tools import EnhancedChatTools
        _chat_tools = EnhancedChatTools()
    return _chat_tools


# ── Tools ─────────────────────────────────────────────────────────────────
@tool
def web_search(query: str, config: RunnableConfig) -> str:
    """Search the web for information about vinyl records, music history,
    pressings, labels, artists, and collecting tips."""
    try:
        results = _get_chat_tools().search_and_scrape(query, scrape_results=False)
        items = results.get("search_results", [])[:5]
        if not items:
            return "No web results found for that query."
        return "\n\n".join(
            f"**{r['title']}**\n{r.get('content', '')[:300]}" for r in items
        )
    except Exception as e:
        logger.error(f"web_search tool error: {e}")
        return f"Web search unavailable: {e}"


@tool
def search_vinyl_prices(artist: str, title: str, config: RunnableConfig) -> str:
    """Get current market pricing and valuation data for a specific vinyl record.
    Use when the user asks about value, price, worth, or market conditions."""
    try:
        info = _get_chat_tools().get_vinyl_comprehensive_info(artist, title)
        parts = []
        for r in (info.get("pricing_info") or [])[:4]:
            parts.append(f"**{r['title']}**\n{r.get('content', '')[:300]}")
        for r in (info.get("general_info") or [])[:2]:
            parts.append(f"**{r['title']}**\n{r.get('content', '')[:200]}")
        return "\n\n".join(parts) if parts else "No pricing data found."
    except Exception as e:
        logger.error(f"search_vinyl_prices tool error: {e}")
        return f"Price lookup unavailable: {e}"


_QUERY_COLLECTION_MAX_LIMIT = 50  # hard cap to protect LLM token budget


@tool
def query_collection(
    user_tag: str = "",
    artist: str = "",
    title: str = "",
    genre: str = "",
    label: str = "",
    catalog_number: str = "",
    barcode: str = "",
    condition: str = "",
    notes: str = "",
    needs_review: Optional[bool] = None,
    year_from: int = 0,
    year_to: int = 0,
    value_min: float = 0.0,
    value_max: float = 0.0,
    sort_by: str = "value",
    sort_order: str = "desc",
    limit: int = 10,
    count_only: bool = False,
    config: RunnableConfig = None,  # type: ignore[assignment]
) -> str:
    """Query the user's vinyl collection database.
    Use to answer questions like 'how many records do I have',
    'what jazz records are in my collection', 'what are my most valuable records',
    'show me records from the 1970s', 'which records are by Miles Davis',
    'do I have any Blue Note records', 'show me records in mint condition',
    'find the record with barcode 1234567890', 'which records need review',
    or 'find records where I noted signed copy'.
    All parameters are optional — combine them to filter results.

    condition values: poor, fair, good, excellent, near_mint
    sort_by values: value, year, artist, title, label, created_at (default: value)
    sort_order values: asc, desc (default: desc)
    needs_review: true = only records pending review, false = only reviewed records
    notes: full-text search in user_notes field
    count_only: set true for 'how many' questions — returns count + stats without listing records
    limit: max records to return (1–50, default 10)
    """
    db = (config or {}).get("configurable", {}).get("db")
    if db is None:
        return "Collection database not available in this context."
    try:
        from sqlalchemy import func
        from backend.database import VinylRecord

        q = db.query(VinylRecord).filter(VinylRecord.in_register.is_(True))
        if user_tag:
            q = q.filter(VinylRecord.user_tag == user_tag)
        if artist:
            q = q.filter(VinylRecord.artist.ilike(f"%{artist}%"))
        if title:
            q = q.filter(VinylRecord.title.ilike(f"%{title}%"))
        if genre:
            q = q.filter(VinylRecord.genres.ilike(f"%{genre}%"))
        if label:
            q = q.filter(VinylRecord.label.ilike(f"%{label}%"))
        if catalog_number:
            q = q.filter(VinylRecord.catalog_number.ilike(f"%{catalog_number}%"))
        if barcode:
            q = q.filter(VinylRecord.barcode == barcode)
        if condition:
            q = q.filter(VinylRecord.condition.ilike(condition))
        if notes:
            q = q.filter(VinylRecord.user_notes.ilike(f"%{notes}%"))
        if needs_review is not None:
            q = q.filter(VinylRecord.needs_review.is_(needs_review))
        if year_from:
            q = q.filter(VinylRecord.year >= year_from)
        if year_to:
            q = q.filter(VinylRecord.year <= year_to)
        if value_min:
            q = q.filter(VinylRecord.estimated_value_eur >= value_min)
        if value_max:
            q = q.filter(VinylRecord.estimated_value_eur <= value_max)

        total = q.count()

        if count_only:
            stats = db.query(
                func.count(VinylRecord.id).label("n"),
                func.sum(VinylRecord.estimated_value_eur).label("total_value"),
                func.avg(VinylRecord.estimated_value_eur).label("avg_value"),
                func.max(VinylRecord.estimated_value_eur).label("max_value"),
            ).filter(VinylRecord.in_register.is_(True)).one()
            total_val = f"€{stats.total_value:.0f}" if stats.total_value else "?"
            avg_val = f"€{stats.avg_value:.0f}" if stats.avg_value else "?"
            max_val = f"€{stats.max_value:.0f}" if stats.max_value else "?"
            return (
                f"Collection stats: {stats.n} record(s) in register\n"
                f"  Total estimated value: {total_val}\n"
                f"  Average value: {avg_val}\n"
                f"  Most valuable: {max_val}"
            )

        if total == 0:
            return "No records found matching those criteria."

        # Sorting
        _sort_col_map = {
            "value": VinylRecord.estimated_value_eur,
            "year": VinylRecord.year,
            "artist": VinylRecord.artist,
            "title": VinylRecord.title,
            "label": VinylRecord.label,
            "created_at": VinylRecord.created_at,
        }
        sort_col = _sort_col_map.get(sort_by, VinylRecord.estimated_value_eur)
        order_expr = sort_col.desc().nullslast() if sort_order != "asc" else sort_col.asc().nullsfirst()

        capped_limit = min(max(1, limit), _QUERY_COLLECTION_MAX_LIMIT)
        records = q.order_by(order_expr).limit(capped_limit).all()

        truncated = total > capped_limit
        header = f"Found {total} record(s)" + (f", showing first {capped_limit} — narrow your search to see more." if truncated else ":")
        lines = [header]
        for r in records:
            value = f"€{r.estimated_value_eur:.0f}" if r.estimated_value_eur else "?"
            genres_list = r.get_genres()[:2] if hasattr(r, "get_genres") else []
            genres_str = f" [{', '.join(genres_list)}]" if genres_list else ""
            year_str = f" ({r.year})" if r.year else ""
            label_str = f" | {r.label}" if r.label else ""
            cat_str = f" [{r.catalog_number}]" if r.catalog_number else ""
            cond_str = f" | {r.condition}" if r.condition else ""
            review_str = " ⚠ needs review" if r.needs_review else ""
            notes_str = f"\n  📝 {r.user_notes[:120]}" if r.user_notes else ""
            spotify_str = f"\n  🎵 {r.spotify_url}" if r.spotify_url else ""
            lines.append(
                f"• {r.artist or '?'} – {r.title or '?'}{year_str}{genres_str}"
                f"{label_str}{cat_str}{cond_str} — {value}{review_str}"
                f"{notes_str}{spotify_str}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"query_collection tool error: {e}")
        return f"Collection query failed: {e}"



# ── Quiz helper ───────────────────────────────────────────────────────────
def _build_mc_question(
    topic: str, rec, pool: list, difficulty: str
) -> tuple:
    """Build a multiple-choice question. Returns (question_text, correct_answer, [4 shuffled choices]).
    Returns ("", "", []) when not enough data to build the question."""
    import random

    def _pick_distractors(values: list, correct: str, n: int = 3) -> list:
        others = [v for v in values if v and v != correct]
        random.shuffle(others)
        return others[:n]

    if topic == "year":
        if not rec.year:
            return "", "", []
        hint = "" if difficulty == "hard" else f" by {rec.artist}"
        q = f"What year was *{rec.title}*{hint} released?"
        correct = str(rec.year)
        distractors = _pick_distractors(list({str(r.year) for r in pool if r.year}), correct)
        if len(distractors) < 3:
            return q, correct, []  # fall back to open-ended
        choices = distractors + [correct]
        random.shuffle(choices)
        return q, correct, choices

    if topic == "label":
        if not rec.label:
            return "", "", []
        hint = f"*{rec.artist}* – *{rec.title}*" if difficulty != "hard" else f"*{rec.title}*"
        q = f"Which label released {hint}?"
        correct = rec.label
        distractors = _pick_distractors([r.label for r in pool], correct)
        if len(distractors) < 3:
            return q, correct, []
        choices = distractors + [correct]
        random.shuffle(choices)
        return q, correct, choices

    if topic == "genre":
        genres = rec.get_genres()
        if not genres:
            return "", "", []
        correct = genres[0]
        hint = f"*{rec.title}* by {rec.artist}" if difficulty != "hard" else f"*{rec.title}*"
        q = f"What is the primary genre of {hint}?"
        all_genres = [g for r in pool for g in r.get_genres()]
        distractors = _pick_distractors(all_genres, correct)
        if len(distractors) < 3:
            return q, correct, []
        choices = distractors + [correct]
        random.shuffle(choices)
        return q, correct, choices

    if topic == "artist":
        hint = f"*{rec.title}*" + (f" ({rec.year})" if rec.year and difficulty != "hard" else "")
        q = f"Which artist released {hint}?"
        correct = rec.artist
        distractors = _pick_distractors([r.artist for r in pool], correct)
        if len(distractors) < 3:
            return q, correct, []
        choices = distractors + [correct]
        random.shuffle(choices)
        return q, correct, choices

    return "", "", []


@tool
def quiz_collection(
    num_questions: int = 5,
    topic: str = "random",
    difficulty: str = "medium",
    config: RunnableConfig = None,  # type: ignore[assignment]
) -> str:
    """Generate an interactive multiple-choice quiz from the user's vinyl collection.

    topic     — 'year', 'label', 'genre', 'artist', or 'random' (default)
    difficulty— 'easy' (more context clues), 'medium', or 'hard' (minimal clues)
    num_questions — 1-10 questions (default 5)

    Use when the user asks to be quizzed, wants trivia, or says 'test me on my collection'.
    Present ONLY the question and answer options to the user — never reveal the ✓ answer
    markers. After the user replies, use the ✓ markers to score their answers."""
    import random

    db = (config or {}).get("configurable", {}).get("db")
    if db is None:
        return "Collection database not available in this context."

    try:
        from backend.database import VinylRecord

        pool = (
            db.query(VinylRecord)
            .filter(
                VinylRecord.in_register.is_(True),
                VinylRecord.artist.isnot(None),
                VinylRecord.title.isnot(None),
            )
            .all()
        )

        if len(pool) < 4:
            return "Need at least 4 records in your collection to build a quiz."

        num_questions = max(1, min(num_questions, 10, len(pool)))
        selected = random.sample(pool, num_questions)

        TOPICS = ["year", "label", "genre", "artist"]
        lines = [
            f"🎵 **Collection Quiz** — {num_questions} question{'s' if num_questions > 1 else ''}"
            f" | difficulty: {difficulty}\n",
            "*(Present questions one at a time; hide the ✓ answer markers; score after all answers received.)*\n",
        ]

        for i, rec in enumerate(selected, 1):
            if topic == "random":
                # Rotate through types that have data for this record
                candidates = [t for t in TOPICS if t != "year" or rec.year]
                candidates = [t for t in candidates if t != "label" or rec.label]
                candidates = [t for t in candidates if t != "genre" or rec.get_genres()]
                actual_topic = random.choice(candidates) if candidates else "artist"
            else:
                actual_topic = topic

            q, answer, choices = _build_mc_question(actual_topic, rec, pool, difficulty)

            # Fallback to artist if preferred topic had insufficient data
            if not q:
                q, answer, choices = _build_mc_question("artist", rec, pool, difficulty)
            if not q:
                continue

            if choices:
                letters = "abcd"
                correct_letter = letters[choices.index(answer)]
                opts = "\n".join(
                    f"   {letters[j]}) {choices[j]}" for j in range(len(choices))
                )
                lines.append(f"**Q{i}.** {q}\n{opts}\n   ✓ {correct_letter}) {answer}\n")
            else:
                # Open-ended fallback
                lines.append(f"**Q{i}.** {q}\n   ✓ {answer}\n")

        if len(lines) <= 2:
            return "Could not generate quiz questions — try a different topic or difficulty."

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"quiz_collection tool error: {e}")
        return f"Quiz generation failed: {e}"


_TOOLS = [web_search, search_vinyl_prices, query_collection, quiz_collection]


# ── System prompts ────────────────────────────────────────────────────────
def _now_str() -> str:
    """Current date and time in local timezone, formatted for the system prompt."""
    return datetime.now(timezone.utc).astimezone().strftime("%A, %Y-%m-%d %H:%M %Z")


def _record_system_prompt(meta: dict) -> str:
    value_str = f"€{meta['estimated_value_eur']:.2f}" if meta.get("estimated_value_eur") else "Unknown"
    genres_str = ", ".join(meta.get("genres") or []) or "Unknown"
    return (
        f"Current date and time: {_now_str()}\n\n"
        "Always reply in the same language the user writes in.\n\n"
        "You are a helpful vinyl record assistant with access to web search and collection tools.\n\n"
        "Use tools when the user asks about:\n"
        "- Current prices / market value → use search_vinyl_prices\n"
        "- General info, history, pressings, labels → use web_search\n"
        "- Their collection statistics or other records → use query_collection\n"
        "- Quiz / trivia about their collection → use quiz_collection\n\n"
        "query_collection usage guidelines:\n"
        "- 'How many records do I have?' or any count/stats question → count_only=True\n"
        "- Filter by any combination of: artist, title, genre, label, catalog_number,\n"
        "  barcode, condition, notes (searches user_notes text), needs_review, user_tag,\n"
        "  year_from/year_to, value_min/value_max\n"
        "- Sort with sort_by (value/year/artist/title/label/created_at) + sort_order (asc/desc)\n"
        "- Results are capped at 50 — tell the user to narrow the search if truncated\n\n"
        "Current record (always up to date — treat as ground truth):\n"
        f"- Artist: {meta.get('artist') or 'Unknown'}\n"
        f"- Title: {meta.get('title') or 'Unknown'}\n"
        f"- Year: {meta.get('year') or 'Unknown'}\n"
        f"- Label: {meta.get('label') or 'Unknown'}\n"
        f"- Catalog #: {meta.get('catalog_number') or 'Unknown'}\n"
        f"- Barcode: {meta.get('barcode') or 'Unknown'}\n"
        f"- Genres: {genres_str}\n"
        f"- Condition: {meta.get('condition') or 'Unknown'}\n"
        f"- Estimated Value: {value_str}\n"
        f"- Spotify: {meta.get('spotify_url') or 'Not available'}\n"
        f"- Notes: {meta.get('user_notes') or 'None'}\n\n"
        "Keep responses concise. Do not repeat the full record details unless asked."
    )


def _general_system_prompt() -> str:
    return (
        f"Current date and time: {_now_str()}\n\n"
        "Always reply in the same language the user writes in.\n\n"
        "You are a knowledgeable vinyl record expert assistant with access to tools.\n\n"
        "Available tools:\n"
        "- web_search: find information about any vinyl-related topic\n"
        "- search_vinyl_prices: get current market pricing for specific records\n"
        "- query_collection: query the user's vinyl collection database\n"
        "- quiz_collection: generate a multiple-choice quiz from the collection\n\n"
        "query_collection usage guidelines:\n"
        "- 'How many records do I have?' or any count/stats question → count_only=True\n"
        "- Filter by any combination of: artist, title, genre, label, catalog_number,\n"
        "  barcode, condition, notes (searches user_notes text), needs_review, user_tag,\n"
        "  year_from/year_to, value_min/value_max\n"
        "- Sort with sort_by (value/year/artist/title/label/created_at) + sort_order (asc/desc)\n"
        "- Results are capped at 50 — tell the user to narrow the search if truncated\n\n"
        "Use tools proactively when the user asks about prices, record details, "
        "or their collection. Keep responses concise and conversational."
    )


# ── Token counting (cheap approximation) ─────────────────────────────────
def _rough_token_count(messages: list) -> int:
    """Approx 4 chars per token — avoids calling the model for counting."""
    return sum(len(str(getattr(m, "content", m))) // 4 for m in messages)


# ── Nodes ─────────────────────────────────────────────────────────────────
def _build_agent_node(llm_with_tools):
    def agent_node(state: ChatAgentState, config: RunnableConfig):
        cfg = config.get("configurable", {})
        record_metadata = cfg.get("record_metadata")

        system_content = (
            _record_system_prompt(record_metadata)
            if record_metadata
            else _general_system_prompt()
        )

        trimmed = trim_messages(
            state["messages"],
            max_tokens=TOKEN_BUDGET,
            strategy="last",
            token_counter=_rough_token_count,
            include_system=False,
            allow_partial=False,
        )

        response = llm_with_tools.invoke(
            [SystemMessage(content=system_content)] + trimmed
        )
        return {"messages": [response]}

    return agent_node


# ── Graph compilation ─────────────────────────────────────────────────────
def _compile_graph(checkpointer: PostgresSaver):
    model_name = os.getenv("ANTHROPIC_CHAT_MODEL", "claude-haiku-4-5-20251001")
    llm = ChatAnthropic(model=model_name, max_tokens=800, temperature=0.3)
    llm_with_tools = llm.bind_tools(_TOOLS)

    g = StateGraph(ChatAgentState)
    g.add_node("agent", _build_agent_node(llm_with_tools))
    g.add_node("tools", ToolNode(_TOOLS))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")

    return g.compile(checkpointer=checkpointer)


# ── Singleton lifecycle ───────────────────────────────────────────────────
_checkpointer: Optional[PostgresSaver] = None
_graph = None


def init_chat_agent(database_url: str) -> None:
    """Call once at app startup. Creates LangGraph tables and compiles the graph."""
    global _checkpointer, _graph
    import psycopg
    conn = psycopg.connect(database_url, autocommit=True)
    _checkpointer = PostgresSaver(conn)
    _checkpointer.setup()
    _graph = _compile_graph(_checkpointer)
    logger.info("✅ Chat agent initialized (LangGraph ReAct + PostgresSaver)")


def get_chat_graph():
    """Return the compiled graph. Raises if init_chat_agent() was not called."""
    if _graph is None:
        raise RuntimeError(
            "Chat agent not initialized. Call init_chat_agent() at startup."
        )
    return _graph
