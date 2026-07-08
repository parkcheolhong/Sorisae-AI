"""관광 데이터 사람검수 라우터 — 샘플링/라벨/집계 API + 자체완결 HTML 검수 콘솔.

내부 전문가 도구. 기본 활성(`TOURISM_REVIEW_ENABLED=1`)이며, **운영에서는 관리자 인증/내부망 뒤**에
두는 것을 전제로 한다(콘솔 HTML 은 정적, API 는 동일 오리진 호출).
"""

from __future__ import annotations

import os
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/tourism-review", tags=["tourism-review"])


def _enabled() -> bool:
    return os.getenv("TOURISM_REVIEW_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off", ""}


def _guard():
    if not _enabled():
        raise HTTPException(status_code=404, detail="tourism review disabled")


class ReviewLabel(BaseModel):
    item_type: str = "poi"
    query: Optional[str] = None
    place_source: Optional[str] = None
    place_source_id: Optional[str] = None
    place_name: Optional[str] = None
    category: Optional[str] = None
    verdict: str
    note: Optional[str] = None


class ReviewLabelBatch(BaseModel):
    reviewer: Optional[str] = None
    labels: List[ReviewLabel] = []


@router.get("/sample")
def review_sample(mode: str = "poi", n: int = 20, k: int = 5) -> Any:
    _guard()
    from backend.services.tourism_kb.review import get_review_store

    store = get_review_store()
    if not store.available:
        raise HTTPException(status_code=503, detail="review DB unavailable")
    if mode == "retrieval":
        return {"mode": "retrieval", "k": k, "batches": store.sample_retrieval(k=k)}
    return {"mode": "poi", "items": store.sample_pois(n=n)}


@router.post("/labels")
def review_labels(batch: ReviewLabelBatch) -> Any:
    _guard()
    from backend.services.tourism_kb.review import get_review_store

    store = get_review_store()
    if not store.available:
        raise HTTPException(status_code=503, detail="review DB unavailable")
    saved = store.save_labels([lb.model_dump() for lb in batch.labels], reviewer=batch.reviewer)
    return {"saved": saved}


@router.get("/stats")
def review_stats() -> Any:
    _guard()
    from backend.services.tourism_kb.review import get_review_store

    return get_review_store().stats()


@router.get("/console", response_class=HTMLResponse)
def review_console() -> str:
    _guard()
    return _CONSOLE_HTML


