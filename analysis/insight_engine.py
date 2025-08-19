import os, json, time, math, statistics as stats
from typing import List, Dict, Any, Tuple
import pandas as pd
import requests

def _pct(n, d): 
    try: return (n/d) if d else None
    except: return None

def _na(v, alt=None):
    return v if v is not None else alt

def _median(series):
    try:
        s = [x for x in series if pd.notna(x)]
        return stats.median(s) if s else None
    except: return None

def _rolling_change(series, window=7):
    # expects daily series; returns pct change last window vs prior window
    if len(series) < window*2: return None
    a = series[-window:]; b = series[-2*window:-window]
    A = sum(a); B = sum(b)
    return None if not B else (A-B)/B

def _top_k(df, col, k=5, asc=False):
    if col not in df.columns: return pd.DataFrame()
    return df.dropna(subset=[col]).sort_values(col, ascending=asc).head(k)

def _simple_heuristics(df: pd.DataFrame) -> Tuple[List[str], List[Dict[str,Any]]]:
    """Derive insights + action items without LLM."""
    insights = []
    actions = []

    # Packaging mismatch: low CTR but above-median AVD
    if {"clickThroughRate","averageViewDuration"}.issubset(df.columns):
        ctr_med = _median(df["clickThroughRate"])
        avd_med = _median(df["averageViewDuration"])
        if ctr_med is not None and avd_med is not None:
            low_ctr = df[df["clickThroughRate"] < ctr_med]
            if not low_ctr.empty:
                keepers = low_ctr[low_ctr["averageViewDuration"] >= avd_med]
                if not keepers.empty:
                    insights.append("Several videos hold attention but fail to attract clicks → packaging (title/thumbnail) is the bottleneck.")
                    for _, r in _top_k(keepers, "averageViewDuration", k=5).iterrows():
                        actions.append({
                            "type":"Retitle/Thumb A/B",
                            "videoId": r.get("videoId"),
                            "title": r.get("title"),
                            "why": "Strong AVD but below-median CTR → packaging mismatch",
                            "suggested_tests":[
                                "Shorter, benefit-first title",
                                "Clearer subject isolation in thumbnail",
                                "Reduce text density <10 words"
                            ]
                        })

    # Cold-open drop: if we have AVD << duration hints (proxy)
    if "averageViewDuration" in df.columns and "durationSec" in df.columns:
        cold = df[(df["averageViewDuration"] < (df["durationSec"]*0.25))]
        if not cold.empty:
            insights.append("Many viewers bounce in the first quarter → cold opens are too slow or off-target.")
            for _, r in _top_k(cold, "averageViewDuration", k=5, asc=True).iterrows():
                actions.append({
                    "type":"Rewrite cold open",
                    "videoId": r.get("videoId"),
                    "title": r.get("title"),
                    "why": "Average view duration <25% of video length",
                    "suggested_tests":[
                        "Lead with result/controversy in first 5–10s",
                        "Cut preamble; add kinetic b-roll",
                        "Front-load a visual payoff"
                    ]
                })

    # Evergreen resurfacing: older videos still getting views
    if {"publishedAt","viewCount"}.issubset(df.columns):
        df2 = df.copy()
        try:
            df2["publishedAt"] = pd.to_datetime(df2["publishedAt"])
            evergreen = df2.sort_values("publishedAt").tail(200)
            hot_old = evergreen[evergreen["viewCount"] > evergreen["viewCount"].median()]
            if not hot_old.empty:
                insights.append("Some older videos still pull views → resurface them via new short/clip or updated title.")
                for _, r in _top_k(hot_old, "viewCount", k=5).iterrows():
                    actions.append({
                        "type":"Resurface evergreen",
                        "videoId": r.get("videoId"),
                        "title": r.get("title"),
                        "why":"High views despite age",
                        "suggested_tests":[
                            "Create 30–45s short with best moment",
                            "Add end screen from new upload",
                            "Minor title refresh (clarify benefit)"
                        ]
                    })
        except Exception:
            pass

    # Thin description / metadata issues (if present)
    if "description" in df.columns:
        thin = df[df["description"].fillna("").str.len() < 60]
        if not thin.empty:
            insights.append("Some videos have thin descriptions → hurts search intent and external discovery.")
            for _, r in _top_k(thin, "viewCount", k=5, asc=False).iterrows():
                actions.append({
                    "type":"Improve description",
                    "videoId": r.get("videoId"),
                    "title": r.get("title"),
                    "why":"Very short description",
                    "suggested_tests":[
                        "2–3 keyword-rich lines summarizing payoff",
                        "Timestamps and resources",
                        "Pin complementary comment"
                    ]
                })

    return insights, actions

