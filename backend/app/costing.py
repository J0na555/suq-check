"""Gemini list prices and the four cost-per-observation benchmarks.

Numbers here are the pitch's sourced constants. Live spend is derived from
token counts written onto `evidence.raw_payload["gemini"]` at ingest time; the
benchmarks stay fixed so the endpoint can put a measured AI cost next to the
slide claim without re-deriving the whole operating model.
"""

from dataclasses import dataclass

# Gemini 2.5 Flash list prices (USD per 1M tokens). Same figures `render.yaml`
# comments next to GEMINI_MODEL.
GEMINI_INPUT_USD_PER_MTOK = 0.30
GEMINI_OUTPUT_USD_PER_MTOK = 2.50

# [ASSUMPTION] FX used to convert WFP's $20–40 questionnaire into ETB in the
# pitch ($20 → 3,160 ETB). Keep one rate so token costs and benchmarks share a
# currency basis.
USD_TO_ETB = 158.0


@dataclass(frozen=True, slots=True)
class CostBenchmark:
    id: str
    label: str
    min_etb: float
    max_etb: float
    unit: str
    source: str


# Four comparables the one-pager stacks against SuqCheck's fully-loaded figure.
COST_BENCHMARKS: tuple[CostBenchmark, ...] = (
    CostBenchmark(
        id="wfp_face_to_face",
        label="WFP face-to-face price questionnaire",
        min_etb=3160.0,
        max_etb=6320.0,
        unit="questionnaire",
        source="WFP mVAM HIF evaluation: $20–40 per face-to-face questionnaire",
    ),
    CostBenchmark(
        id="field_agent_sa",
        label="Field Agent South Africa retail audit mission",
        min_etb=1550.0,
        max_etb=3900.0,
        unit="store_mission",
        source="Field Agent SA retail audit mission rates, converted at pitch FX",
    ),
    CostBenchmark(
        id="premise_capture",
        label="Premise cost-per-capture",
        min_etb=9.5,
        max_etb=63.0,
        unit="capture",
        source="Premise published cost-per-capture $0.06–0.40",
    ),
    CostBenchmark(
        id="suqcheck_modelled",
        label="SuqCheck fully-loaded modelled cost",
        min_etb=5.9,
        max_etb=5.9,
        unit="observation",
        source="Operating model: ambassadors + rewards + coordinator + infra + contingency",
    ),
)


def gemini_cost_usd(*, prompt_tokens: float, candidates_tokens: float) -> float:
    return (
        prompt_tokens * GEMINI_INPUT_USD_PER_MTOK
        + candidates_tokens * GEMINI_OUTPUT_USD_PER_MTOK
    ) / 1_000_000


def usd_to_etb(amount_usd: float) -> float:
    return amount_usd * USD_TO_ETB


def allocated_tokens(count: int | float | None, *, shared_across: int | float | None) -> float:
    """Split a call's token count across the evidence rows it produced."""
    tokens = float(count or 0)
    share = max(float(shared_across or 1), 1.0)
    return tokens / share