_CONSOLE_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>관광 데이터 사람검수 콘솔</title>
<style>
 :root{color-scheme:dark}
 body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0b0f16;color:#e6edf3;margin:0;padding:16px}
 h1{font-size:18px;margin:0 0 4px} .sub{color:#8b949e;font-size:12px;margin-bottom:14px}
 .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
 input,select,button{font-size:13px;border-radius:8px;border:1px solid #27405a;background:#0d2236;color:#e6edf3;padding:7px 10px}
 button{cursor:pointer;font-weight:700} button.primary{background:#1d4ed8;border-color:#1d4ed8}
 .card{background:#151b23;border:1px solid #21262d;border-radius:12px;padding:12px;margin-bottom:10px}
 .name{font-weight:700;font-size:14px} .meta{color:#8b949e;font-size:12px;margin-top:3px}
 .qhead{color:#79c0ff;font-weight:800;margin:14px 0 6px}
 .verdicts{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
 .v{padding:5px 10px;border-radius:999px;border:1px solid #27405a;background:#0d2236;font-size:12px;cursor:pointer}
 .v.sel{background:#1d4ed8;border-color:#1d4ed8;color:#fff}
 .note{margin-top:6px;width:100%;box-sizing:border-box}
 #stats{color:#9be8b3;font-size:12px;margin-left:auto;white-space:pre}
 #toast{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#1f3d28;color:#cfe8d6;padding:10px 16px;border-radius:10px;opacity:0;transition:opacity .3s}
</style></head>
<body>
<h1>관광 데이터 사람검수 콘솔</h1>
<div class="sub">전문가 검수: POI 분류/실재성 정확도 · 검색 결과 관련성. 라벨은 자동 메트릭과 상호보완됩니다.</div>
<div class="bar">
  <input id="reviewer" placeholder="검수자 이름/ID" style="width:140px"/>
  <select id="mode"><option value="poi">POI 검수</option><option value="retrieval">검색 관련성</option></select>
  <input id="n" type="number" value="20" min="1" max="200" style="width:70px" title="POI 표본 수"/>
  <input id="k" type="number" value="5" min="1" max="20" style="width:60px" title="top-k"/>
  <button class="primary" onclick="loadSample()">표본 불러오기</button>
  <button onclick="submitLabels()">라벨 제출</button>
  <span id="stats"></span>
</div>
<div id="list"></div>
<div id="toast"></div>
<script>
const VPOI=[['correct','정확'],['incorrect','부정확'],['unsure','모름']];
const VRET=[['relevant','관련'],['irrelevant','무관'],['unsure','모름']];
let STATE={mode:'poi',rows:[]};

function toast(t){const e=document.getElementById('toast');e.textContent=t;e.style.opacity=1;setTimeout(()=>e.style.opacity=0,1800);}
function pick(idx,verdict,btn){STATE.rows[idx].verdict=verdict;
  const p=btn.parentNode;[...p.children].forEach(c=>c.classList.remove('sel'));btn.classList.add('sel');}

function verdictBtns(idx,opts){
  return '<div class="verdicts">'+opts.map(([v,label])=>
    `<span class="v" onclick="pick(${idx},'${v}',this)">${label}</span>`).join('')+'</div>'
    +`<input class="note" placeholder="메모(선택)" oninput="STATE.rows[${idx}].note=this.value"/>`;
}

async function loadSample(){
  const mode=document.getElementById('mode').value;
  const n=document.getElementById('n').value, k=document.getElementById('k').value;
  const r=await fetch(`sample?mode=${mode}&n=${n}&k=${k}`); const d=await r.json();
  STATE={mode,rows:[]}; const list=document.getElementById('list'); list.innerHTML='';
  if(mode==='poi'){
    (d.items||[]).forEach(it=>{
      const idx=STATE.rows.length;
      STATE.rows.push({item_type:'poi',place_source:it.place_source,place_source_id:it.place_source_id,
        place_name:it.place_name,category:it.category,verdict:null,note:''});
      const el=document.createElement('div');el.className='card';
      el.innerHTML=`<div class="name">${it.place_name||'(이름없음)'} · ${it.category||'(미지정)'}</div>`
        +`<div class="meta">${it.address||''} · ${it.country||''} · ${it.place_source}/${it.place_source_id}</div>`
        +verdictBtns(idx,VPOI);
      list.appendChild(el);
    });
  } else {
    (d.batches||[]).forEach(b=>{
      const h=document.createElement('div');h.className='qhead';h.textContent='질의: '+b.query;list.appendChild(h);
      (b.results||[]).forEach(res=>{
        const idx=STATE.rows.length;
        STATE.rows.push({item_type:'retrieval',query:b.query,place_source:res.place_source,
          place_source_id:res.place_source_id,place_name:res.place_name,category:res.category,verdict:null,note:''});
        const el=document.createElement('div');el.className='card';
        el.innerHTML=`<div class="name">${res.place_name||'(이름없음)'} · ${res.category||''}</div>`
          +`<div class="meta">${res.address||''} · score ${res.score}</div>`+verdictBtns(idx,VRET);
        list.appendChild(el);
      });
    });
  }
  toast('표본 '+STATE.rows.length+'건 로드');
  loadStats();
}

async function submitLabels(){
  const labels=STATE.rows.filter(r=>r.verdict);
  if(!labels.length){toast('선택된 라벨이 없습니다');return;}
  const reviewer=document.getElementById('reviewer').value||null;
  const r=await fetch('labels',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({reviewer,labels})});
  const d=await r.json(); toast('저장 '+(d.saved||0)+'건'); loadStats();
}

async function loadStats(){
  const r=await fetch('stats'); const d=await r.json();
  if(!d.available){document.getElementById('stats').textContent='DB 비활성';return;}
  document.getElementById('stats').textContent=
    `총 ${d.total_labels} · 검수자 ${d.reviewers} · 사람정밀도 ${d.human_precision_retrieval??'-'} · POI정확도 ${d.poi_accuracy??'-'}`;
}
loadStats();
</script>
</body></html>
"""