def _llm_summarize(provider: str, model: str, base_url: str, system: str, prompt: str) -> str:
    """Best-effort local LLM (Ollama) or OpenAI; returns empty string on any failure."""
    try:
        if provider == "ollama":
            # Minimal Ollama chat call
            import json, requests
            r = requests.post(f"{base_url}/api/chat", json={
                "model": model,
                "messages":[
                    {"role":"system","content":system},
                    {"role":"user","content":prompt}
                ],
                "stream": False
            }, timeout=30)
            j = r.json()
            return j.get("message",{}).get("content","") if isinstance(j, dict) else ""
        elif provider == "openai":
            import os
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY","")
            if not api_key: return ""
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
                temperature=0.4,
            )
            return resp.choices[0].message.content or ""
        return ""
    except Exception:
        return ""

def generate_insights_and_actions(df: pd.DataFrame, provenance: dict) -> dict:
    # 1) Heuristics
    insights, actions = _simple_heuristics(df)

    # 2) Optional GPT layer (adds narrative + ranks actions by impact/risk)
    provider = os.getenv("LLM_PROVIDER","ollama")
    base = os.getenv("OLLAMA_BASE_URL","http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL","llama3.1:8b")
    system = ("You are a ruthless YouTube growth analyst. Summarize shifts, spot packaging mismatches, "
              "and output prioritized, practical actions. No fluff.")
    # Compact table context (top rows only to stay local and cheap)
    cols = [c for c in ["title","videoId","impressions","clickThroughRate","averageViewDuration","viewCount","likeCount","commentCount"] if c in df.columns]
    view = df[cols].sort_values(by=[c for c in cols if c!="title" and c!="videoId"][:1], ascending=False).head(20)
    prompt = f"Data sample (top 20 rows):\n{view.to_csv(index=False)[:8000]}\n\nHeuristic insights: {json.dumps(insights)[:2000]}\nHeuristic actions: {json.dumps(actions)[:4000]}\n\nWrite: (1) a 4-6 bullet narrative of what changed and why; (2) the 6 highest-impact, low-effort actions with short rationale."

    narrative = _llm_summarize(provider, model, base, system, prompt)

    return {
        "provenance": provenance,
        "insights_heuristic": insights,
        "actions_heuristic": actions,
        "narrative_gpt": narrative
    }

def write_reports(payload: dict, reports_dir: str):
    os.makedirs(reports_dir, exist_ok=True)
    # insights.md
    with open(os.path.join(reports_dir,"insights.md"),"w",encoding="utf-8") as f:
        f.write(f"# Weekly Insights\n\n")
        prov = payload.get("provenance",{})
        f.write(f"_Source: {prov.get('source')} • synthetic={prov.get('synthetic')} • ts={prov.get('ts')}_\n\n")
        if payload.get("narrative_gpt"):
            f.write("## Narrative\n\n")
            f.write(payload["narrative_gpt"] + "\n\n")
        if payload.get("insights_heuristic"):
            f.write("## Heuristic Insights\n\n")
            for i in payload["insights_heuristic"]:
                f.write(f"- {i}\n")
            f.write("\n")
    # actions.csv
    import csv
    actions = payload.get("actions_heuristic",[])
    with open(os.path.join(reports_dir,"actions.csv"),"w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["type","videoId","title","why","suggested_tests"])
        w.writeheader()
        for a in actions: w.writerow(a)
