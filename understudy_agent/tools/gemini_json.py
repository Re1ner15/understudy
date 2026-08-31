import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from understudy_agent.config import MODEL_ID

load_dotenv("understudy_agent/.env")
load_dotenv()

client = genai.Client()

async def gemini_json(prompt: str, schema: type[BaseModel]) -> BaseModel:
    retries = [2, 5, 15, 30]
    
    for attempt in range(len(retries) + 1):
        try:
            response = await client.aio.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return schema.model_validate_json(response.text)
        except Exception as e:
            err_str = str(e)
            if attempt < len(retries) and (
                "503" in err_str
                or "429" in err_str
                or "UNAVAILABLE" in err_str
                or "Too Many Requests" in err_str
                or "RESOURCE_EXHAUSTED" in err_str
            ):
                await asyncio.sleep(retries[attempt])
            else:
                raise e
                
    raise RuntimeError("gemini_json: exhausted retries")


async def grounded_research(query: str) -> dict:
    """Runs a Gemini call grounded with Google Search — returns REAL, current,
    cited findings. Returns {"findings": str, "sources": [{"title","url"}]}.

    Grounding can't be combined with a strict response_schema, so this returns
    formatted markdown text plus the grounding citations.
    """
    prompt = (
        f"Research this and give a concise, decision-ready brief: {query}\n\n"
        "Use current, real data with specific numbers. Format as markdown with "
        "EXACTLY these sections, in this order:\n"
        "1. A single line starting with `**TL;DR:**` — one punchy sentence with the "
        "bottom-line recommendation or headline number.\n"
        "2. A markdown comparison table (columns for each option being compared and "
        "the dimensions that matter). Always include a table when two or more options "
        "are mentioned.\n"
        "3. A `**Key takeaways**` heading followed by 3-4 tight bullets, each leading "
        "with the specific fact/number.\n\n"
        "Keep it scannable — no long paragraphs. Do NOT include a sources section; "
        "sources are captured separately."
    )
    # Retry on transient Vertex rate limits so a 429 doesn't drop us to the
    # ungrounded fallback (which loses the table + live citations).
    retries = [3, 8, 20]
    response = None
    for attempt in range(len(retries) + 1):
        try:
            response = await client.aio.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    tools=[genai.types.Tool(google_search=genai.types.GoogleSearch())],
                    temperature=0.2,
                ),
            )
            break
        except Exception as e:
            err = str(e)
            transient = any(k in err for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"))
            if attempt < len(retries) and transient:
                await asyncio.sleep(retries[attempt])
            else:
                raise
    findings = response.text or ""
    sources = []
    try:
        gm = response.candidates[0].grounding_metadata
        seen = set()
        for chunk in (gm.grounding_chunks or []):
            web = getattr(chunk, "web", None)
            if web and web.uri and web.uri not in seen:
                seen.add(web.uri)
                sources.append({"title": web.title or web.uri, "url": web.uri})
    except Exception:
        pass
    return {"findings": findings, "sources": sources}
